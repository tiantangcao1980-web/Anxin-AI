"""
找律师 — AI 智能匹配服务

核心能力：
1. AI 案情分析：对用户描述进行法律要素提取 + 领域识别 + 风险评估
2. 自动脱敏：移除个人信息（姓名、电话、身份证、地址等）生成匿名摘要
3. 智能匹配：根据案情特征匹配最合适的律师（领域、评分、距离、价格）
4. 匹配评分：为每位律师计算匹配度分数
"""

import re
from collections import defaultdict
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ===== 脱敏正则 =====

# 中国手机号
RE_PHONE = re.compile(r"1[3-9]\d{9}")
# 身份证号
RE_ID_CARD = re.compile(
    r"[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]"
)
# 邮箱
RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# 银行卡号（16-19位数字）
RE_BANK_CARD = re.compile(r"\b\d{16,19}\b")
# 中文姓名模式（常见2-4字姓名，前面有"我叫""姓名""本人"等关键词）
RE_CN_NAME = re.compile(r"(?:我叫|姓名[：:]?\s*|本人|我是)\s*([^\s,，。；;、]{2,4})")
# 详细地址（包含省市区+具体地址）
RE_ADDRESS = re.compile(r"[\u4e00-\u9fa5]{2,}(?:省|市|区|县|镇|村|路|街|号|栋|单元|室|楼)")
# 公司具体名称（在需要完全匿名时使用）
RE_COMPANY = re.compile(r"[\u4e00-\u9fa5]{2,}(?:有限公司|股份有限公司|集团|科技|实业|贸易|咨询)")


def anonymize_text(text: str, level: str = "standard") -> str:
    """
    文本脱敏

    Args:
        text: 原始文本
        level: 脱敏级别
          - 'standard': 标准脱敏（手机号、身份证、邮箱、银行卡、姓名）
          - 'strict': 严格脱敏（额外脱敏地址、公司名称）

    Returns:
        脱敏后的文本
    """
    result = text

    # 手机号 → 1xx****xxxx
    result = RE_PHONE.sub(lambda m: m.group()[:3] + "****" + m.group()[-4:], result)

    # 身份证 → 前6后4
    result = RE_ID_CARD.sub(lambda m: m.group()[:6] + "********" + m.group()[-4:], result)

    # 邮箱 → 首字母***@域名
    result = RE_EMAIL.sub(lambda m: m.group()[0] + "***@" + m.group().split("@")[1], result)

    # 银行卡号 → 前4后4
    result = RE_BANK_CARD.sub(lambda m: m.group()[:4] + "****" + m.group()[-4:], result)

    # 中文姓名 → X某
    def replace_name(m: re.Match[str]) -> str:
        full = m.group(0)
        name = m.group(1)
        return full.replace(name, name[0] + "某")

    result = RE_CN_NAME.sub(replace_name, result)

    if level == "strict":
        # 详细地址 → [某地]
        result = RE_ADDRESS.sub("[某地]", result)
        # 公司名称 → [某公司]
        result = RE_COMPANY.sub("[某公司]", result)

    return result


# ===== 法律领域关键词映射 =====

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "contract": ["合同", "违约", "签约", "约定", "条款", "履行", "解约", "买卖", "租赁", "借款"],
    "labor": ["劳动", "工资", "辞退", "社保", "加班", "竞业", "工伤", "劳务", "离职", "裁员"],
    "ip": ["专利", "商标", "著作权", "版权", "侵权", "仿冒", "抄袭", "知识产权", "注册"],
    "corporate": ["公司", "股权", "股东", "董事", "法人", "章程", "增资", "减资", "清算", "并购"],
    "litigation": ["起诉", "被告", "原告", "法院", "判决", "上诉", "执行", "仲裁", "调解", "赔偿"],
    "compliance": ["合规", "审查", "监管", "行政处罚", "许可证", "资质", "备案", "整改"],
    "criminal": ["刑事", "犯罪", "拘留", "逮捕", "公安", "检察", "取保", "诈骗", "盗窃", "伤害"],
    "real_estate": ["房产", "房屋", "拆迁", "土地", "产权", "过户", "物业", "业主"],
    "family": ["离婚", "抚养", "财产分割", "婚姻", "继承", "遗产", "监护"],
    "debt": ["债务", "欠款", "借贷", "催收", "担保", "抵押", "逾期", "坏账"],
}

DOMAIN_LABELS: dict[str, str] = {
    "contract": "合同纠纷",
    "labor": "劳动争议",
    "ip": "知识产权",
    "corporate": "公司治理",
    "litigation": "民事诉讼",
    "compliance": "合规审查",
    "criminal": "刑事案件",
    "real_estate": "房产纠纷",
    "family": "婚姻家庭",
    "debt": "债务纠纷",
}

