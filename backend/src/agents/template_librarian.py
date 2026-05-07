"""
模板管理员 Agent

当用户需求被识别为 TEMPLATE_REQUEST（"给我一个合同模板"、"下载租赁合同范本"）时，
不走 AI 生成流程，而是从模板库中查询匹配的模板并返回下载链接。

Harness 设计理念：区分"模板请求"和"生成请求"，避免不必要的 LLM 调用和等待。
"""

from typing import Any

from loguru import logger

from src.agents.base import AgentResponse

# ===== 内置模板注册表 =====
# 实际生产环境应从数据库/知识库动态加载
TEMPLATE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "tpl_sales_contract",
        "name": "商品买卖合同",
        "category": "合同",
        "sub_category": "买卖合同",
        "description": "适用于商品买卖交易，包含标的物、价款、交付、质量保证等条款",
        "applicable_keywords": ["买卖", "销售", "货物", "货款", "商品"],
        "download_path": "/api/v1/knowledge/templates/sales-contract",
        "format": "docx",
        "version": "2.0",
    },
    {
        "id": "tpl_rental_contract",
        "name": "房屋租赁合同",
        "category": "合同",
        "sub_category": "租赁合同",
        "description": "适用于住宅或商业房屋租赁，包含租期、租金、押金、维修责任等条款",
        "applicable_keywords": ["租赁", "租房", "出租", "房屋", "租金"],
        "download_path": "/api/v1/knowledge/templates/rental-contract",
        "format": "docx",
        "version": "2.0",
    },
    {
        "id": "tpl_labor_contract",
        "name": "劳动合同",
        "category": "合同",
        "sub_category": "劳动合同",
        "description": "适用于建立劳动关系，包含岗位、薪酬、工时、保密、竞业限制等条款",
        "applicable_keywords": ["劳动", "雇佣", "入职", "员工", "劳动合同"],
        "download_path": "/api/v1/knowledge/templates/labor-contract",
        "format": "docx",
        "version": "2.0",
    },
    {
        "id": "tpl_service_contract",
        "name": "服务合同",
        "category": "合同",
        "sub_category": "服务合同",
        "description": "适用于各类服务外包和咨询服务，包含服务内容、标准、验收、付款等条款",
        "applicable_keywords": ["服务", "外包", "咨询", "顾问", "技术服务"],
        "download_path": "/api/v1/knowledge/templates/service-contract",
        "format": "docx",
        "version": "1.0",
    },
    {
        "id": "tpl_nda",
        "name": "保密协议 (NDA)",
        "category": "合同",
        "sub_category": "保密协议",
        "description": "适用于保护商业秘密和机密信息，包含保密范围、义务、期限、违约责任",
        "applicable_keywords": ["保密", "NDA", "商业秘密", "机密"],
        "download_path": "/api/v1/knowledge/templates/nda",
        "format": "docx",
        "version": "1.0",
    },
    {
        "id": "tpl_lawyer_letter",
        "name": "律师函模板",
        "category": "文书",
        "sub_category": "律师函",
        "description": "通用律师函模板，包含催告、警告、解除通知等用途",
        "applicable_keywords": ["律师函", "催告", "催款函", "警告函"],
        "download_path": "/api/v1/knowledge/templates/lawyer-letter",
        "format": "docx",
        "version": "1.0",
    },
    {
        "id": "tpl_legal_opinion",
        "name": "法律意见书模板",
        "category": "文书",
        "sub_category": "法律意见书",
        "description": "正式法律意见书模板，包含事实描述、法律分析、结论建议等部分",
        "applicable_keywords": ["法律意见", "法律意见书", "意见书"],
        "download_path": "/api/v1/knowledge/templates/legal-opinion",
        "format": "docx",
        "version": "1.0",
    },
    {
        "id": "tpl_complaint",
        "name": "民事起诉状模板",
        "category": "文书",
        "sub_category": "起诉状",
        "description": "民事诉讼起诉状模板，包含当事人信息、诉讼请求、事实理由等",
        "applicable_keywords": ["起诉状", "起诉", "诉讼", "民事起诉"],
        "download_path": "/api/v1/knowledge/templates/complaint",
        "format": "docx",
        "version": "1.0",
    },
    {
        "id": "tpl_equity_transfer",
        "name": "股权转让协议",
        "category": "合同",
        "sub_category": "股权转让",
        "description": "适用于公司股权转让交易，包含转让价格、付款方式、过渡期安排等",
        "applicable_keywords": ["股权转让", "股权", "转让协议", "股份"],
        "download_path": "/api/v1/knowledge/templates/equity-transfer",
        "format": "docx",
        "version": "1.0",
    },
    {
        "id": "tpl_investment_agreement",
        "name": "投资协议模板",
        "category": "合同",
        "sub_category": "投资协议",
        "description": "适用于股权投资，包含投资条款、估值、对赌、反稀释、退出等",
        "applicable_keywords": ["投资", "融资", "投资协议", "对赌"],
        "download_path": "/api/v1/knowledge/templates/investment-agreement",
        "format": "docx",
        "version": "1.0",
    },
]


