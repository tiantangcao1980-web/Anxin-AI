"""
合同审查智能体
"""

from typing import Any, Dict
import json

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse
from src.prompts import load_prompt


_FALLBACK_PROMPT = "你是一位资深的合同审查专家，拥有丰富的合同法律实务经验。"


class ContractReviewAgent(BaseLegalAgent):
    """合同审查智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="合同审查Agent",
            role="合同审查专家",
            description="审查合同条款、识别风险、提供修改建议",
            system_prompt=load_prompt("agents/contract_reviewer.txt", fallback=_FALLBACK_PROMPT),
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
