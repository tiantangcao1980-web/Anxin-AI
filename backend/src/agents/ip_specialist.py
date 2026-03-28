"""
知识产权专家智能体
"""

from typing import Any, Dict

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse


IP_SPECIALIST_PROMPT = """你是一位知识产权领域的专家律师，精通专利、商标、著作权及商业秘密保护。

你的职责是：
1. 解答关于知识产权申请、保护和维权的咨询。
2. 分析知识产权侵权风险，进行侵权对比分析。
3. 提供知识产权布局和管理建议。
4. 协助处理知识产权许可和转让合同。

专业领域：
- 专利法
- 商标法
- 著作权法
- 反不正当竞争法
- 知识产权国际公约

回答要求：
1. 准确引用相关知识产权法律法规。
2. 对于侵权判定，要遵循“接触+实质性相似”或“全面覆盖”等专业原则。
3. 提供切实可行的维权或应诉建议。
"""


class IPSpecialistAgent(BaseLegalAgent):
    """知识产权专家智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="知识产权Agent",
            role="IP专家",
            description="处理专利、商标、著作权等知识产权相关事务",
            system_prompt=IP_SPECIALIST_PROMPT,
            tools=["patent_search", "trademark_search", "ip_law_search"],
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理知识产权任务"""
        query_type = task.get("type", "consultation") # consultation, infringement_check, registration
        details = task.get("details", "")
        context = task.get("context", {})
        
        prompt = ""
        
        if query_type == "infringement_check":
            prompt = f"""
请进行知识产权侵权初步分析：

疑似侵权行为描述：
{details}

权利权利基础（如专利号、商标注册号、作品登记等）：
{context.get('rights_basis', '未提供')}

对比文件/对象：
{context.get('comparison_target', '未提供')}

请分析：
1. 权利基础的稳定性。
2. 侵权比对分析（遵循相关法律原则）。
3. 侵权成立的可能性评估。
4. 维权建议。
"""
        else:
            prompt = f"""
请回答以下知识产权咨询：

问题详情：
{details}

背景信息：
{context}

请提供专业解答和建议。
"""
        
        # 调用Agent
        response = await self.chat(prompt)
        
        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于知识产权法律法规及审查标准",
            actions=[
                {"type": "ip_analysis", "description": "提供IP专业分析意见"}
            ]
        )
