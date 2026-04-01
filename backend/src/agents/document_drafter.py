"""
文书起草智能体
"""

from typing import Any, Dict

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse
from src.prompts import load_prompt


_FALLBACK_PROMPT = "你是一位专业的法律文书起草专家，精通各类法律文书的撰写。"


class DocumentDraftAgent(BaseLegalAgent):
    """文书起草智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="文书起草Agent",
            role="法律文书专家",
            description="起草各类法律文书、合同、函件",
            system_prompt=load_prompt("agents/document_drafter.txt", fallback=_FALLBACK_PROMPT),
            tools=["template_library", "document_generator"],
        )
        super().__init__(config)
    
    # 各文书类型的最低条款数要求
    _MIN_CLAUSE_REQUIREMENTS = {
        "合同": 12,
        "协议": 10,
        "起诉状": 0,
        "律师函": 0,
        "法律意见": 0,
    }

    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理文书起草任务"""
        description = task.get("description", "")
        context = task.get("context", {})
        doc_type = context.get("doc_type", "")
        requirements = context.get("requirements", {})
        scenario = context.get("scenario", "")

        # 获取文书类型专项结构指南
        structure_guide = self._get_structure_guide(doc_type)

        # 构建增强的起草提示
        prompt = f"""请根据以下需求起草一份**完整、专业、可直接使用**的法律文书：

【文书类型】：{doc_type or '请根据需求判断'}
【需求描述】：{description}
{f'【场景背景】：{scenario}' if scenario else ''}
【具体要求】：
{self._format_requirements(requirements)}

{structure_guide}

【起草规范（必须遵守）】：
1. 输出完整的法律文书，禁止省略或用"..."代替内容
2. 合同类文书不得少于3000字，必须包含至少10个条款
3. 使用规范的 Markdown 格式输出：
   - 合同标题用 # 一级标题
   - 各条用 ## 二级标题，格式"第X条 条款名称"
   - 条款内容用 X.X 编号，子条款用（1）（2）编号
4. 需要用户填写的信息用【】标注，并附示例说明
5. 合同金额同时标注阿拉伯数字和大写中文
6. 必须包含完整的签署区（甲方/乙方盖章、签字、日期）
7. 在文书末尾添加"---"分隔线后附上"起草说明"，解释重要条款的设置理由

开始起草：
"""

        # 调用Agent
        response = await self.chat(prompt)

        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于法律文书规范、专业模板和行业惯例生成",
            actions=[
                {"type": "document_generated", "description": "文书起草完成"}
            ]
        )

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

    def _format_requirements(self, requirements: Dict[str, Any]) -> str:
        """格式化具体要求"""
        if not requirements:
            return "无特殊要求"
        
        lines = []
        for key, value in requirements.items():
            # 转换key为中文描述（如果是英文）
            label = key
            if key == "client": label = "委托方/甲方"
            elif key == "target": label = "对方/乙方"
            elif key == "amount": label = "涉及金额"
            elif key == "details": label = "详细情况"
            
            lines.append(f"- {label}：{value}")
        return "\n".join(lines)

    
    async def draft_contract(
        self,
        contract_type: str,
        parties: Dict[str, Any],
        terms: Dict[str, Any],
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
    
    def _format_terms(self, terms: Dict[str, Any]) -> str:
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
主要内容：{content}

请使用正式的法律函件格式。
"""
        return await self.chat(prompt)
    
    async def draft_lawsuit(
        self,
        case_type: str,
        plaintiff: Dict[str, Any],
        defendant: Dict[str, Any],
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
{facts}

请按照起诉状的标准格式生成。
"""
        return await self.chat(prompt)
    
    def _format_party(self, party: Dict[str, Any]) -> str:
        """格式化当事方信息"""
        if not party:
            return "待填写"
        
        lines = []
        for key, value in party.items():
            lines.append(f"  {key}：{value}")
        return "\n".join(lines)
