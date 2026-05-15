"""
Risk Scoring Engine — 数据驱动的风险评分引擎

核心原则：风险评分必须基于真实采集的数据计算，而非 LLM 估算。
LLM 只在无真实数据时作为最后的补充。

五维风险模型（每维 0-100 分）：
1. 经营风险 operation_risk — 基于工商异常、经营状态
2. 诉讼风险 litigation_risk — 基于执行案件、失信记录、裁判文书数
3. 信用风险 credit_risk — 基于信用中国数据、行政处罚
4. 合规风险 compliance_risk — 基于税务、环保、安全生产
5. 关联风险 relation_risk — 基于关联企业风险传导

数据来源优先级：
1. 真实政府公开数据（执行公开网、信用中国、裁判文书网）→ 权重最高
2. 公开工商数据（天眼查/企查查/爱企查 公开端点）→ 次高权重
3. LLM 分析 → 仅作为补充（标注为估算值）
"""

from datetime import datetime
from typing import Any


class DataQuality:
    """数据质量标注"""

    REAL = "real"  # 来自政府公开数据
    PUBLIC = "public"  # 来自公开工商平台
    LLM_ESTIMATED = "estimated"  # LLM 估算
    UNKNOWN = "unknown"


class RiskDimension:
    """单维风险评估结果"""

    def __init__(self, name: str, score: int = 0, label: str = "low"):
        self.name = name
        self.score = max(0, min(100, score))
        self.label = label  # low / medium / high
        self.data_quality = DataQuality.UNKNOWN
        self.evidence: list[str] = []  # 每个评分的依据
        self.data_sources: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "label": self.label,
            "data_quality": self.data_quality,
            "evidence": self.evidence,
            "data_sources": self.data_sources,
        }


