"""
审查记忆服务

保存每次合同审查的经验（发现+用户修正），
供后续相似合同审查复用。

核心能力：
1. 保存审查会话（合同类型+发现+用户修正）
2. 检索相似的历史审查
3. 统计分析审查薄弱环节
"""

import time
from collections import defaultdict
from typing import Any

from loguru import logger


class ReviewMemoryEntry:
    """审查记忆条目"""

    def __init__(
        self,
        contract_type: str,
        risks_found: list[dict[str, Any]],
        user_accepted: list[str],
        user_rejected: list[str],
        missing_clauses: list[str],
        quality_score: float = 0.0,
        timestamp: float = 0.0,
    ) -> None:
        self.contract_type = contract_type
        self.risks_found = risks_found
        self.user_accepted = user_accepted  # 用户接受的风险ID
        self.user_rejected = user_rejected  # 用户拒绝的风险ID
        self.missing_clauses = missing_clauses
        self.quality_score = quality_score
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "risks_count": len(self.risks_found),
            "accepted_count": len(self.user_accepted),
            "rejected_count": len(self.user_rejected),
            "missing_clauses": self.missing_clauses,
            "quality_score": self.quality_score,
            "timestamp": self.timestamp,
        }


class ReviewMemoryService:
    """审查记忆服务（内存版，后续可升级为DB持久化）"""

    def __init__(self) -> None:
        self._memories: list[ReviewMemoryEntry] = []
        self._type_stats: dict[str, dict[str, int]] = defaultdict(lambda: {
            "total_reviews": 0,
            "total_risks": 0,
            "accepted_risks": 0,
            "rejected_risks": 0,
        })

    def save_review(
        self,
        contract_type: str,
        review_result: dict[str, Any],
        accepted_risk_ids: list[str] | None = None,
        rejected_risk_ids: list[str] | None = None,
        quality_score: float = 0.0,
    ) -> None:
        """保存审查记忆"""
        entry = ReviewMemoryEntry(
            contract_type=contract_type,
            risks_found=review_result.get("risks", []),
            user_accepted=accepted_risk_ids or [],
            user_rejected=rejected_risk_ids or [],
            missing_clauses=review_result.get("missing_clauses", []),
            quality_score=quality_score,
        )
        self._memories.append(entry)

        # 更新统计
        stats = self._type_stats[contract_type]
        stats["total_reviews"] += 1
        stats["total_risks"] += len(entry.risks_found)
        stats["accepted_risks"] += len(entry.user_accepted)
        stats["rejected_risks"] += len(entry.user_rejected)

        logger.info(
            f"审查记忆保存: {contract_type}, "
            f"风险{len(entry.risks_found)}个, "
            f"接受{len(entry.user_accepted)}/拒绝{len(entry.user_rejected)}"
        )

    def find_similar_reviews(
        self,
        contract_type: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """查找相似的历史审查"""
        relevant = [
            m for m in self._memories
            if m.contract_type == contract_type or self._type_overlap(m.contract_type, contract_type)
        ]
        # 按时间倒序
        relevant.sort(key=lambda m: m.timestamp, reverse=True)
        return [m.to_dict() for m in relevant[:limit]]

    def get_common_risks(self, contract_type: str) -> list[str]:
        """获取某类合同的常见风险（基于历史）"""
        risk_counter: dict[str, int] = defaultdict(int)
        for m in self._memories:
            if m.contract_type == contract_type:
                for risk in m.risks_found:
                    title = risk.get("title", "")
                    if title:
                        risk_counter[title] += 1

        sorted_risks = sorted(risk_counter.items(), key=lambda x: x[1], reverse=True)
        return [risk for risk, _ in sorted_risks[:10]]

    def get_rejection_patterns(self, contract_type: str) -> dict[str, Any]:
        """分析用户拒绝模式（识别审查薄弱环节）"""
        rejected_types: dict[str, int] = defaultdict(int)
        total_reviews = 0

        for m in self._memories:
            if m.contract_type == contract_type:
                total_reviews += 1
                for risk in m.risks_found:
                    risk_id = risk.get("title", "")
                    if risk_id in m.user_rejected:
                        rejected_types[risk.get("type", "unknown")] += 1

        return {
            "total_reviews": total_reviews,
            "rejection_patterns": dict(rejected_types),
            "improvement_areas": [
                t for t, c in sorted(rejected_types.items(), key=lambda x: x[1], reverse=True)
                if c > 1
            ],
        }

    def get_type_stats(self, contract_type: str | None = None) -> dict[str, Any]:
        """获取审查统计"""
        if contract_type:
            return dict(self._type_stats.get(contract_type, {}))
        return {k: dict(v) for k, v in self._type_stats.items()}

    def get_prompt_enhancement(self, contract_type: str) -> str:
        """
        基于历史审查经验生成Prompt增强片段

        用于注入到审查Agent的prompt中，使其关注历史常见问题
        """
        common_risks = self.get_common_risks(contract_type)
        rejection_info = self.get_rejection_patterns(contract_type)

        if not common_risks and not rejection_info.get("improvement_areas"):
            return ""

        parts: list[str] = []
        if common_risks:
            parts.append(f"【历史审查经验】此类合同({contract_type})的常见风险点包括：{', '.join(common_risks[:5])}。请重点关注这些领域。")

        improvement = rejection_info.get("improvement_areas", [])
        if improvement:
            parts.append(f"【质量改进提示】过去审查中，以下类型的风险判断曾被用户拒绝较多：{', '.join(improvement[:3])}。请更审慎地评估这些类型的风险。")

        return "\n".join(parts)

    @staticmethod
    def _type_overlap(type_a: str, type_b: str) -> bool:
        """判断两个合同类型是否有交集"""
        keywords_a = set(type_a.replace("合同", "").replace("协议", ""))
        keywords_b = set(type_b.replace("合同", "").replace("协议", ""))
        return bool(keywords_a & keywords_b)


# 全局实例
review_memory = ReviewMemoryService()
