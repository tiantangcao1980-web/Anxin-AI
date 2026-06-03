"""
监管合规监测智能体
"""

from typing import Any

from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent
from src.prompts import load_prompt

_FALLBACK_PROMPT = (
    "你是一位敏锐的监管合规监测专家，专注于跟踪和解读最新的法律法规、监管政策及行业动态。"
)


class RegulatoryMonitorAgent(BaseLegalAgent):
    """监管合规监测智能体"""

    def __init__(self) -> None:
        config = AgentConfig(
            name="监管监测Agent",
            role="政策分析师",
            description="监测法律法规变化，解读政策影响，发出合规预警",
            system_prompt=load_prompt("agents/regulatory_monitor.txt", fallback=_FALLBACK_PROMPT),
            tools=["news_search", "regulation_database", "impact_analysis"],
        )
        super().__init__(config)

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """处理监管监测任务"""
        industry = task.get("industry", "通用")
        region = task.get("region", "中国")
        keywords = task.get("keywords", [])

        prompt = f"""
请针对以下领域进行监管政策监测和解读：

关注行业：{industry}
关注地区：{region}
关键词：{', '.join(keywords)}

请提供：
1. **最新法规速递**：近期出台或征求意见的重要法律法规。
2. **重点解读**：核心条款及其对行业的影响。
3. **合规义务清单**：企业新增或变更的合规义务。
4. **行动建议**：企业应采取的应对措施（如制度修订、流程改造）。
"""

        # 调用Agent
        response = await self.chat(prompt)

        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于最新监管动态和合规分析框架",
            actions=[{"type": "compliance_alert", "description": "发布合规预警通知"}],
        )
