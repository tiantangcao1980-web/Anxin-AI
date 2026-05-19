"""
法务分析智能体 — 综合法律量化分析与咨询

核心定位：不是"计算器工具"，而是一个懂法律、会计算、能分析的综合智能体。

两种服务模式并存：
1. 咨询模式：用户问"辞退员工有什么风险？" → 法律分析 + 风险评估 + 合规建议
2. 解决模式：用户问"辞退这个员工要赔多少？" → 精确金额 + 操作步骤 + 文件清单

不管哪种模式，都提供完整闭环：
- 法律分析（为什么）
- 精确计算（多少钱）
- 操作建议（怎么做）
- 风险提示（注意什么）
- 后续追踪（下一步）
"""

import json
import re
from typing import Any

from src.agents._prompt_safety import USER_INPUT_BOUNDARY, wrap_user_input
from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent
from src.prompts import load_prompt
from src.services.legal_calculator_service import legal_calculator_service

_FALLBACK_PROMPT = (
    "你是一位资深法务分析师，精通中国劳动法、民事诉讼法、合同法。"
    "你既能提供深度法律咨询分析，也能给出精准的法律费用计算，为用户提供全面的法律服务。"
)


class LegalCalculatorAgent(BaseLegalAgent):
    """法务分析智能体 — 综合法律量化分析与咨询"""

    def __init__(self) -> None:
        config = AgentConfig(
            name="法务分析Agent",
            role="资深法务分析师",
            description="综合法务分析：经济补偿金、诉讼费用、时效评估、用工成本、工伤赔偿等量化分析与法律咨询",
            system_prompt=load_prompt("agents/legal_calculator.txt", fallback=_FALLBACK_PROMPT),
            tools=["legal_calculator", "knowledge_search"],
        )
        super().__init__(config)

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """处理法务分析任务"""
        description = str(task.get("description", ""))
        context_raw = task.get("context", {})
        context: dict[str, Any] = context_raw if isinstance(context_raw, dict) else {}

        # Step 1: 判断服务模式 — 是否包含可计算的量化需求
        analysis_prompt = f"""请分析以下用户需求，判断服务模式并提取信息。

用户描述：
{wrap_user_input(description, label='description')}

补充信息：
{json.dumps(context.get('filled_slots', {}), ensure_ascii=False, default=str) if context.get('filled_slots') else '无'}

请严格按以下 JSON 格式输出（只输出 JSON）：

```json
{{
  "mode": "calculate|consult|hybrid",
  "calc_type": "severance|litigation_cost|statute_of_limitations|overtime_pay|work_injury|none",
  "params": {{}},
  "missing_params": [],
  "clarification_needed": "",
  "consult_topics": ["需要咨询分析的法律问题"]
}}
```

mode 判断规则：
- "calculate"：用户明确要算具体金额（"赔多少""费用多少""还有多久到期"）
- "consult"：用户问法律问题/风险/流程，无需精确计算（"有什么风险""怎么处理""流程是什么"）
- "hybrid"：既要分析也要计算（"辞退员工有什么风险，赔偿怎么算"）

各计算器参数：
- severance: monthly_salary(月工资), work_years(工作年限), termination_type("N"/"N+1"/"2N"), city(城市), is_illegal(是否违法辞退)
- litigation_cost: amount(标的额), case_type("civil_property"/"labor"/"divorce"/"ip"/"administrative"), is_simplified(简易程序)
- statute_of_limitations: cause_of_action("general"/"labor_arbitration"等), trigger_date("YYYY-MM-DD"), is_interrupted(是否中断)
- overtime_pay: monthly_salary, overtime_hours_workday, overtime_hours_weekend, overtime_hours_holiday
- work_injury: disability_level(1-10), monthly_salary, city
"""

        try:
            extraction_result = await self.chat(analysis_prompt, max_tokens=800)
            request = self._parse_json(extraction_result)
        except Exception:
            request = None

        if not request:
            return await self._full_consult(description, context)

        mode = str(request.get("mode", "consult"))
        calc_type = str(request.get("calc_type", "none"))
        params_raw = request.get("params", {})
        params: dict[str, Any] = params_raw if isinstance(params_raw, dict) else {}
        missing = self._as_string_list(request.get("missing_params", []))
        clarification = str(request.get("clarification_needed", ""))
        consult_topics = self._as_string_list(request.get("consult_topics", []))

        # ===== 纯咨询模式 =====
        if mode == "consult" or calc_type == "none":
            return await self._full_consult(description, context, consult_topics)

        # ===== 需要补充信息 =====
        if missing and clarification:
            return await self._ask_for_details(calc_type, clarification, missing, description, context)

        # ===== 计算 + 分析模式 =====
        calc_result = legal_calculator_service.calculate(calc_type, params)

        if calc_result.warnings and calc_result.total_amount == 0 and not calc_result.breakdown:
            return await self._full_consult(description, context, consult_topics)

        markdown_result = calc_result.to_markdown()

        # 用 LLM 将计算结果融合进完整的法律分析
        synthesis_prompt = f"""你是资深法务分析师。以下是精确计算结果：

{markdown_result}

用户原始需求：{wrap_user_input(description, label='description')}

请提供一份完整的法务分析报告，要求：

1. **情况分析**：简要分析用户面临的法律情境
2. **精确计算**：保留上面的计算明细表格和法律依据（原样呈现）
3. **法律解读**：解释计算背后的法律逻辑，让用户理解"为什么是这个数"
4. **操作方案**：用户现在应该做什么（具体的、可执行的步骤）
5. **风险提示**：需要注意的法律风险和常见陷阱
6. **所需文件**：需要准备的文件清单
7. **后续建议**：完成当前步骤后，下一步应该关注什么

格式要求：
- 使用 Markdown，层次清晰
- 金额精确到元
- 法条引用具体到条款号
- 操作步骤要可执行（"第一步...第二步..."），不要空泛建议
"""

        try:
            full_response = await self.chat(synthesis_prompt, max_tokens=3000)
        except Exception:
            full_response = markdown_result

        full_response += "\n\n---\n*以上分析基于中国现行法律法规，仅供参考。具体金额可能因地方政策差异和个案情况有所不同，建议咨询当地专业律师确认。*"

        return AgentResponse(
            agent_name=self.config.name,
            content=full_response,
            metadata={
                "mode": mode,
                "calc_type": calc_type,
                "total_amount": calc_result.total_amount,
                "has_calculation": True,
                "confidence": 0.95,
            },
        )

    async def _full_consult(
        self,
        description: str,
        context: dict[str, Any],
        topics: list[str] | None = None,
    ) -> AgentResponse:
        """纯咨询模式 — 深度法律分析（不涉及具体计算）"""
        topics_hint = f"\n重点分析方向：{', '.join(topics)}" if topics else ""

        prompt = f"""你是资深法务分析师，请对以下法律问题提供全面深度分析。

用户描述：{wrap_user_input(description, label='description')}
{topics_hint}

请从以下角度提供完整分析：

1. **问题定性**：这属于什么类型的法律问题？涉及哪些法律关系？
2. **法律依据**：适用的核心法条（具体条款号）
3. **权利义务分析**：各方的权利和义务是什么？
4. **风险评估**：当前情况的主要法律风险
5. **解决方案**：
   - 方案A（推荐）：...
   - 方案B（备选）：...
6. **操作步骤**：推荐方案的具体执行步骤
7. **费用预估**：可能涉及的费用（如果适用，我可以帮您精确计算）
8. **注意事项**：常见的误区和陷阱

如果涉及金额计算（补偿金、诉讼费、时效等），主动告知用户"我可以帮您精确计算，请提供以下信息：..."
"""

        response = await self.chat(prompt, max_tokens=3000)

        response += "\n\n---\n*以上分析基于中国现行法律法规，仅供参考。建议咨询专业律师确认。*"

        return AgentResponse(
            agent_name=self.config.name,
            content=response,
            metadata={"mode": "consult", "has_calculation": False, "confidence": 0.85},
        )

    async def _ask_for_details(
        self,
        calc_type: str,
        clarification: str,
        missing: list[str],
        description: str,
        context: dict[str, Any],
    ) -> AgentResponse:
        """信息不足时：先给初步分析，再追问具体参数"""
        type_labels = {
            "severance": "经济补偿/赔偿金",
            "litigation_cost": "诉讼费用",
            "statute_of_limitations": "诉讼时效",
            "overtime_pay": "加班费",
            "work_injury": "工伤赔偿",
        }
        label = type_labels.get(calc_type, "法律费用")

        # 先给一个初步分析框架，再追问
        prompt = f"""用户想了解{label}相关问题，但信息还不完整。

用户描述：{wrap_user_input(description, label='description')}
缺少的信息：{', '.join(missing)}

请先给出：
1. 对用户情况的初步分析（基于已有信息）
2. 相关法律框架说明（适用哪些法条，一般怎么计算）
3. 然后自然地引导用户补充缺少的信息

语气要专业但亲切，让用户感受到你在帮他解决问题而不是机械追问。
不要列出参数名，而是用自然语言引导（如"请问您的月工资（税前）大概是多少？"）
"""

        response = await self.chat(prompt, max_tokens=1500)

        return AgentResponse(
            agent_name=self.config.name,
            content=response,
            metadata={
                "mode": "hybrid",
                "needs_clarification": True,
                "calc_type": calc_type,
                "missing_params": missing,
                "confidence": 0.7,
            },
        )

    @staticmethod
    def _as_string_list(value: Any) -> list[str]:
        """Normalize loose LLM JSON list fields into display-safe strings."""
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if item is not None]

    def _parse_json(self, text: str) -> dict[str, Any]:
        """从 LLM 输出中提取 JSON"""
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if match:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict):
                return parsed
            raise ValueError("JSON 根节点不是对象")
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
            raise ValueError("JSON 根节点不是对象")
        raise ValueError("无法解析 JSON")