class RiskScoringEngine:
    """数据驱动的风险评分引擎"""

    DIMENSION_WEIGHTS: dict[str, float] = {
        "operation_risk": 0.2,
        "litigation_risk": 0.2,
        "credit_risk": 0.2,
        "compliance_risk": 0.2,
        "relation_risk": 0.2,
    }

    DIMENSION_LABELS: dict[str, str] = {
        "operation_risk": "经营风险",
        "litigation_risk": "诉讼风险",
        "credit_risk": "信用风险",
        "compliance_risk": "合规风险",
        "relation_risk": "关联风险",
    }

    def compute_risk_scores(
        self,
        basic_info: dict[str, Any],
        litigation: dict[str, Any],
        credit: dict[str, Any],
        llm_risk: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        基于真实数据计算五维风险评分

        Args:
            basic_info: 工商基本信息
            litigation: 诉讼/执行数据
            credit: 信用/处罚数据
            llm_risk: LLM 估算的风险分（仅作补充）

        Returns:
            完整的风险评估结果，含评分、依据、数据质量
        """
        llm = llm_risk or {}

        op = self._compute_operation_risk(basic_info, llm)
        lit = self._compute_litigation_risk(litigation, llm)
        cred = self._compute_credit_risk(credit, llm)
        comp = self._compute_compliance_risk(credit, basic_info, llm)
        rel = self._compute_relation_risk(basic_info, llm)

        dimensions = [op, lit, cred, comp, rel]
        factors = self._build_factors(dimensions)
        avg_score = sum(d.score * self.DIMENSION_WEIGHTS[d.name] for d in dimensions)

        overall_rating = "high" if avg_score > 60 else "medium" if avg_score > 35 else "low"

        # 汇总所有依据
        all_evidence: list[str] = []
        for d in dimensions:
            all_evidence.extend(d.evidence)

        # 汇总所有数据来源
        all_sources: set[str] = set()
        for d in dimensions:
            all_sources.update(d.data_sources)

        # 判断整体数据质量
        quality_counts = {DataQuality.REAL: 0, DataQuality.PUBLIC: 0, DataQuality.LLM_ESTIMATED: 0}
        for d in dimensions:
            quality_counts[d.data_quality] = quality_counts.get(d.data_quality, 0) + 1

        if quality_counts[DataQuality.REAL] >= 3:
            overall_quality = DataQuality.REAL
        elif quality_counts[DataQuality.REAL] + quality_counts[DataQuality.PUBLIC] >= 3:
            overall_quality = DataQuality.PUBLIC
        else:
            overall_quality = DataQuality.LLM_ESTIMATED

        return {
            "operation_risk": op.score,
            "litigation_risk": lit.score,
            "credit_risk": cred.score,
            "compliance_risk": comp.score,
            "relation_risk": rel.score,
            "score": round(avg_score, 1),
            "overall_rating": overall_rating,
            "overall_score": round(avg_score, 1),
            "factors": factors,
            "explain": self._build_explanation(round(avg_score, 1), overall_rating, factors),
            "risk_points": all_evidence[:10],  # 最多 10 条
            "recommendations": self._generate_recommendations(dimensions),
            "data_quality": overall_quality,
            "data_sources": sorted(all_sources),
            "dimensions": {d.name: d.to_dict() for d in dimensions},
        }

    # ===== 各维度评分 =====

    def _compute_operation_risk(
        self, basic_info: dict[str, Any], llm: dict[str, Any]
    ) -> RiskDimension:
        """经营风险：基于工商状态、经营年限、异常记录"""
        dim = RiskDimension("operation_risk")
        score = 20  # 基准分（正常经营企业）

        status = basic_info.get("status", "")
        established = basic_info.get("established_date", "")

        # 经营状态
        if status:
            dim.data_sources.append("工商数据")
            if "注销" in status or "吊销" in status:
                score = 90
                dim.evidence.append(f"企业经营状态为「{status}」")
                dim.data_quality = DataQuality.PUBLIC
            elif "异常" in status:
                score = 70
                dim.evidence.append(f"企业经营状态为「{status}」")
                dim.data_quality = DataQuality.PUBLIC
            else:
                dim.data_quality = DataQuality.PUBLIC

        # 经营年限
        if established:
            try:
                year = int(established[:4])
                years = datetime.now().year - year
                if years < 1:
                    score = max(score, 50)
                    dim.evidence.append(f"企业成立不足1年（{established}），经营风险偏高")
                elif years < 3:
                    score = max(score, 35)
                    dim.evidence.append(f"企业成立{years}年，处于成长期")
                elif years > 20:
                    score = max(score - 10, 10)  # 老企业减分
            except (ValueError, TypeError):
                pass

        # 如果无真实数据，参考 LLM 但降低权重
        if dim.data_quality == DataQuality.UNKNOWN:
            llm_score = llm.get("operation_risk", 30)
            score = max(score, int(llm_score * 0.6))  # LLM 估算打 6 折
            dim.data_quality = DataQuality.LLM_ESTIMATED
            dim.data_sources.append("AI 估算")
            if llm_score > 50:
                dim.evidence.append(f"AI 评估经营风险偏高（{llm_score}分，仅供参考）")

        dim.score = min(100, score)
        dim.label = "high" if dim.score > 60 else "medium" if dim.score > 35 else "low"
        return dim

    def _compute_litigation_risk(
        self, litigation: dict[str, Any], llm: dict[str, Any]
    ) -> RiskDimension:
        """诉讼风险：基于执行案件数、失信记录、裁判文书数"""
        dim = RiskDimension("litigation_risk")
        score = 10  # 基准分

        execution_cases = litigation.get("execution_cases", 0)
        dishonest = litigation.get("dishonest_records", 0)
        wenshu_count = litigation.get("wenshu_case_count", 0)

        has_real_data = False

        # 执行案件（真实数据，权重最高）
        if execution_cases > 0 or "data_source_execution" in litigation:
            has_real_data = True
            dim.data_sources.append("中国执行信息公开网")
            if execution_cases > 10:
                score = max(score, 85)
                dim.evidence.append(f"存在 {execution_cases} 件执行案件（高风险）")
            elif execution_cases > 3:
                score = max(score, 65)
                dim.evidence.append(f"存在 {execution_cases} 件执行案件")
            elif execution_cases > 0:
                score = max(score, 45)
                dim.evidence.append(f"存在 {execution_cases} 件执行案件")

        # 失信记录（真实数据，严重性最高）
        if dishonest > 0 or "data_source_dishonest" in litigation:
            has_real_data = True
            dim.data_sources.append("全国法院失信被执行人名单")
            score = max(score, 75 + min(dishonest * 5, 20))
            dim.evidence.append(f"存在 {dishonest} 条失信被执行人记录（严重）")

        # 裁判文书（真实数据）
        if wenshu_count > 0 or "data_source_wenshu" in litigation:
            has_real_data = True
            dim.data_sources.append("中国裁判文书网")
            if wenshu_count > 20:
                score = max(score, 70)
                dim.evidence.append(f"裁判文书网收录 {wenshu_count} 条相关文书（较多）")
            elif wenshu_count > 5:
                score = max(score, 50)
                dim.evidence.append(f"裁判文书网收录 {wenshu_count} 条相关文书")
            elif wenshu_count > 0:
                score = max(score, 30)
                dim.evidence.append(f"裁判文书网收录 {wenshu_count} 条相关文书")

        if has_real_data:
            dim.data_quality = DataQuality.REAL
        else:
            # 无真实数据，参考 LLM（打折）
            llm_score = llm.get("litigation_risk", 20)
            score = max(score, int(llm_score * 0.5))
            dim.data_quality = DataQuality.LLM_ESTIMATED
            dim.data_sources.append("AI 估算")
            if llm_score > 40:
                dim.evidence.append(f"AI 评估诉讼风险偏高（{llm_score}分，仅供参考）")

        dim.score = min(100, score)
        dim.label = "high" if dim.score > 60 else "medium" if dim.score > 35 else "low"
        return dim

    def _compute_credit_risk(self, credit: dict[str, Any], llm: dict[str, Any]) -> RiskDimension:
        """信用风险：基于信用中国数据、行政处罚"""
        dim = RiskDimension("credit_risk")
        score = 15  # 基准分

        penalties = credit.get("administrative_penalties", 0)
        black_list = credit.get("black_list", False)
        red_list = credit.get("red_list", False)

        has_real_data = False

        # 行政处罚（真实数据）
        if penalties > 0 or "data_source_credit_china" in credit:
            has_real_data = True
            dim.data_sources.append("信用中国")
            if penalties > 5:
                score = max(score, 75)
                dim.evidence.append(f"信用中国记录 {penalties} 条行政处罚（较多）")
            elif penalties > 2:
                score = max(score, 55)
                dim.evidence.append(f"信用中国记录 {penalties} 条行政处罚")
            elif penalties > 0:
                score = max(score, 35)
                dim.evidence.append(f"信用中国记录 {penalties} 条行政处罚")

        # 黑名单（真实数据，极严重）
        if black_list:
            has_real_data = True
            score = max(score, 90)
            dim.evidence.append("企业在信用中国严重失信黑名单中（极高风险）")
            dim.data_sources.append("信用中国黑名单")

        # 红名单（正面信号）
        if red_list:
            has_real_data = True
            score = max(0, score - 15)
            dim.evidence.append("企业在守信红名单中（正面信号）")

        if has_real_data:
            dim.data_quality = DataQuality.REAL
        else:
            llm_score = llm.get("credit_risk", 20)
            score = max(score, int(llm_score * 0.5))
            dim.data_quality = DataQuality.LLM_ESTIMATED
            dim.data_sources.append("AI 估算")

        dim.score = min(100, score)
        dim.label = "high" if dim.score > 60 else "medium" if dim.score > 35 else "low"
        return dim

    def _compute_compliance_risk(
        self, credit: dict[str, Any], basic_info: dict[str, Any], llm: dict[str, Any]
    ) -> RiskDimension:
        """合规风险：基于处罚记录、经营范围"""
        dim = RiskDimension("compliance_risk")
        score = 15

        penalties = credit.get("administrative_penalties", 0)
        tax_violations = credit.get("tax_violations", 0)
        env_penalties = credit.get("environmental_penalties", 0)

        has_signal = False

        if penalties > 0:
            has_signal = True
            score += min(penalties * 10, 40)
            dim.evidence.append(f"行政处罚 {penalties} 条（合规隐患）")
            dim.data_sources.append("信用中国")

        if tax_violations > 0:
            has_signal = True
            score += min(tax_violations * 15, 30)
            dim.evidence.append(f"税务违规 {tax_violations} 条")

        if env_penalties > 0:
            has_signal = True
            score += min(env_penalties * 12, 30)
            dim.evidence.append(f"环保处罚 {env_penalties} 条")

        if has_signal:
            dim.data_quality = DataQuality.REAL
        else:
            llm_score = llm.get("compliance_risk", 20)
            score = max(score, int(llm_score * 0.5))
            dim.data_quality = DataQuality.LLM_ESTIMATED
            dim.data_sources.append("AI 估算")

        dim.score = min(100, score)
        dim.label = "high" if dim.score > 60 else "medium" if dim.score > 35 else "low"
        return dim

    def _compute_relation_risk(
        self, basic_info: dict[str, Any], llm: dict[str, Any]
    ) -> RiskDimension:
        """关联风险：当前主要依赖 LLM，标注为估算"""
        dim = RiskDimension("relation_risk")

        # 关联风险目前无法从公开数据直接获取，需要付费 API
        llm_score = llm.get("relation_risk", 20)
        dim.score = max(15, int(llm_score * 0.7))
        dim.data_quality = DataQuality.LLM_ESTIMATED
        dim.data_sources.append("AI 估算")

        if llm_score > 40:
            dim.evidence.append(f"AI 评估关联风险偏高（{llm_score}分，建议通过股权关系验证）")
        else:
            dim.evidence.append("关联风险评估需要股权数据支撑，当前为 AI 估算")

        dim.label = "high" if dim.score > 60 else "medium" if dim.score > 35 else "low"
        return dim

    # ===== 建议生成 =====

    def _build_factors(self, dimensions: list[RiskDimension]) -> list[dict[str, Any]]:
        """Build deterministic factor contribution rows for explainable scoring."""
        factors: list[dict[str, Any]] = []
        for dim in dimensions:
            weight = self.DIMENSION_WEIGHTS[dim.name]
            contribution = round(dim.score * weight, 1)
            evidence = list(dim.evidence[:3])
            factor = {
                "key": dim.name,
                "name": self.DIMENSION_LABELS[dim.name],
                "score": dim.score,
                "weight": weight,
                "contribution": contribution,
                "label": dim.label,
                "data_quality": dim.data_quality,
                "evidence": evidence,
                "explain": self._build_factor_explanation(dim, weight, contribution, evidence),
            }
            factors.append(factor)
        return factors

    def _build_factor_explanation(
        self,
        dim: RiskDimension,
        weight: float,
        contribution: float,
        evidence: list[str],
    ) -> str:
        label = self.DIMENSION_LABELS[dim.name]
        basis = "；".join(evidence) if evidence else "暂无明确风险信号"
        return f"{label}{dim.score}/100，权重{weight:.0%}，贡献{contribution:.1f}分；依据：{basis}"

    def _build_explanation(
        self,
        score: float,
        overall_rating: str,
        factors: list[dict[str, Any]],
    ) -> str:
        rating_label = {"high": "高", "medium": "中", "low": "低"}[overall_rating]
        leading_factors = sorted(
            factors,
            key=lambda f: (-float(f["contribution"]), str(f["key"])),
        )[:2]
        leading = "、".join(
            f"{factor['name']}贡献{factor['contribution']:.1f}分" for factor in leading_factors
        )
        return f"综合风险为{rating_label}（{score:.1f}/100）；主要来源：{leading}。"

    def _generate_recommendations(self, dimensions: list[RiskDimension]) -> list[str]:
        """基于评分结果生成针对性建议"""
        recs: list[str] = []

        for d in dimensions:
            if d.score > 60:
                if d.name == "litigation_risk":
                    recs.append("建议尽快核查涉诉详情，评估败诉风险和执行风险")
                elif d.name == "credit_risk":
                    recs.append("建议调查行政处罚详情，评估对业务的实质影响")
                elif d.name == "operation_risk":
                    recs.append("建议核实企业经营状态，确认是否存在停业/异常风险")
                elif d.name == "compliance_risk":
                    recs.append("建议开展合规审查，重点关注处罚涉及的业务领域")
                elif d.name == "relation_risk":
                    recs.append("建议排查关联企业风险传导，通过股权穿透分析")
            elif d.score > 35:
                recs.append(f"建议持续监控{d.name.replace('_risk', '')}相关指标变化")

        # 数据质量建议
        estimated_dims = [d for d in dimensions if d.data_quality == DataQuality.LLM_ESTIMATED]
        if estimated_dims:
            names = "、".join(d.name.replace("_risk", "风险") for d in estimated_dims)
            recs.append(f"注意：{names} 基于 AI 估算，建议核实")

        if not recs:
            recs.append("企业各项指标正常，建议定期复查")

        return recs


# 全局实例
risk_scoring_engine = RiskScoringEngine()
