"""
合规审核智能体
"""

from typing import Any, Dict, List

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse


COMPLIANCE_PROMPT = """你是一位资深的企业合规官，精通企业合规管理和法律风险防控。

你的职责是：
1. 审核企业经营行为的合规性
2. 评估法律法规遵从情况
3. 识别合规风险和漏洞
4. 制定合规整改建议
5. 建立合规管理体系

合规审核领域：
1. 公司治理合规
   - 公司章程
   - 三会运作
   - 关联交易
   - 信息披露

2. 劳动用工合规
   - 劳动合同管理
   - 社保公积金
   - 工时与休假
   - 劳动保护

3. 数据隐私合规
   - 个人信息保护
   - 数据安全
   - 跨境数据传输
   - 用户授权

4. 反商业贿赂合规
   - 商业往来
   - 礼品馈赠
   - 招待费用
   - 第三方管理

5. 行业监管合规
   - 资质许可
   - 行业规范
   - 监管报告
   - 合规经营

6. 知识产权合规
   - 自主知识产权
   - 第三方授权
   - 侵权防范

合规评估标准：
- 合规：完全符合法律法规要求
- 基本合规：存在轻微不足，风险可控
- 部分合规：存在明显缺陷，需要整改
- 不合规：存在重大违规，需要立即纠正

输出要求：
1. 合规评估结论
2. 发现的合规问题
3. 风险等级评估
4. 整改建议和时间表
"""


class ComplianceAgent(BaseLegalAgent):
    """合规审核智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="合规审核Agent",
            role="合规官",
            description="企业合规审核、风险识别、整改建议",
            system_prompt=COMPLIANCE_PROMPT,
            tools=["regulation_database", "compliance_checklist"],
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理合规审核任务"""
        description = task.get("description", "")
        context = task.get("context", {})
        compliance_area = context.get("area", "")
        
        # 构建审核提示
        prompt = f"""
请对以下事项进行合规审核：

审核事项：{description}
审核领域：{compliance_area or '综合合规'}

请提供：
1. 合规评估结论（合规/基本合规/部分合规/不合规）
2. 适用的法律法规
3. 发现的合规问题（列明具体问题）
4. 风险等级评估
5. 整改建议（具体可执行）
6. 建议整改时间表

请详细分析并给出专业意见。
"""
        
        # 调用Agent
        response = await self.chat(prompt)
        
        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于现行法律法规和合规管理最佳实践",
            citations=[],
            actions=[
                {"type": "compliance_review", "description": "合规审核完成"}
            ]
        )
    
    async def check_compliance(
        self,
        area: str,
        checklist_items: List[str],
    ) -> Dict[str, Any]:
        """按清单检查合规性"""
        items_str = "\n".join([f"- {item}" for item in checklist_items])
        
        prompt = f"""
请对以下{area}合规检查项进行评估：

{items_str}

对每一项给出：
1. 合规状态（合规/不合规/待确认）
2. 简要说明
3. 如不合规，给出整改建议
"""
        response = await self.chat(prompt)
        
        return {
            "area": area,
            "checklist": checklist_items,
            "assessment": response,
            "agent": self.name
        }
    
    async def generate_compliance_report(
        self,
        company_name: str,
        review_areas: List[str],
    ) -> str:
        """生成合规报告"""
        areas_str = "、".join(review_areas) if review_areas else "综合合规"
        
        prompt = f"""
请为企业 "{company_name}" 生成{areas_str}领域的合规评估报告：

报告应包含：
1. 概述
2. 合规评估范围
3. 评估方法
4. 主要发现
5. 风险评估
6. 整改建议
7. 结论

请使用正式的报告格式。
"""
        return await self.chat(prompt)
