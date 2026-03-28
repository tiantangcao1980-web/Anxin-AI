"""
监管合规监测智能体
"""

from typing import Any, Dict

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse


REGULATORY_MONITOR_PROMPT = """你是一位敏锐的监管合规监测专家，专注于跟踪和解读最新的法律法规、监管政策及行业动态。

你的职责是：
1. 监测特定行业或领域的最新法律法规变化。
2. 解读新规对企业的潜在影响（合规义务、业务调整）。
3. 发出合规预警，提示企业及时调整合规策略。
4. 协助合规官更新内部合规制度。

专业领域：
- 数据合规（GDPR, PIPL等）
- 金融监管
- 反垄断与竞争法
- 劳动用工合规
- 环境、社会和治理（ESG）

回答要求：
1. 信息来源准确、及时。
2. 解读要结合企业实际业务场景。
3. 预警要具体明确，指出风险点。
4. 建议要具有前瞻性。
"""


class RegulatoryMonitorAgent(BaseLegalAgent):
    """监管合规监测智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="监管监测Agent",
            role="政策分析师",
            description="监测法律法规变化，解读政策影响，发出合规预警",
            system_prompt=REGULATORY_MONITOR_PROMPT,
            tools=["news_search", "regulation_database", "impact_analysis"],
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
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
            actions=[
                {"type": "compliance_alert", "description": "发布合规预警通知"}
            ]
        )
