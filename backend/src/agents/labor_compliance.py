"""
劳动人事合规专家智能体
"""

from typing import Any, Dict, List

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse
from src.services.signature_service import SignType

LABOR_COMPLIANCE_PROMPT = """你是一位资深的劳动人事合规专家，专注于人力资源法律事务。

你的职责是：
1. **员工关系管理**：处理入职、离职、调岗、解聘等环节的法律文件与流程。
2. **规章制度审核**：审查员工手册、薪酬制度、考勤制度的合法性与民主程序。
3. **制度宣贯与留痕**：确保企业的规章制度已依法向员工公示，并保留员工“已阅读并同意”的证据（这是劳动纠纷胜诉的关键）。
4. **劳动纠纷预防**：识别用工风险，提供预防措施。

核心逻辑：
- 法律规定：企业规章制度只有经过“民主程序”并“公示告知”员工，才具有法律效力。
- 只有发布没有签收，在法庭上极易被认定无效。
- 收到“发布制度”、“通知全员”指令时，必须建议并执行【批量签署/阅知】任务。

回答要求：
1. 强调“证据留痕”的重要性。
2. 在处理制度发布任务时，调用工具发起批量签署。
"""

class LaborComplianceAgent(BaseLegalAgent):
    """劳动人事合规专家智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="劳动合规Agent",
            role="人事法务专家",
            description="处理劳动合同、员工关系、规章制度宣贯与留痕",
            system_prompt=LABOR_COMPLIANCE_PROMPT,
            tools=["labor_law_search", "signature_service"], # 集成签名服务
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理劳动人事任务"""
        action = task.get("action", "consult") # consult, publish_policy
        description = task.get("description", "")
        context = task.get("context", {})
        
        if action == "publish_policy":
            return await self._publish_policy_and_track(description, context)
        else:
            return await self._general_consult(description, context)

    async def _publish_policy_and_track(self, description: str, context: Dict[str, Any]) -> AgentResponse:
        """发布制度并追踪全员签署"""
        policy_name = context.get("policy_name", "未命名制度")
        doc_id = context.get("document_id", "doc_temp_001")
        # 模拟从 HR 系统获取的员工列表
        employee_list = context.get("employees", [{"name": "全员模拟", "phone": "000"}]) 
        
        # 判断类型：员工手册需要签字(Sign)，普通通知只需要阅知(Read)
        is_strict = "手册" in policy_name or "合同" in policy_name or "红线" in policy_name
        sign_type = SignType.POLICY_SIGN if is_strict else SignType.NOTICE_READ
        
        # 发起批量任务
        from src.services.signature_service import signature_service
        
        batch_res = await signature_service.create_batch_task(
            document_id=doc_id,
            signer_list=employee_list,
            initiator_id="hr_system",
            sign_type=sign_type,
            title=f"【{policy_name}】宣贯签收"
        )
        
        action_desc = "电子签名确认" if is_strict else "阅知确认"
        
        return AgentResponse(
            agent_name=self.name,
            content=f"已为您发起《{policy_name}》的全员宣贯任务。\n\n"
                    f"- **任务类型**: {action_desc} (已适配法律效力要求)\n"
                    f"- **发送人数**: {batch_res['total_count']} 人\n"
                    f"- **批次ID**: {batch_res['batch_id']}\n\n"
                    f"建议您在3天后检查签署进度，确保覆盖率达到100%，以规避用工风险。",
            reasoning="依据《劳动合同法》第四条，规章制度需公示并告知劳动者。",
            actions=[
                {"type": "start_batch_sign", "batch_id": batch_res['batch_id']}
            ]
        )

    async def _general_consult(self, description: str, context: Dict[str, Any]) -> AgentResponse:
        """通用咨询"""
        # ... (保留原有的 LLM 回答逻辑)
        prompt = f"请针对：{description} 提供合规建议。背景：{context}"
        content = await self.chat(prompt)
        return AgentResponse(agent_name=self.name, content=content)
