"""
风险评估智能体
"""

from typing import Any

from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent
from src.prompts import load_prompt

_FALLBACK_PROMPT = "你是一位专业的法律风险评估专家，擅长识别和评估各类法律风险。"


class RiskAssessmentAgent(BaseLegalAgent):
    """风险评估智能体"""

    def __init__(self) -> None:
        config = AgentConfig(
            name="风险评估Agent",
            role="风险评估专家",
            description="法律风险识别、评估、防控建议",
            system_prompt=load_prompt("agents/risk_assessor.txt", fallback=_FALLBACK_PROMPT),
            tools=["risk_database", "case_analysis"],
        )
        super().__init__(config)

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """处理风险评估任务 (支持 A2UI 动态输出)"""
        description = task.get("description", "")
        context = task.get("context", {})
        dependent_results = task.get("dependent_results", {})
        context_text = f"\n补充背景：{context}\n" if context else ""

        # 整合前置智能体的结果
        context_info = ""
        if dependent_results:
            context_info = "\n\n前置分析结果：\n"
            for t_id, result in dependent_results.items():
                if isinstance(result, AgentResponse):
                    context_info += f"- {result.agent_name} (任务 {t_id})：{result.content[:200]}...\n"

        # 构建评估提示，要求输出包含 A2UI 结构
        prompt = f"""
请对以下事项进行法律风险评估：

评估对象：{description}
{context_text}
{context_info}

请提供：
1. 风险识别（列出所有潜在风险点）
2. 风险分析（分析每个风险的成因）
3. 风险评估（评估概率和影响程度）
4. 风险等级（极高/高/中/低）
5. 防控建议（具体可执行的措施）

**特别要求**：
除了文字描述，请在回复最后提供一个 JSON 格式的 A2UI 结构，用于前端动态渲染风险看板。
JSON 格式示例：
```json
{{
  "a2ui": {{
    "components": [
      {{
        "id": "risk_card",
        "type": "card",
        "props": {{ "title": "风险评估总览", "icon": "shield" }},
        "children": [
          {{ "id": "m1", "type": "metric", "props": {{ "label": "核心风险点", "value": "3处", "color": "red" }} }},
          {{ "id": "m2", "type": "metric", "props": {{ "label": "整体风险等级", "value": "高", "color": "red" }} }}
        ]
      }},
      {{
        "id": "alert_1",
        "type": "alert",
        "props": {{ "status": "warning", "title": "关键预警", "content": "合同违约金条款描述不清晰" }}
      }}
    ]
  }}
}}
```
"""

        # 调用Agent
        response_text = await self.chat(prompt)

        # 提取 A2UI JSON
        import json
        import re
        a2ui_data = {}
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if not json_match:
            json_match = re.search(r'(\{.*"a2ui".*\})', response_text, re.DOTALL)

        if json_match:
            try:
                raw_json = json.loads(json_match.group(1))
                a2ui_data = raw_json.get("a2ui", {})
            except Exception:
                pass

        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            reasoning="基于法律风险评估模型和 A2UI 动态渲染协议",
            metadata={"a2ui": a2ui_data},
            actions=[
                {"type": "risk_assessment", "description": "风险评估完成"}
            ]
        )

    async def assess_transaction(self, transaction_info: dict[str, Any]) -> dict[str, Any]:
        """评估交易风险"""
        prompt = f"""
请评估以下交易的法律风险：

交易类型：{transaction_info.get('type', '未知')}
交易对手：{transaction_info.get('counterparty', '未知')}
交易金额：{transaction_info.get('amount', '未知')}
交易内容：{transaction_info.get('description', '未知')}

请从以下角度评估：
1. 合同风险
2. 交易对手风险
3. 资金风险
4. 履约风险
5. 合规风险

给出综合风险评级和建议。
"""
        response = await self.chat(prompt)

        return {
            "transaction": transaction_info,
            "assessment": response,
            "agent": self.name
        }

    async def generate_risk_matrix(self, risks: list[dict[str, Any]]) -> str:
        """生成风险矩阵"""
        risks_str = "\n".join([
            f"- {r.get('name', '未知风险')}：{r.get('description', '')}"
            for r in risks
        ])

        prompt = f"""
请为以下风险生成风险矩阵：

{risks_str}

风险矩阵应包含：
1. 风险名称
2. 发生概率（极低/低/中/高/极高）
3. 影响程度（轻微/一般/严重/重大/灾难性）
4. 风险等级（根据概率×影响计算）
5. 优先级排序
6. 建议措施

请以表格形式输出。
"""
        return await self.chat(prompt)

    async def calculate_risk_score(self, factors: dict[str, Any]) -> dict[str, Any]:
        """计算风险评分"""
        # 简单的风险评分逻辑
        score = 0.0

        # 合同风险
        contract_risk = factors.get("contract_risk", 0.5)
        score += contract_risk * 0.3

        # 诉讼风险
        litigation_risk = factors.get("litigation_risk", 0.3)
        score += litigation_risk * 0.25

        # 合规风险
        compliance_risk = factors.get("compliance_risk", 0.4)
        score += compliance_risk * 0.25

        # 其他风险
        other_risk = factors.get("other_risk", 0.3)
        score += other_risk * 0.2

        # 确定风险等级
        if score >= 0.75:
            level = "critical"
        elif score >= 0.5:
            level = "high"
        elif score >= 0.25:
            level = "medium"
        else:
            level = "low"

        return {
            "score": round(score, 2),
            "level": level,
            "factors": factors
        }