URGENCY_WEIGHTS = {"low": 0.5, "medium": 1.0, "high": 1.5, "urgent": 2.0}
_MATCHING_EXPOSURE_COUNTER: dict[str, int] = defaultdict(int)


def detect_legal_domain(text: str) -> tuple[str, float]:
    """
    自动识别法律领域

    Returns:
        (domain_code, confidence)
    """
    scores: dict[str, int] = {}
    text_lower = text.lower()

    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[domain] = score

    if not scores:
        return "other", 0.0

    best = max(scores, key=scores.get)  # type: ignore
    total_hits = sum(scores.values())
    confidence = min(0.95, scores[best] / max(total_hits, 1) * 0.7 + min(scores[best], 5) * 0.06)

    return best, round(confidence, 2)


def extract_risk_level(text: str) -> str:
    """从描述中提取风险等级"""
    high_risk = ["紧急", "严重", "巨额", "犯罪", "拘留", "逮捕", "重大", "恶意", "欺诈"]
    medium_risk = ["纠纷", "争议", "违约", "起诉", "赔偿", "投诉", "处罚"]

    text_lower = text.lower()
    if any(kw in text_lower for kw in high_risk):
        return "high"
    if any(kw in text_lower for kw in medium_risk):
        return "medium"
    return "low"


def extract_legal_elements(text: str) -> dict[str, Any]:
    """
    提取法律要素

    Returns:
        包含主体、标的、争议焦点等法律要素
    """
    elements: dict[str, Any] = {
        "parties_mentioned": [],
        "amounts_mentioned": [],
        "dates_mentioned": [],
        "legal_basis": [],
        "dispute_focus": "",
    }

    # 金额提取
    amount_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(?:万|元|块|千|百万|亿)")
    amounts = amount_pattern.findall(text)
    elements["amounts_mentioned"] = [float(a) for a in amounts[:5]]

    # 日期提取
    date_pattern = re.compile(r"(\d{4})[年/.-](\d{1,2})[月/.-]?(\d{1,2})?")
    dates = date_pattern.findall(text)
    elements["dates_mentioned"] = [f"{y}-{m}{'-' + d if d else ''}" for y, m, d in dates[:5]]

    # 法律依据提取
    law_pattern = re.compile(r"《([^》]+)》")
    laws = law_pattern.findall(text)
    elements["legal_basis"] = laws[:5]

    return elements


