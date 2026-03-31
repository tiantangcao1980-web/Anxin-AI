"""
法律顾问智能体
"""

from typing import Any, Dict

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse
from src.prompts import load_prompt


# 保留原始 prompt 作为 fallback（文件不存在时使用）
_FALLBACK_PROMPT = "你是一位资深的法律顾问，拥有丰富的法律实务经验。"


class LegalAdvisorAgent(BaseLegalAgent):
    """法律顾问智能体"""

    def __init__(self):
        config = AgentConfig(
            name="法律顾问Agent",
            role="首席法律顾问",
            description="提供综合法律咨询、方案建议和专业意见",
            system_prompt=load_prompt("agents/legal_advisor.txt", fallback=_FALLBACK_PROMPT),
            tools=["knowledge_search", "case_search"],
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理法律咨询任务"""
        description = task.get("description", "")
        context = task.get("context", {})
        
        # 构建提示
        prompt = f"""
请对以下法律问题提供专业咨询：

问题描述：
{description}

背景信息：
{context.get('background', '无')}

请从以下角度进行分析：
1. 问题性质判断
2. 相关法律依据
3. 可能的法律风险
4. 建议的解决方案
5. 后续行动建议
"""
        
        # 调用Agent
        llm_config = context.get("llm_config")
        response = await self.chat(prompt, llm_config=llm_config)
        
        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于法律专业知识和相关法规进行分析",
            citations=[],  # TODO: 添加法律引用
            actions=[
                {"type": "recommendation", "description": "建议进一步咨询专业律师"}
            ]
        )