class TemplateLirarianAgent:
    """
    模板管理员 Agent

    从模板库中查询匹配的模板，返回结构化的模板列表。
    不调用 LLM，纯规则匹配，响应时间 < 10ms。
    """

    def __init__(self) -> None:
        self.name = "模板管理员"
        self.role = "template_librarian"
        self.templates = TEMPLATE_CATALOG

    def get_info(self) -> dict[str, Any]:
        """返回智能体元信息，保持与其他 Agent 的查询契约一致。"""
        return {
            "name": self.name,
            "role": self.role,
            "description": "从模板库中检索匹配模板，并引导用户下载或切换到 AI 定制生成。",
            "tools": ["template_library", "knowledge_base_navigation"],
        }

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """
        处理模板请求

        Args:
            task: {"description": "给我一份买卖合同模板", ...}

        Returns:
            AgentResponse 包含匹配的模板列表
        """
        description = task.get("description", "")
        logger.info(f"[TemplateLirarianAgent] 查询模板: {description[:50]}")

        # 关键词匹配模板
        matched = self._match_templates(description)

        if matched:
            # 构建友好的回复
            template_list = "\n".join([
                f"📄 **{t['name']}**\n"
                f"   {t['description']}\n"
                f"   类型: {t['category']}/{t['sub_category']} | 格式: {t['format'].upper()}"
                for t in matched
            ])

            content = (
                f"为您找到 {len(matched)} 个相关模板：\n\n"
                f"{template_list}\n\n"
                f"您可以在 **法律智库** 中下载这些模板。\n\n"
                f"💡 如果模板不能满足您的需求，我也可以根据您的具体情况 **AI 定制生成** 一份完整的法律文件。"
            )

            return AgentResponse(
                agent_name="模板管理员",
                content=content,
                metadata={
                    "response_type": "template_list",
                    "templates": matched,
                    "template_count": len(matched),
                    "has_ai_fallback": True,
                },
                actions=[
                    {"type": "navigate", "label": "前往法律智库", "url": "/knowledge-base?tab=templates"},
                    {"type": "action", "label": "AI 定制生成", "action": "switch_to_generation"},
                ],
            )
        else:
            # 没有匹配的模板
            content = (
                "抱歉，暂时没有找到完全匹配的模板。\n\n"
                "您可以：\n"
                "1. 📚 前往 **法律智库** 浏览全部模板\n"
                "2. 🤖 让 AI 根据您的需求 **定制生成** 一份法律文件\n\n"
                "请问您想选择哪种方式？"
            )

            return AgentResponse(
                agent_name="模板管理员",
                content=content,
                metadata={
                    "response_type": "no_template_match",
                    "templates": [],
                    "template_count": 0,
                    "has_ai_fallback": True,
                },
                actions=[
                    {"type": "navigate", "label": "浏览法律智库", "url": "/knowledge-base?tab=templates"},
                    {"type": "action", "label": "AI 定制生成", "action": "switch_to_generation"},
                ],
            )

    def _match_templates(self, query: str) -> list[dict[str, Any]]:
        """基于关键词匹配模板"""
        query_lower = query.lower()
        scored = []

        for tpl in self.templates:
            score = 0
            for kw in tpl["applicable_keywords"]:
                if kw in query_lower:
                    score += 1
            # 模板名称匹配
            if tpl["name"] in query:
                score += 2
            if tpl["sub_category"] in query:
                score += 1

            if score > 0:
                scored.append((score, tpl))

        # 按匹配度排序，返回前 5 个
        scored.sort(key=lambda x: x[0], reverse=True)
        return [tpl for _, tpl in scored[:5]]
