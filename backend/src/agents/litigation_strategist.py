"""
诉讼策略专家智能体
"""

from typing import Any

from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent
from src.prompts import load_prompt

_FALLBACK_PROMPT = "你是一位资深的诉讼策略专家，擅长处理复杂的民商事诉讼和仲裁案件。"


class LitigationStrategistAgent(BaseLegalAgent):
    """诉讼策略专家智能体"""

    def __init__(self) -> None:
        config = AgentConfig(
            name="诉讼策略Agent",
            role="资深诉讼律师",
            description="制定诉讼策略，评估案件风险，指导证据准备",
            system_prompt=load_prompt(
                "agents/litigation_strategist.txt", fallback=_FALLBACK_PROMPT
            ),
            tools=["case_search", "law_search", "evidence_analysis"],
        )
        super().__init__(config)

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """处理诉讼策略任务"""
        case_info = task.get("case_info", {})
        evidence_list = task.get("evidence", [])
        opponent_info = task.get("opponent", {})

        # 构建提示
        prompt = f"""
请为以下案件制定诉讼策略：

案件基本信息：
{case_info}

现有证据：
{evidence_list}

对方当事人信息：
{opponent_info}

请提供以下分析：
1. **案件评估**：核心争议焦点、胜诉概率预估。
2. **证据分析**：现有证据的证明力，还需补充哪些关键证据。
3. **策略建议**：建议采取的整体策略（诉讼、仲裁、调解等）及理由。
4. **风险提示**：最大的败诉风险点及应对预案。
5. **行动计划**：下一阶段的具体行动步骤。
"""

        # 调用Agent
        response = await self.chat(prompt)

        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于案件分析方法论和诉讼实务经验",
            actions=[{"type": "strategy_report", "description": "生成诉讼策略分析报告"}],
        )
