"""
合规自检服务

功能：
1. AI 增强合规分析 — 根据检查结果生成专业整改建议
2. 报告生成 — 生成结构化 HTML 合规报告
3. 历史对比 — 对比多次检查结果的改善情况
"""

from datetime import datetime
from typing import Any

from loguru import logger


class ComplianceService:
    """合规自检服务"""

    async def generate_report(
        self,
        evaluation_result: dict[str, Any],
        company_name: str = "被检企业",
    ) -> dict[str, Any]:
        """
        生成合规检查报告

        Args:
            evaluation_result: 评估结果（来自 /compliance-check/evaluate 接口）
            company_name: 企业名称

        Returns:
            包含 HTML 报告和结构化数据
        """
        score = evaluation_result.get("score", 0)
        grade = evaluation_result.get("grade", "D")
        grade_label = evaluation_result.get("grade_label", "未评估")
        industry_name = evaluation_result.get("industry_name", "未知行业")
        risk_summary = evaluation_result.get("risk_summary", {})
        non_compliant = evaluation_result.get("non_compliant_details", [])
        recommendations = evaluation_result.get("recommendations", [])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 生成 HTML 报告
        html = self._render_html(
            company_name=company_name,
            industry_name=industry_name,
            score=score,
            grade=grade,
            grade_label=grade_label,
            risk_summary=risk_summary,
            non_compliant=non_compliant,
            recommendations=recommendations,
            generated_at=now,
        )

        # 尝试 AI 增强建议
        ai_suggestions = await self._ai_enhance(non_compliant, industry_name)

        return {
            "html": html,
            "company_name": company_name,
            "industry": evaluation_result.get("industry", ""),
            "score": score,
            "grade": grade,
            "ai_suggestions": ai_suggestions,
            "generated_at": now,
        }

    async def _ai_enhance(
        self,
        non_compliant: list[dict[str, Any]],
        industry: str,
    ) -> list[dict[str, str]]:
        """调用 LLM 生成专业整改建议"""
        if not non_compliant:
            return []

        try:
            from src.services import llm_service as llm_module

            llm_service = getattr(llm_module, "llm_service", None)
            if llm_service is None:
                raise RuntimeError("llm_service singleton is not configured")

            items_text = "\n".join(
                f"- [{item.get('risk_level', 'medium')}] {item.get('question', '')}（法规依据：{item.get('law_ref', '')}）"
                for item in non_compliant[:10]
            )

            prompt = f"""你是企业合规专家。以下是{industry}行业企业的合规自检中发现的不合规项目：

{items_text}

请为每个不合规项提供简洁的整改建议（每条不超过50字），格式为 JSON 数组：
[{{"item_id": "xxx", "suggestion": "整改建议内容"}}]

直接输出 JSON，不要其他内容："""

            result = await llm_service.chat(prompt, max_tokens=800)
            if result:
                import json

                try:
                    parsed = json.loads(result)
                    if isinstance(parsed, list):
                        suggestions: list[dict[str, str]] = []
                        for item in parsed:
                            if isinstance(item, dict):
                                suggestions.append(
                                    {
                                        "item_id": str(item.get("item_id", "")),
                                        "suggestion": str(item.get("suggestion", "")),
                                    }
                                )
                        if suggestions:
                            return suggestions
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.debug(f"AI 增强合规建议不可用: {e}")

        # Fallback: 基于规则生成通用建议
        return [
            {
                "item_id": item.get("id", ""),
                "suggestion": f"建议按照{item.get('law_ref', '相关法规')}要求，尽快完善相关制度并留存书面记录",
            }
            for item in non_compliant[:10]
        ]

    def _render_html(
        self,
        company_name: str,
        industry_name: str,
        score: int,
        grade: str,
        grade_label: str,
        risk_summary: dict[str, Any],
        non_compliant: list[dict[str, Any]],
        recommendations: list[str],
        generated_at: str,
    ) -> str:
        """渲染 HTML 合规报告"""
        grade_color = {
            "A": "#34C759",
            "B": "#007AFF",
            "C": "#FF9500",
            "D": "#FF3B30",
        }.get(grade, "#8E8E93")

        risk_rows = ""
        for item in non_compliant:
            level = item.get("risk_level", "low")
            level_color = {"high": "#FF3B30", "medium": "#FF9500", "low": "#007AFF"}.get(
                level, "#8E8E93"
            )
            level_label = {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(level, "未知")
            risk_rows += f"""
            <tr>
                <td style="padding:8px;border-bottom:1px solid #e5e5e5;"><span style="color:{level_color};font-weight:600;">{level_label}</span></td>
                <td style="padding:8px;border-bottom:1px solid #e5e5e5;">{item.get('question', '')}</td>
                <td style="padding:8px;border-bottom:1px solid #e5e5e5;font-size:12px;color:#666;">{item.get('law_ref', '')}</td>
            </tr>"""

        rec_items = "\n".join(f"<li style='margin-bottom:8px;'>{r}</li>" for r in recommendations)

        return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>{company_name} — 合规自检报告</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px; color: #333; line-height: 1.8; }}
h1 {{ text-align: center; color: #007AFF; border-bottom: 2px solid #007AFF; padding-bottom: 10px; }}
h2 {{ color: #1C1C1E; margin-top: 30px; padding: 8px 12px; background: #F2F2F7; border-left: 4px solid #007AFF; }}
.score-card {{ text-align: center; padding: 30px; background: linear-gradient(135deg, {grade_color}15, {grade_color}05); border: 2px solid {grade_color}40; border-radius: 16px; margin: 20px 0; }}
.score-number {{ font-size: 64px; font-weight: 800; color: {grade_color}; }}
.grade-badge {{ display: inline-block; padding: 4px 16px; border-radius: 20px; background: {grade_color}20; color: {grade_color}; font-weight: 700; font-size: 18px; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
th {{ background: #F2F2F7; padding: 10px 8px; text-align: left; font-weight: 600; }}
.footer {{ text-align: center; color: #8E8E93; font-size: 12px; margin-top: 40px; border-top: 1px solid #E5E5EA; padding-top: 20px; }}
.summary {{ display: flex; gap: 16px; justify-content: center; margin: 16px 0; }}
.summary-item {{ text-align: center; padding: 12px 20px; background: #F8F8FA; border-radius: 12px; }}
.summary-value {{ font-size: 24px; font-weight: 700; }}
</style></head><body>
<h1>{company_name}<br><small style="font-size:14px;color:#8E8E93;">合规自检报告 · {industry_name}</small></h1>

<div class="score-card">
  <div class="score-number">{score}</div>
  <div class="grade-badge">{grade} · {grade_label}</div>
</div>

<div class="summary">
  <div class="summary-item"><div class="summary-value" style="color:#FF3B30;">{risk_summary.get('high', 0)}</div><div>高风险</div></div>
  <div class="summary-item"><div class="summary-value" style="color:#FF9500;">{risk_summary.get('medium', 0)}</div><div>中风险</div></div>
  <div class="summary-item"><div class="summary-value" style="color:#007AFF;">{risk_summary.get('low', 0)}</div><div>低风险</div></div>
</div>

<h2>不合规项目明细</h2>
<table>
  <thead><tr><th>风险等级</th><th>检查项目</th><th>法规依据</th></tr></thead>
  <tbody>{risk_rows if risk_rows else '<tr><td colspan="3" style="text-align:center;padding:20px;color:#999;">全部合规，无不合规项目</td></tr>'}</tbody>
</table>

<h2>整改建议</h2>
<ol style="padding-left:20px;">{rec_items if rec_items else '<li>暂无整改建议，企业合规状况良好</li>'}</ol>

<div class="footer">
  <p>本报告由安心智能助手 AI 辅助生成，仅供参考</p>
  <p>报告生成时间：{generated_at}</p>
</div>
</body></html>"""

    async def compare_evaluations(
        self,
        current: dict[str, Any],
        previous: dict[str, Any],
    ) -> dict[str, Any]:
        """对比两次合规检查结果"""
        current_score = current.get("score", 0)
        previous_score = previous.get("score", 0)
        delta = current_score - previous_score

        current_risks = current.get("risk_summary", {})
        previous_risks = previous.get("risk_summary", {})

        return {
            "score_current": current_score,
            "score_previous": previous_score,
            "score_delta": delta,
            "trend": "improved" if delta > 0 else "declined" if delta < 0 else "unchanged",
            "risk_changes": {
                level: current_risks.get(level, 0) - previous_risks.get(level, 0)
                for level in ("high", "medium", "low")
            },
            "summary": f"合规评分{'提升' if delta > 0 else '下降' if delta < 0 else '持平'} {abs(delta)} 分"
            + (
                f"，高风险项{'减少' if current_risks.get('high', 0) < previous_risks.get('high', 0) else '增加'}"
                if current_risks.get("high", 0) != previous_risks.get("high", 0)
                else ""
            ),
        }


# 全局实例
compliance_service = ComplianceService()
