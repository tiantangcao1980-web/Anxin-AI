"""
合同管家智能体 (Contract Steward Agent)
负责合同的全生命周期管理：归档、关键要素提取、履约监控、风险预警。
"""

import json
from datetime import datetime
from typing import Any

from src.agents._prompt_safety import USER_INPUT_BOUNDARY, wrap_user_input
from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent
from src.prompts import load_prompt

_FALLBACK_PROMPT = "你是一位细致入微的合同管家（Contract Steward）。"


class ContractStewardAgent(BaseLegalAgent):
    """合同管家智能体"""

    def __init__(self) -> None:
        config = AgentConfig(
            name="合同管家Agent",
            role="合同全生命周期管理员",
            description="负责合同归档、要素提取、履约监控与智能预警",
            system_prompt=load_prompt("agents/contract_steward.txt", fallback=_FALLBACK_PROMPT),
            tools=["signature_service", "calendar_tool", "risk_radar"],
        )
        super().__init__(config)

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """处理合同管理任务"""
        action = task.get("action", "archive")  # archive, check_status, analyze_risk
        context = task.get("context", {})
        contract_text = context.get("contract_text", "")
        contract_id = context.get("contract_id", "unknown")

        if action == "archive":
            return await self._archive_contract(contract_text, contract_id)
        elif action == "check_status":
            return await self._check_contract_status(context.get("contract_metadata", {}))
        else:
            return await self._general_management(task.get("description", ""))

    async def _archive_contract(self, text: str, cid: str) -> AgentResponse:
        """归档并提取要素"""
        prompt = f"""
请对以下合同文本进行归档解析，提取关键要素：

合同文本摘要：
{text[:3000]}... (略)

请输出严格的 JSON 格式，包含以下字段：
- contract_type: 合同类型
- parties: [甲方, 乙方]
- total_amount: 总金额
- effective_date: 生效日期 (YYYY-MM-DD)
- expiration_date: 到期日期 (YYYY-MM-DD)
- payment_schedule: [{{date: "...", amount: "...", condition: "..."}}]
- key_obligations: [义务1, 义务2]
- risk_points: [风险点1]
"""
        response = await self.chat(prompt)

        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="已完成合同关键要素提取，准备存入结构化数据库",
            actions=[{"type": "db_save", "data": "extracted_json"}],  # 模拟存库
        )

    async def _check_contract_status(self, metadata: dict[str, Any]) -> AgentResponse:
        """检查状态并生成提醒"""
        current_date = datetime.now().strftime("%Y-%m-%d")

        prompt = f"""
当前日期：{current_date}

请检查以下合同元数据，判断是否需要发出提醒：

{json.dumps(metadata, ensure_ascii=False, indent=2)}

检查规则：
1. 如果距离到期日少于 30 天 -> 续约/终止提醒。
2. 如果距离付款日少于 7 天 -> 付款/收款提醒。
3. 如果对方有高风险标记 -> 履约风险预警。

请输出：
- alerts: [{{type: "payment", level: "high", message: "..."}}]
- recommendations: [建议1, 建议2]
"""
        response = await self.chat(prompt)

        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于时间线和风险规则的智能扫描",
            actions=[
                {
                    "type": "send_notification",
                    "target": "user",
                    "title": "合同状态预警",
                    "message": "检测到合同关键节点或风险，请查看详细报告。",
                    "level": "warning",
                }
            ],
        )

    async def _general_management(self, query: str) -> AgentResponse:
        """通用管理问答"""
        response = await self.chat(query)
        return AgentResponse(agent_name=self.name, content=response)