class LawyerMatchingService:
    """找律师智能匹配服务"""

    async def analyze_case(
        self,
        description: str,
        user_domain: str | None = None,
    ) -> dict[str, Any]:
        """
        AI 案情分析

        Args:
            description: 用户描述的法律问题
            user_domain: 用户选择的法律领域（可选）

        Returns:
            {
                'anonymous_summary': 脱敏后的匿名摘要,
                'legal_domain': 识别的法律领域,
                'domain_label': 领域中文名,
                'domain_confidence': 识别置信度,
                'risk_level': 风险等级,
                'legal_elements': 法律要素,
                'recommended_specializations': 建议的律师专业方向,
                'urgency_assessment': 紧急程度评估,
            }
        """
        # 1. 文本脱敏
        anonymous = anonymize_text(description, level="standard")

        # 2. 领域识别
        detected_domain, confidence = detect_legal_domain(description)
        # 用户手动选择的优先级更高
        final_domain = user_domain if user_domain and user_domain != "other" else detected_domain
        domain_label = DOMAIN_LABELS.get(final_domain, "综合法务")

        # 3. 风险评估
        risk_level = extract_risk_level(description)

        # 4. 法律要素提取
        elements = extract_legal_elements(description)

        # 5. 生成结构化摘要
        summary_parts = [f"[{domain_label}]"]
        if risk_level == "high":
            summary_parts.append("[紧急]")
        summary_parts.append(anonymous[:300])
        if elements["amounts_mentioned"]:
            summary_parts.append(f"\n涉及金额：约 {max(elements['amounts_mentioned'])} 万元")
        if elements["legal_basis"]:
            summary_parts.append(f"\n相关法规：{'、'.join(elements['legal_basis'][:3])}")

        anonymous_summary = "".join(summary_parts)

        # 6. 推荐律师专业方向
        specializations = [domain_label]
        # 如果检测到多个领域相关，加入次要方向
        all_domains = {
            d: s
            for d, s in (
                (d, sum(1 for kw in kws if kw in description.lower()))
                for d, kws in DOMAIN_KEYWORDS.items()
            )
            if s > 0
        }
        for d in sorted(all_domains, key=all_domains.get, reverse=True)[:3]:  # type: ignore
            label = DOMAIN_LABELS.get(d, "")
            if label and label not in specializations:
                specializations.append(label)

        # 7. 尝试调用 LLM 进行更深度的分析（可选，失败则用规则引擎结果）
        llm_summary = await self._llm_analyze(description, domain_label, anonymous)

        if llm_summary:
            anonymous_summary = llm_summary

        return {
            "anonymous_summary": anonymous_summary,
            "legal_domain": final_domain,
            "domain_label": domain_label,
            "domain_confidence": confidence,
            "risk_level": risk_level,
            "legal_elements": elements,
            "recommended_specializations": specializations,
            "urgency_assessment": "high" if risk_level == "high" else "normal",
        }

    async def _llm_analyze(
        self,
        description: str,
        domain_label: str,
        anonymized: str,
    ) -> str | None:
        """调用 LLM 生成更精细的匿名案情摘要"""
        try:
            from src.services import llm_service as llm_module

            llm_service = getattr(llm_module, "llm_service", None)
            if llm_service is None:
                return None

            prompt = f"""你是一名专业的法律顾问助手。请对以下法律咨询进行分析，生成一段匿名案情摘要。

要求：
1. 移除所有个人信息（姓名、电话、地址、公司名等），用"当事人""对方""某公司"等代替
2. 保留法律事实要素（时间、金额、行为、后果）
3. 识别核心法律问题和争议焦点
4. 评估案件复杂度和紧急程度
5. 控制在200字以内

法律领域：{domain_label}

原始描述（仅用于分析，不得在摘要中暴露个人信息）：
{description[:1000]}

请直接输出匿名案情摘要，不要添加标题或格式标记："""

            result = await llm_service.chat(prompt, max_tokens=500)
            if result and len(result) > 20:
                # 二次脱敏确保安全
                return anonymize_text(result, level="strict")
        except Exception as e:
            logger.debug(f"LLM 分析不可用，使用规则引擎: {e}")

        return None

    async def match_lawyers(
        self,
        db: AsyncSession,
        domain: str,
        urgency: str = "medium",
        city: str | None = None,
        specializations: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        智能匹配律师

        评分维度：
        - 领域匹配度 (40%) — 律师专业方向是否包含目标领域
        - 评分 (25%) — 用户评价分数
        - 活跃度 (20%) — 在线状态、接单量
        - 性价比 (15%) — 价格区间合理性

        Returns:
            按匹配分数降序排列的律师列表
        """
        from src.models.lawyer_matching import LawyerProfile

        query = select(LawyerProfile).where(
            LawyerProfile.is_verified == True,
            LawyerProfile.is_accepting == True,
        )

        if city:
            query = query.where(LawyerProfile.city == city)

        result = await db.execute(query.limit(50))
        all_lawyers = result.scalars().all()

        if not all_lawyers:
            return []

        domain_label = DOMAIN_LABELS.get(domain, "")
        urgency_weight = URGENCY_WEIGHTS.get(urgency, 1.0)

        scored: list[tuple[Any, float]] = []

        for lp in all_lawyers:
            score = 0.0

            # 领域匹配度 (40分)
            specs = lp.specializations or []
            if isinstance(specs, str):
                specs = [specs]
            domain_match = (
                any(
                    domain_label in s
                    or domain in s
                    or (specializations and any(sp in s for sp in specializations))
                    for s in specs
                )
                if specs
                else False
            )
            score += 40 if domain_match else 10  # 未匹配也给基础分

            # 评分 (25分)
            score += min(25, (lp.rating or 0) * 5)

            # 活跃度 (20分)
            if lp.is_online:
                score += 15
            score += min(5, (lp.total_cases or 0) / 20)

            # 紧急加权（紧急时优先在线律师）
            if urgency in ("high", "urgent") and lp.is_online:
                score += min(20, 10 * urgency_weight)

            scored.append((lp, round(score, 1)))

        # 排序：先按匹配分，再对同分律师按曝光次数做轮询，避免长期先到先得。
        scored.sort(key=lambda x: (-x[1], _MATCHING_EXPOSURE_COUNTER[str(x[0].id)], str(x[0].id)))

        selected = scored[:limit]
        for lp, _score in selected:
            _MATCHING_EXPOSURE_COUNTER[str(lp.id)] += 1

        return [
            {
                "id": lp.id,
                "real_name": lp.real_name,
                "license_number": lp.license_number,
                "law_firm": lp.law_firm,
                "years_of_practice": lp.years_of_practice,
                "city": lp.city,
                "specializations": lp.specializations or [],
                "bio": lp.bio,
                "avatar_url": lp.avatar_url,
                "rating": lp.rating,
                "total_cases": lp.total_cases,
                "success_cases": lp.success_cases,
                "hourly_rate_min": lp.hourly_rate_min,
                "hourly_rate_max": lp.hourly_rate_max,
                "is_online": lp.is_online,
                "is_verified": lp.is_verified,
                "match_score": score,
                "match_reason": "领域匹配" if domain_match else "综合推荐",
            }
            for lp, score in selected
        ]


# 全局实例
lawyer_matching_service = LawyerMatchingService()
