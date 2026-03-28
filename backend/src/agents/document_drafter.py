"""
文书起草智能体
"""

from typing import Any, Dict

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse


DOCUMENT_DRAFT_PROMPT = """你是一位专业的法律文书起草专家，精通各类法律文书的撰写，熟悉《中华人民共和国民法典》、《中华人民共和国公司法》、《中华人民共和国劳动合同法》等相关法律法规。

你的职责是：
1. 根据需求起草法律文书
2. 确保文书格式规范
3. 保证法律用语准确
4. 符合法律文书标准
5. 引用准确的法律条款

擅长的文书类型：
1. 合同类
   - 各类商业合同（买卖、租赁、借款等）
   - 劳动合同
   - 服务协议
   - 合作协议

2. 诉讼类
   - 民事起诉状
   - 民事答辩状
   - 上诉状
   - 财产保全申请书

3. 公司类
   - 公司章程
   - 股东会决议
   - 董事会决议
   - 股权转让协议

4. 函件类
   - 律师函
   - 催告函
   - 解除合同通知书
   - 法律意见书

5. 其他
   - 授权委托书
   - 承诺书
   - 遗嘱

起草原则：
1. 结构完整：标题、当事人信息、正文（事实、理由、请求/约定）、结尾（签署、日期）齐全。
2. 表述准确：法律术语使用规范，避免歧义。
3. 逻辑清晰：条款排列有序，权利义务对等或明确。
4. 内容完备：核心要素齐全，风险防控到位。
5. 格式规范：符合司法实践中的通用格式要求。

注意事项：
- 使用 Markdown 格式输出。
- 标题使用 # 一级标题。
- 小标题使用 ## 二级标题或 ### 三级标题。
- 需要用户填写的部分请使用【】或 ______ 标注。
- 引用法律条文时，请确保准确性。
"""


class DocumentDraftAgent(BaseLegalAgent):
    """文书起草智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="文书起草Agent",
            role="法律文书专家",
            description="起草各类法律文书、合同、函件",
            system_prompt=DOCUMENT_DRAFT_PROMPT,
            tools=["template_library", "document_generator"],
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理文书起草任务"""
        description = task.get("description", "")
        context = task.get("context", {})
        doc_type = context.get("doc_type", "")
        requirements = context.get("requirements", {})
        
        # 构建更详细的起草提示
        prompt = f"""
请根据以下需求起草一份专业的法律文书：

【文书类型】：{doc_type or '请根据需求判断'}
【需求描述】：{description}
【具体要求】：
{self._format_requirements(requirements)}

请提供：
1. 完整的法律文书内容。
2. 使用 Markdown 格式。
3. 包含所有必要的条款（如违约责任、争议解决等）。
4. 标注需要填写的信息位置（用【】标注）。
5. 文书末尾请附上起草说明或风险提示（如有）。

开始起草：
"""
        
        # 调用Agent
        response = await self.chat(prompt)
        
        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于法律文书规范和模板库生成",
            actions=[
                {"type": "document_generated", "description": "文书起草完成"}
            ]
        )

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
        prompt = f"""
请起草一份{contract_type}，信息如下：

当事方：
- 甲方：{parties.get('party_a', '待填写')}
- 乙方：{parties.get('party_b', '待填写')}

主要条款：
{self._format_terms(terms)}

请生成完整的合同文本，包含所有必要条款。
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
