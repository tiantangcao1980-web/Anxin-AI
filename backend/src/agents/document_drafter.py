"""
文书起草智能体
"""

from dataclasses import dataclass
from typing import Any

from src.agents._prompt_safety import USER_INPUT_BOUNDARY, wrap_user_input
from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent
from src.prompts import load_prompt
from src.services.agent_rag_service import AgentRAGService
from src.services.document_validator import DocumentValidator

_FALLBACK_PROMPT = "你是一位专业的法律文书起草专家，精通各类法律文书的撰写。"
MissingFieldSpec = dict[str, str | float]


@dataclass
class DraftPlan:
    normalized_doc_type: str
    draft_mode: str
    missing_fields: list[dict[str, str]]
    completeness_score: float


class DocumentDraftAgent(BaseLegalAgent):
    """文书起草智能体"""

    def __init__(self) -> None:
        config = AgentConfig(
            name="文书起草Agent",
            role="法律文书专家",
            description="起草各类法律文书、合同、函件",
            system_prompt=load_prompt("agents/document_drafter.txt", fallback=_FALLBACK_PROMPT),
            tools=["template_library", "document_generator"],
        )
        super().__init__(config)

    _MIN_CLAUSE_REQUIREMENTS = {
        "合同": 12,
        "协议": 10,
        "起诉状": 0,
        "律师函": 0,
        "法律意见": 0,
    }

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        description = task.get("description", "")
        context = task.get("context", {})
        doc_type = context.get("doc_type", "")
        requirements = context.get("requirements", {})
        scenario = context.get("scenario", "")
        draft_plan = self._assess_draft_plan(doc_type, description, requirements, scenario)
        structure_guide = self._get_structure_guide(doc_type)
        rag_context = ""
        try:
            rag_context = await AgentRAGService.get_legal_context(
                query=f"{doc_type} {(scenario or description)[:1000]}",
                contract_type=doc_type,
                max_articles=6,
            )
            if rag_context:
                rag_context = AgentRAGService.build_rag_prompt_section(
                    rag_context, task_type="draft"
                )
        except Exception:
            pass

        prompt = self._build_prompt(
            doc_type=doc_type or "请根据需求判断",
            description=description,
            scenario=scenario,
            requirements=requirements,
            draft_plan=draft_plan,
            structure_guide=structure_guide,
            rag_context=rag_context,
        )
        response = await self.chat(prompt)
        response = self._ensure_output_sections(response, draft_plan, doc_type)
        result = DocumentValidator.validate_document(response, doc_type or "")
        try:
            issues_to_fix = [
                issue.message for issue in result.issues if issue.level in {"critical", "warning"}
            ]
            if not result.passed and issues_to_fix:
                fix_prompt = self._build_repair_prompt(
                    original_output=response,
                    issues=issues_to_fix[:5],
                    draft_plan=draft_plan,
                    structure_guide=structure_guide,
                    rag_context=rag_context,
                )
                response = await self.chat(fix_prompt)
                response = self._ensure_output_sections(response, draft_plan, doc_type)
                result = DocumentValidator.validate_document(response, doc_type or "")
        except Exception:
            pass

        validation_info = f"输出模式: {draft_plan.draft_mode}；完整度: {draft_plan.completeness_score:.0%}；质量评分: {result.score:.0%}；通过: {result.passed}"

        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning=f"基于法律文书规范、专业模板和行业惯例生成。{validation_info}",
            actions=[{"type": "document_generated", "description": "文书起草完成"}],
            metadata={
                "draft_mode": draft_plan.draft_mode,
                "normalized_doc_type": draft_plan.normalized_doc_type,
                "completeness_score": draft_plan.completeness_score,
                "missing_fields": draft_plan.missing_fields,
                "validation_score": result.score,
            },
        )

    def _normalize_doc_type(self, doc_type: str) -> str:
        return DocumentValidator.normalize_doc_type(doc_type)

    def _assess_draft_plan(
        self,
        doc_type: str,
        description: str,
        requirements: dict[str, Any],
        scenario: str,
    ) -> DraftPlan:
        normalized = self._normalize_doc_type(doc_type)
        facts = self._build_completeness_checks(
            normalized=normalized,
            description=description,
            scenario=scenario,
            requirements=requirements,
        )
        missing = [name for name, present in facts.items() if not present]
        missing_fields = self._build_missing_field_items(normalized, missing)
        score = self._calculate_completeness_score(normalized, facts)
        if score >= 0.85:
            draft_mode = "成稿"
        elif score >= 0.45:
            draft_mode = "高可用草案"
        else:
            draft_mode = "结构化草稿"
        return DraftPlan(
            normalized_doc_type=normalized,
            draft_mode=draft_mode,
            missing_fields=missing_fields,
            completeness_score=score,
        )

    def _calculate_completeness_score(
        self,
        normalized: str,
        facts: dict[str, bool],
    ) -> float:
        specs = self._get_missing_field_specs(normalized)
        total_weight = 0.0
        present_weight = 0.0
        for label, present in facts.items():
            weight = float(specs.get(label, {}).get("weight", 1.0))
            total_weight += weight
            if present:
                present_weight += weight
        if total_weight <= 0:
            return 0.0
        return round(present_weight / total_weight, 2)

    def _build_missing_field_items(
        self,
        normalized: str,
        missing_labels: list[str],
    ) -> list[dict[str, str]]:
        specs = self._get_missing_field_specs(normalized)
        items: list[dict[str, str]] = []
        for label in missing_labels:
            spec: MissingFieldSpec = specs.get(label) or {}
            items.append(
                {
                    "key": label,
                    "label": label,
                    "severity": self._spec_text(spec, "severity", "medium"),
                    "group": self._spec_text(spec, "group", "基础信息"),
                    "suggestion": self._spec_text(
                        spec,
                        "suggestion",
                        f"建议补充：完善{label}相关事实",
                    ),
                    "weight": str(spec.get("weight", 1.0)),
                }
            )
        return items

    @staticmethod
    def _spec_text(spec: MissingFieldSpec, key: str, default: str) -> str:
        value = spec.get(key, default)
        return value if isinstance(value, str) else default

    def _sort_missing_fields(
        self,
        missing_fields: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        severity_rank = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            missing_fields,
            key=lambda item: (
                severity_rank.get(item["severity"], 3),
                -float(item.get("weight", "1.0")),
                item["label"],
            ),
        )

    def _get_missing_field_specs(self, normalized: str) -> dict[str, MissingFieldSpec]:
        common: dict[str, MissingFieldSpec] = {
            "主体信息": {
                "severity": "high",
                "group": "基础信息",
                "suggestion": "建议补充：明确文书涉及的主体身份与角色",
            },
            "事实细节": {
                "severity": "high",
                "group": "事实背景",
                "suggestion": "建议补充：按时间顺序说明关键事实经过",
            },
            "金额或核心条件": {
                "severity": "high",
                "group": "交易条件",
                "suggestion": "建议补充：明确金额、价格或核心商务条件",
            },
            "时间安排": {
                "severity": "medium",
                "group": "时间节点",
                "suggestion": "建议补充：明确起止日期、履行期限或关键时间点",
            },
        }
        if normalized == "contract":
            return {
                "合同金额与付款安排": {
                    "severity": "high",
                    "group": "交易条件",
                    "suggestion": "建议补充：明确合同总价、付款节点、付款条件",
                    "weight": 1.4,
                },
                "履行期限与交付节点": {
                    "severity": "high",
                    "group": "履行安排",
                    "suggestion": "建议补充：明确履行期限、交付时间和验收节点",
                    "weight": 1.3,
                },
                "服务/标的范围": {
                    "severity": "high",
                    "group": "标的范围",
                    "suggestion": "建议补充：明确服务内容、标的范围和交付标准",
                    "weight": 0.8,
                },
                "当事方信息": {
                    "severity": "high",
                    "group": "主体信息",
                    "suggestion": "建议补充：明确甲乙方名称、身份信息与联系方式",
                    "weight": 1.0,
                },
            }
        if normalized == "lawsuit":
            return {
                "原被告信息": {
                    "severity": "high",
                    "group": "诉讼主体",
                    "suggestion": "建议补充：明确原告、被告的完整身份信息",
                    "weight": 1.2,
                },
                "诉讼请求": {
                    "severity": "high",
                    "group": "诉讼请求",
                    "suggestion": "建议补充：逐项列明诉讼请求与诉请金额",
                    "weight": 1.4,
                },
                "事实与理由": {
                    "severity": "high",
                    "group": "案件事实",
                    "suggestion": "建议补充：说明争议经过、违约或侵权事实及法律依据",
                    "weight": 1.2,
                },
                "证据与法院信息": {
                    "severity": "medium",
                    "group": "程序信息",
                    "suggestion": "建议补充：明确证据材料及拟提交法院或仲裁机构",
                    "weight": 0.8,
                },
            }
        if normalized == "lawyer_letter":
            return {
                "委托人与收函对象": {
                    "severity": "high",
                    "group": "委托基础",
                    "suggestion": "建议补充：明确委托人、收函对象及双方关系",
                    "weight": 1.1,
                },
                "事实经过": {
                    "severity": "high",
                    "group": "事实背景",
                    "suggestion": "建议补充：简述争议事实、违约经过和催告背景",
                    "weight": 1.0,
                },
                "履行要求与期限": {
                    "severity": "high",
                    "group": "主张内容",
                    "suggestion": "建议补充：明确履行事项、履行方式和最后期限",
                    "weight": 1.4,
                },
                "法律后果提示": {
                    "severity": "medium",
                    "group": "风险控制",
                    "suggestion": "建议补充：说明逾期不履行将面临的诉讼、仲裁或其他法律后果",
                    "weight": 0.8,
                },
            }
        if normalized == "legal_opinion":
            return {
                "委托事项与范围": {
                    "severity": "high",
                    "group": "委托基础",
                    "suggestion": "建议补充：明确委托事项、审查范围和意见用途",
                    "weight": 1.2,
                },
                "事实前提": {
                    "severity": "high",
                    "group": "事实基础",
                    "suggestion": "建议补充：列明意见所依据的事实、文件和假设前提",
                    "weight": 1.1,
                },
                "法律分析焦点": {
                    "severity": "high",
                    "group": "分析框架",
                    "suggestion": "建议补充：明确需要分析的法律问题与风险焦点",
                    "weight": 1.1,
                },
                "结论与适用限制": {
                    "severity": "high",
                    "group": "结论边界",
                    "suggestion": "建议补充：明确核心结论、保留意见和适用限制",
                    "weight": 1.4,
                },
            }
        return common

    def _build_completeness_checks(
        self,
        *,
        normalized: str,
        description: str,
        scenario: str,
        requirements: dict[str, Any],
    ) -> dict[str, bool]:
        combined_text = f"{wrap_user_input(description, label='description')} {scenario}"
        parties_present = any(
            key in requirements
            for key in ["client", "target", "plaintiff", "defendant", "party_a", "party_b"]
        )
        if normalized == "contract":
            return {
                "当事方信息": parties_present,
                "合同金额与付款安排": any(
                    key in requirements for key in ["amount", "payment_terms", "price", "fee"]
                ),
                "履行期限与交付节点": any(
                    token in combined_text
                    for token in [
                        "期限",
                        "日期",
                        "时间",
                        "交付",
                        "付款",
                        "履行",
                        "完成",
                        "年度",
                        "月度",
                        "季度",
                    ]
                ),
                "服务/标的范围": bool(requirements.get("details") or scenario or description),
            }
        if normalized == "lawsuit":
            return {
                "原被告信息": any(key in requirements for key in ["plaintiff", "defendant"]),
                "诉讼请求": any(token in combined_text for token in ["诉讼请求", "请求", "判令"]),
                "事实与理由": bool(requirements.get("details") or scenario or description),
                "证据与法院信息": any(token in combined_text for token in ["证据", "法院", "仲裁"]),
            }
        if normalized == "lawyer_letter":
            return {
                "委托人与收函对象": parties_present,
                "事实经过": bool(requirements.get("details") or scenario or description),
                "履行要求与期限": any(
                    token in combined_text for token in ["期限", "日内", "履行", "付款", "整改"]
                ),
                "法律后果提示": any(
                    token in combined_text for token in ["诉讼", "仲裁", "法律后果"]
                ),
            }
        if normalized == "legal_opinion":
            return {
                "委托事项与范围": any(
                    key in requirements for key in ["scope", "mandate", "client", "matter"]
                ),
                "事实前提": bool(requirements.get("facts"))
                or any(token in combined_text for token in ["事实", "背景", "交易", "协议"]),
                "法律分析焦点": bool(requirements.get("issues"))
                or any(token in combined_text for token in ["法律", "合规", "风险", "条款"]),
                "结论与适用限制": any(
                    key in requirements for key in ["conclusion", "limitations", "reservation"]
                ),
            }
        return {
            "主体信息": parties_present,
            "事实细节": bool(requirements.get("details") or scenario or description),
            "金额或核心条件": "amount" in requirements,
            "时间安排": any(token in combined_text for token in ["期限", "日期", "时间"]),
        }

    def _build_prompt(
        self,
        *,
        doc_type: str,
        description: str,
        scenario: str,
        requirements: dict[str, Any],
        draft_plan: DraftPlan,
        structure_guide: str,
        rag_context: str,
    ) -> str:
        return f"""请根据以下任务单起草法律文书。
{rag_context}

【文书类型】{doc_type}
【输出模式】{draft_plan.draft_mode}
【需求描述】{description or scenario or '请根据用户输入识别'}
【场景背景】{scenario or '未单独提供'}
【已知信息】
{self._format_requirements(requirements)}
【缺失信息】
{self._format_missing_fields(draft_plan.missing_fields)}
【结构要求】
{structure_guide}

【输出要求】
1. 输出完整 Markdown 文书正文，不得只写原则性说明
2. 信息完整时按成稿标准写满关键条款
3. 信息不完整时保留专业占位，不得写“请按实际情况补充”
4. 合同类文书应包含明确条款编号、签署区、金额表达与争议解决
5. 函件、诉状、法律意见书必须包含对应结尾格式与结论部分
6. 文末必须严格包含以下区块：
---
## 起草说明
## 待确认事项
## 使用提示
"""

    def _build_repair_prompt(
        self,
        *,
        original_output: str,
        issues: list[str],
        draft_plan: DraftPlan,
        structure_guide: str,
        rag_context: str,
    ) -> str:
        joined_issues = "\n".join(f"- {item}" for item in issues)
        prioritized_missing_fields = self._format_repair_priorities(draft_plan.missing_fields)
        return f"""你刚才生成的法律文书未达到可交付标准，请基于下列问题重新输出完整文书。
{rag_context}

【当前输出模式】{draft_plan.draft_mode}
【必须修复的问题】
{joined_issues}
【结构要求】
{structure_guide}

【保留要求】
1. 保留原文中已正确的当事方和场景事实
2. 补齐缺失的核心条款、结构和结尾部分
3. 仍然输出完整正文，不要输出修订说明
4. 文末继续保留起草说明、待确认事项、使用提示三个区块

【优先补齐的待确认事项】
{prioritized_missing_fields}

【原始文书】
{original_output}
"""

    def _ensure_output_sections(self, text: str, draft_plan: DraftPlan, doc_type: str) -> str:
        content = text.rstrip()
        if "## 起草说明" not in content:
            content += f"\n\n---\n## 起草说明\n- 本文书按{draft_plan.draft_mode}标准起草，并依据当前已知事实补足基础结构。"
        if "## 待确认事项" not in content:
            content += "\n\n## 待确认事项\n" + self._format_missing_fields(
                draft_plan.missing_fields
            )
        if "## 使用提示" not in content:
            content += f"\n\n## 使用提示\n- 使用前请结合{doc_type or '文书类型'}的实际业务背景、附件和证据材料复核。"
        return content

    def _get_structure_guide(self, doc_type: str) -> str:
        """根据文书类型返回结构指南"""
        doc_type_lower = (doc_type or "").lower()

        if any(k in doc_type_lower for k in ["合同", "协议", "contract"]):
            return """【结构要求——合同类】：
必须包含以下完整结构：
- 合同标题（居中）
- 合同编号
- 甲乙双方信息（名称、统一社会信用代码/身份证号、法定代表人、地址、联系方式）
- 鉴于条款（背景说明）
- 第一条 定义与解释
- 第二条 合同标的（详细描述）
- 第三条 合同价款及支付（金额、方式、时间、发票）
- 第四条 双方权利与义务
- 第五条 履行期限、地点和方式
- 第六条 验收条款
- 第七条 知识产权（如适用）
- 第八条 保密条款
- 第九条 违约责任（明确违约金比例）
- 第十条 合同的变更和解除
- 第十一条 不可抗力
- 第十二条 争议解决
- 第十三条 通知与送达
- 第十四条 附则
- 签署区（甲方盖章/乙方盖章/日期）
- 附件列表"""

        if any(k in doc_type_lower for k in ["起诉", "诉状", "答辩"]):
            return """【结构要求——诉讼文书】：
必须包含以下结构：
- 文书标题（如"民事起诉状"）
- 原告信息（姓名/名称、性别、民族、出生日期、住所地、身份证号、联系方式）
- 被告信息（同上格式）
- 诉讼请求（逐项列明，用"一、""二、"编号）
- 事实与理由（按时间顺序叙述，引用证据和法律条文）
- 结尾（"此致 XX人民法院"）
- 具状人/日期
- 附件清单（副本份数、证据材料）"""

        if any(k in doc_type_lower for k in ["律师函", "催告", "通知"]):
            return """【结构要求——函件类】：
必须包含以下结构：
- 函件标题和编号
- 致函对象
- 委托说明段
- 一、基本事实
- 二、法律分析（引用具体法律条文）
- 三、律师意见
- 四、具体要求（含期限）
- 法律后果警示段
- 律所名称、承办律师签名、日期"""

        if any(k in doc_type_lower for k in ["法律意见", "尽职调查"]):
            return """【结构要求——法律意见书】：
必须包含以下结构：
- 文书标题
- 致函对象
- 一、引言（委托事项、范围、依据）
- 二、事实概述
- 三、法律分析（逐项分析，引用法条）
- 四、法律意见（结论性意见）
- 五、特别说明（假设前提、局限性）
- 律所名称、签名、日期"""

        return "【结构要求】：请按照该文书类型的专业格式规范起草，确保结构完整、内容充实。"

    def _format_requirements(self, requirements: dict[str, Any]) -> str:
        """格式化具体要求"""
        if not requirements:
            return "无特殊要求"

        lines = []
        for key, value in requirements.items():
            label = key
            if key == "client":
                label = "委托方/甲方"
            elif key == "target":
                label = "对方/乙方"
            elif key == "amount":
                label = "涉及金额"
            elif key == "details":
                label = "详细情况"
            lines.append(f"- {label}：{value}")
        return "\n".join(lines)

    def _format_missing_fields(self, missing_fields: list[dict[str, str]]) -> str:
        if not missing_fields:
            return "- 无关键缺失信息"
        return "\n".join(
            f"- {field['label']}：{field['suggestion']}（分组：{field['group']}，优先级：{field['severity']}）"
            for field in self._sort_missing_fields(missing_fields)
        )

    def _format_repair_priorities(self, missing_fields: list[dict[str, str]]) -> str:
        if not missing_fields:
            return "- 无待补齐事项"
        return "\n".join(
            f"- {field['label']}（优先级：{field['severity']}）：{field['suggestion']}"
            for field in self._sort_missing_fields(missing_fields)
        )

    async def draft_contract(
        self,
        contract_type: str,
        parties: dict[str, Any],
        terms: dict[str, Any],
    ) -> str:
        """起草合同"""
        structure_guide = self._get_structure_guide(contract_type)

        prompt = f"""请起草一份完整、专业的{contract_type}，信息如下：

当事方：
- 甲方：{parties.get('party_a', '待填写')}
- 乙方：{parties.get('party_b', '待填写')}

主要条款要求：
{self._format_terms(terms)}

{structure_guide}

【起草规范】：
1. 合同正文不少于3000字，至少包含12个条款
2. 使用"第X条"+"X.X"的编号体系
3. 违约金条款明确具体比例或计算方式
4. 争议解决条款明确管辖法院或仲裁机构
5. 需用户填写处用【】标注，并给出示例
6. 包含完整签署区和附件清单
"""
        return await self.chat(prompt)

    def _format_terms(self, terms: dict[str, Any]) -> str:
        """格式化条款信息"""
        if not terms:
            return "请根据合同类型生成标准条款"

        lines = []
        for key, value in terms.items():
            lines.append(f"- {key}：{value}")
        return "\n".join(lines)

    async def draft_letter(
        self,
        letter_type: str,
        sender: str,
        recipient: str,
        content: str,
    ) -> str:
        """起草函件"""
        prompt = f"""
请起草一份{letter_type}：

发函方：{sender}
收函方：{recipient}
主要内容：{wrap_user_input(content, label='content')}

请使用正式的法律函件格式。
"""
        return await self.chat(prompt)

    async def draft_lawsuit(
        self,
        case_type: str,
        plaintiff: dict[str, Any],
        defendant: dict[str, Any],
        claims: str,
        facts: str,
    ) -> str:
        """起草诉状"""
        prompt = f"""
请起草一份{case_type}起诉状：

原告信息：
{self._format_party(plaintiff)}

被告信息：
{self._format_party(defendant)}

诉讼请求：
{claims}

事实与理由：
{wrap_user_input(facts, label='facts')}

请按照起诉状的标准格式生成。
"""
        return await self.chat(prompt)

    def _format_party(self, party: dict[str, Any]) -> str:
        """格式化当事方信息"""
        if not party:
            return "待填写"

        lines = []
        for key, value in party.items():
            lines.append(f"  {key}：{value}")
        return "\n".join(lines)
