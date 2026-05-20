"""
审查验证Agent（审查循环的验证步骤）

职责：
1. 验证审查结论的法律依据准确性
2. 检查是否遗漏关键条款审查
3. 评估风险评级的合理性
4. 生成审查质量置信度评分

在双循环架构中的位置：
  分析循环: ContractInvestigator → ContractReviewer
  审查循环: ContractReviewer → ReviewChecker ← (验证+补充)
"""

import json
import re
from typing import Any, cast

from src.agents._prompt_safety import USER_INPUT_BOUNDARY, wrap_user_input
from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent

_SYSTEM_PROMPT = """你是一位资深的法律审查质量控制专家，负责验证合同审查结论的准确性和完整性。

你的任务是：
1. 逐一验证每个风险点的法律依据是否正确
2. 检查审查是否遗漏了重要维度
3. 评估风险等级的合理性
4. 识别审查结论中的逻辑矛盾或不一致
5. 给出审查质量的置信度评分

验证标准：
- 法条引用必须准确（法律名称+条号正确）
- 风险等级必须与法律后果匹配
- 修改建议必须具有可操作性
- 不能遗漏合同的核心风险领域

输出格式（JSON）：
{
    "quality_score": 0.0-1.0,
    "confidence_level": "high/medium/low",
    "verification_results": [
        {
            "risk_index": 0,
            "risk_title": "风险标题",
            "legal_basis_correct": true/false,
            "risk_level_appropriate": true/false,
            "suggestion_actionable": true/false,
            "notes": "验证备注"
        }
    ],
    "missed_areas": [
        {
            "area": "遗漏的审查领域",
            "importance": "critical/high/medium",
            "recommendation": "建议补充审查的内容"
        }
    ],
    "inconsistencies": ["发现的逻辑矛盾或不一致"],
    "improvement_suggestions": ["审查质量改进建议"],
    "summary": "整体验证结论"
}"""


class ReviewCheckerAgent(BaseLegalAgent):
    """审查验证Agent — 双循环审查的验证阶段"""

    def __init__(self) -> None:
        config = AgentConfig(
            name="审查验证Agent",
            role="法律审查质量控制专家",
            description="验证审查结论的准确性、完整性和合理性",
            system_prompt=_SYSTEM_PROMPT,
            temperature=0.2,
            tools=[],
        )
        super().__init__(config)

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """验证审查结果"""
        description = task.get("description", "")
        context = task.get("context") or {}
        review_result = context.get("review_result", {})
        investigation = context.get("investigation", {})

        # 构建验证提示
        prompt = f"""请验证以下合同审查结果的质量：

【调查阶段发现】：
- 任务说明：{wrap_user_input(description, label='description')}
- 合同类型：{investigation.get('contract_type', '未知')}
- 缺失要素：{json.dumps(investigation.get('missing_elements', []), ensure_ascii=False)}
- 初步风险：{json.dumps(investigation.get('preliminary_risks', []), ensure_ascii=False)}
- 重点审查区域：{json.dumps([a.get('area', '') for a in investigation.get('focus_areas', [])], ensure_ascii=False)}

【审查结果】：
- 总结：{review_result.get('summary', '无')}
- 风险等级：{review_result.get('risk_level', '未评级')}
- 风险评分：{review_result.get('risk_score', 'N/A')}
- 识别的风险点数量：{len(review_result.get('risks', []))}
- 缺失条款：{json.dumps(review_result.get('missing_clauses', []), ensure_ascii=False)}

【风险详情】：
{self._format_risks(review_result.get('risks', []))}

请逐一验证并以JSON格式输出验证结果。重点关注：
1. 法条引用是否准确（检查法律名称和条文编号）
2. 风险等级是否与实际法律后果匹配
3. 调查阶段发现的重点区域是否都已覆盖
4. 修改建议是否具体可执行"""

        response = await self.chat(prompt)
        verification = self._parse_verification(response)

        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="审查质量验证：法条准确性+覆盖完整性+等级合理性",
            metadata=verification,
            actions=[{"type": "verification_complete", "data": verification}],
        )

    def _format_risks(self, risks: list[dict[str, Any]]) -> str:
        """格式化风险列表"""
        if not risks:
            return "无风险点"
        lines = []
        for i, risk in enumerate(risks):
            lines.append(
                f"风险{i+1}：[{risk.get('level', '?')}] {risk.get('title', '未知')}\n"
                f"  描述：{risk.get('description', '')[:200]}\n"
                f"  法律依据：{risk.get('legal_basis', '无')}\n"
                f"  建议：{risk.get('suggestion', '')[:200]}"
            )
        return "\n\n".join(lines)

    def _parse_verification(self, response: str) -> dict[str, Any]:
        """解析验证结果"""
        try:
            code_block = re.search(r"```json\s*([\s\S]*?)\s*```", response)
            if code_block:
                result = json.loads(code_block.group(1))
            else:
                json_match = re.search(r"\{[\s\S]*\}", response)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found")

            result = cast(dict[str, Any], result)
            result.setdefault("quality_score", 0.7)
            result.setdefault("confidence_level", "medium")
            result.setdefault("verification_results", [])
            result.setdefault("missed_areas", [])
            result.setdefault("inconsistencies", [])
            return result

        except (json.JSONDecodeError, ValueError):
            return {
                "quality_score": 0.5,
                "confidence_level": "low",
                "verification_results": [],
                "missed_areas": [],
                "inconsistencies": [],
                "summary": response[:500],
            }
