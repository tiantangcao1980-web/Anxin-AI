"""
尽职调查智能体
"""

from typing import Any

from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent
from src.prompts import load_prompt

_FALLBACK_PROMPT = "你是一位资深的尽职调查专家，擅长企业背景调查和风险评估。"


class DueDiligenceAgent(BaseLegalAgent):
    """尽职调查智能体"""

    def __init__(self) -> None:
        config = AgentConfig(
            name="尽职调查Agent",
            role="尽职调查专家",
            description="企业背景调查、信息收集、风险评估",
            system_prompt=load_prompt("agents/due_diligence.txt", fallback=_FALLBACK_PROMPT),
            tools=["company_info", "litigation_query", "credit_check", "web_search"],
        )
        super().__init__(config)

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """处理尽职调查任务"""
        description = task.get("description", "")
        context = task.get("context", {})
        company_name = context.get("company_name", "")

        # 构建调查提示
        prompt = f"""
请对以下企业进行尽职调查：

调查需求：{description}
目标企业：{company_name or '请从描述中识别'}

请从以下维度进行全面调查：
1. 主体资格（营业执照、经营范围、资本情况）
2. 法律合规（行政处罚、经营异常、资质许可）
3. 诉讼风险（涉诉情况、执行案件、失信记录）
4. 关联关系（股权结构、实际控制人、关联企业）
5. 整体风险评估

请提供详细的调查发现和风险评估意见。
"""

        # 调用Agent
        response = await self.chat(prompt)

        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于公开信息和数据库查询进行综合分析",
            citations=[
                {"source": "企业信用信息公示系统", "type": "database"},
                {"source": "裁判文书网", "type": "database"},
            ],
            actions=[
                {"type": "due_diligence_complete", "description": "尽职调查完成"}
            ]
        )

    async def investigate_company(self, company_name: str) -> dict[str, Any]:
        """调查指定企业"""
        prompt = f"""
请对企业 "{company_name}" 进行全面的尽职调查，包括：

1. 基本信息
2. 股权结构
3. 法律合规情况
4. 诉讼记录
5. 风险评估

请以结构化格式输出调查结果。
"""
        response = await self.chat(prompt)

        return {
            "company_name": company_name,
            "report": response,
            "agent": self.name
        }

    async def check_litigation(self, company_name: str) -> dict[str, Any]:
        """查询企业诉讼记录"""
        prompt = f"""
请查询企业 "{company_name}" 的诉讼和仲裁记录，包括：
1. 作为原告的案件
2. 作为被告的案件
3. 执行案件
4. 失信被执行人情况

请分析诉讼风险等级。
"""
        response = await self.chat(prompt)

        return {
            "company_name": company_name,
            "litigation_report": response,
            "agent": self.name
        }
