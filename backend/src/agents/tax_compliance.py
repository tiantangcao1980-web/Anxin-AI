"""
财税合规专家智能体
"""

from typing import Any, Dict

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse
from src.prompts import load_prompt


_FALLBACK_PROMPT = "你是一位资深的财税合规专家，精通税法、会计准则及财务风险控制。"


class TaxComplianceAgent(BaseLegalAgent):
    """财税合规专家智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="财税合规Agent",
            role="税务专家",
            description="处理税务合规、财务风险、税务筹划",
            system_prompt=load_prompt("agents/tax_compliance.txt", fallback=_FALLBACK_PROMPT),
            tools=["tax_law_search", "financial_analysis", "invoice_check"],
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理财税任务"""
        description = task.get("description", "")
        financial_data = task.get("context", {}).get("financial_data", {})
        
        prompt = f"""
请进行财税合规分析：

任务描述：
{description}

相关财务/税务背景数据：
{financial_data}

请从以下维度进行分析：
1. **合规性评估**：当前操作是否存在违规风险（如偷逃税、发票违规）。
2. **政策适用**：适用的具体税收政策依据。
3. **风险提示**：潜在的稽查风险点及后果（滞纳金、罚款、刑事责任）。
4. **优化建议**：合规的改进措施或筹划方案。
"""
        
        # 调用Agent
        response = await self.chat(prompt)
        
        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于税收征管法及会计准则",
            actions=[
                {"type": "tax_advisory", "description": "出具财税合规意见"}
            ]
        )
