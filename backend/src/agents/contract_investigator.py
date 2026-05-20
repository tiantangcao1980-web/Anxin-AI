"""
合同调查Agent（分析循环的第一步）

职责：
1. 提取合同关键要素（主体、标的、金额、期限等）
2. 查询RAG知识库获取相关法条
3. 识别需要重点审查的条款
4. 输出结构化的调查笔记供审查循环使用

在双循环架构中的位置：
  分析循环: ContractInvestigator → ContractReviewer
  审查循环: ContractReviewer → ReviewChecker
"""

import json
from typing import Any, cast

from src.agents._prompt_safety import USER_INPUT_BOUNDARY, wrap_user_input
from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent
from src.services.agent_rag_service import AgentRAGService

_SYSTEM_PROMPT = """你是一位合同分析调查专家，负责合同审查的前置调查工作。

你的任务是：
1. 仔细阅读合同文本，提取所有关键要素
2. 识别合同类型和适用的法律法规
3. 标注需要重点审查的条款和潜在风险区域
4. 列出需要参考的法律条文

输出格式要求（JSON）：
{
    "contract_type": "合同类型",
    "parties": {
        "party_a": {"name": "甲方名称", "type": "自然人/法人/其他"},
        "party_b": {"name": "乙方名称", "type": "自然人/法人/其他"}
    },
    "key_elements": {
        "subject": "合同标的描述",
        "amount": "合同金额",
        "term": "合同期限",
        "payment": "付款安排",
        "delivery": "交付方式"
    },
    "applicable_laws": ["适用的法律法规名称列表"],
    "focus_areas": [
        {
            "area": "需要重点审查的领域",
            "reason": "原因",
            "related_clauses": ["相关条款编号"]
        }
    ],
    "clause_inventory": [
        {"number": "条款编号", "title": "条款标题", "type": "条款类型", "completeness": "完整/缺失/不完善"}
    ],
    "missing_elements": ["缺少的重要要素列表"],
    "preliminary_risks": ["初步识别的风险点"]
}

注意：你只负责调查和信息提取，不负责给出最终审查结论。"""


class ContractInvestigatorAgent(BaseLegalAgent):
    """合同调查Agent — 双循环审查的分析阶段"""

    def __init__(self) -> None:
        config = AgentConfig(
            name="合同调查Agent",
            role="合同分析调查专家",
            description="合同审查前置调查：提取要素、识别重点、匹配法条",
            system_prompt=_SYSTEM_PROMPT,
            temperature=0.2,  # 低温度确保结构化输出
            tools=[],
        )
        super().__init__(config)

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """执行合同调查分析"""
        description = task.get("description", "")
        context = task.get("context") or {}
        contract_type = context.get("contract_type", "")

        # RAG检索相关法律条文
        rag_context = ""
        try:
            rag_context = await AgentRAGService.get_legal_context(
                query=description[:2000],
                contract_type=contract_type,
                max_articles=10,
            )
            if rag_context:
                rag_context = f"\n【参考法律条文】\n{rag_context}"
        except Exception:
            pass

        prompt = f"""请对以下合同文本进行全面的调查分析：

{rag_context}

【合同文本】：
{description[:12000]}

请按照JSON格式输出调查结果，重点关注：
1. 准确提取所有关键要素（不遗漏）
2. 识别合同类型和适用法律
3. 标注每个条款的完整性评估
4. 列出需要重点审查的风险区域
5. 标明缺失的重要要素或条款"""

        response = await self.chat(prompt)

        # 解析调查结果
        investigation = self._parse_investigation(response)

        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="合同前置调查：要素提取+法条匹配+风险区域标注",
            metadata=investigation,
            actions=[{"type": "investigation_complete", "data": investigation}],
        )

    def _parse_investigation(self, response: str) -> dict[str, Any]:
        """解析调查结果"""
        import re

        try:
            code_block = re.search(r"```json\s*([\s\S]*?)\s*```", response)
            if code_block:
                return cast(dict[str, Any], json.loads(code_block.group(1)))
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                return cast(dict[str, Any], json.loads(json_match.group()))
        except json.JSONDecodeError:
            pass

        return {
            "contract_type": "未识别",
            "key_elements": {},
            "focus_areas": [],
            "missing_elements": [],
            "preliminary_risks": [],
        }
