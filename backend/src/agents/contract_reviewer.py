"""
合同审查智能体
"""

from typing import Any, Dict
import json

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse


CONTRACT_REVIEW_PROMPT = """你是一位资深的合同审查专家，拥有丰富的合同法律实务经验。

你的职责是：
1. 仔细审查合同文本，识别潜在风险条款
2. 检查合同的完整性和合规性
3. 提取关键条款信息
4. 评估合同风险等级
5. 提供专业的修改建议

审查重点：
- 主体资格：检查签约主体的合法性
- 权利义务：审查权利义务是否对等
- 违约责任：评估违约条款的合理性
- 争议解决：检查管辖和仲裁条款
- 保密条款：审查保密义务和期限
- 知识产权：检查IP归属和使用权
- 付款条款：审查付款方式和时间
- 解除终止：评估合同解除条件

风险等级判断：
- critical: 存在重大法律风险，可能导致严重损失
- high: 存在较高风险，需要重点关注和修改
- medium: 存在一般风险，建议适当调整
- low: 风险较小，可以接受

输出格式要求：
请以JSON格式输出审查结果，包含以下字段：
{
    "summary": "审查总结",
    "risk_level": "overall风险等级",
    "risk_score": 0.0-1.0的风险评分,
    "key_terms": {
        "parties": "合同主体",
        "subject": "合同标的",
        "amount": "合同金额",
        "term": "合同期限",
        "payment": "付款条款",
        "liability": "违约责任"
    },
    "risks": [
        {
            "type": "风险类型",
            "level": "风险等级",
            "title": "风险标题",
            "description": "风险描述",
            "clause": "相关条款编号",
            "original_text": "原文内容",
            "suggestion": "修改建议",
            "suggested_text": "建议修改后的文本"
        }
    ],
    "suggestions": [
        "建议1",
        "建议2"
    ]
}
"""


class ContractReviewAgent(BaseLegalAgent):
    """合同审查智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="合同审查Agent",
            role="合同审查专家",
            description="审查合同条款、识别风险、提供修改建议",
            system_prompt=CONTRACT_REVIEW_PROMPT,
            temperature=0.3,  # 低温度确保稳定输出
            tools=["contract_parser", "template_compare"],
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理合同审查任务"""
        description = task.get("description", "")
        context = task.get("context") or {}
        contract_type = context.get("contract_type", "通用合同")
        
        # 构建审查提示
        prompt = f"""
请审查以下合同文本：

合同类型：{contract_type}

{description}

请按照规定的JSON格式输出完整的审查结果，包括：
1. 总体评估和风险等级
2. 关键条款提取
3. 识别的风险点（至少检查5个维度）
4. 具体修改建议
"""
        
        # 调用Agent
        response = await self.chat(prompt)
        
        # 尝试解析JSON结果
        review_result = self._parse_review_result(response)
        
        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于合同法和商业惯例进行系统性审查",
            citations=review_result.get("citations", []),
            actions=[
                {"type": "review_complete", "data": review_result}
            ],
            metadata=review_result
        )
    
    def _parse_review_result(self, response: str) -> Dict[str, Any]:
        """解析审查结果"""
        try:
            # 尝试从响应中提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        # 如果解析失败，返回基本结构
        return {
            "summary": response[:500],
            "risk_level": "medium",
            "risk_score": 0.5,
            "risks": [],
            "suggestions": [],
        }
    
    async def quick_review(self, contract_text: str) -> Dict[str, Any]:
        """快速审查合同（简化版）"""
        prompt = f"""
请快速审查以下合同，指出最重要的3个风险点：

{contract_text[:5000]}

请简洁回答，每个风险点用一句话描述。
"""
        response = await self.chat(prompt)
        
        return {
            "quick_review": response,
            "agent": self.name
        }
