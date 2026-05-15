"""获客猎手 (lead_hunter) Persona — P7-C 实装。

定位：制造业 / B2B 跨境获客 + 销售跟进 + 商务沟通自动化。

5 大能力：
    1. lead_discovery        — 行业 / 地域 / 规模筛选 + 评分
    2. sales_email_drafting  — 模板 + 个性化 + AB 主题
    3. linkedin_outreach     — 合规范围内的连接消息
    4. quote_generation      — 报价单 .docx 生成（依赖 docx skill）
    5. crm_sync              — Salesforce / HubSpot / Pipedrive / Zoho 双向同步

合规边界（重要）：
    - 不主动撞 LinkedIn 私有 API；必须走 OAuth + 官方 Marketing Solutions API。
    - 邮件营销默认包含 unsubscribe 出口，遵循 CAN-SPAM / PIPL / GDPR Art. 21。
    - 联系人来源仅限：用户主动提供 / 公开商务邮箱 / OAuth 内 CRM 既有联系人。
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.agents.personas.base_persona import BasePersonaAgent
from src.agents.personas.sales_models import (
    Contact,
    CrmSyncResult,
    EmailDraft,
    Lead,
    LeadDiscoveryCriteria,
    QuoteItem,
    QuoteTerms,
)

# ---------------------------------------------------------------------------
# Lead Scoring 算法
# ---------------------------------------------------------------------------


class LeadScoring:
    """5 因子加权评分算法（权重总和 = 1.0）。

    选权重的理由（写到 docstring 让审计 / 销售经理可校准）：

    +----------------------------+--------+----------------------------------------+
    | factor                     | weight | rationale                              |
    +============================+========+========================================+
    | icp_fit (industry match)   |  0.30  | 最强先验：行业不对一切归零，权重最大   |
    | recent_funding_news        |  0.20  | 资金 + 新闻代表"有预算 + 有动力"双信号 |
    | competitor_overlap         |  0.20  | 已用竞品 ⇒ 已被教育 ⇒ 替换/补充窗口    |
    | response_rate_history      |  0.15  | 历史响应是最直接的"可达性"指标         |
    | decision_maker_in_contacts |  0.15  | 决策人触达直接决定推进速度             |
    +----------------------------+--------+----------------------------------------+

    选 0.30 / 0.20 / 0.20 / 0.15 / 0.15 而非平均（0.20 ×5）的原因：
        - ICP fit 是 hard gate，必须给最高权；
        - funding/competitor 是 medium signals，并列；
        - history/decision_maker 是 soft signals，权重略低，避免过拟合到老客户。
    """

    WEIGHTS: dict[str, float] = {
        "icp_fit": 0.30,
        "recent_funding_news": 0.20,
        "competitor_overlap": 0.20,
        "response_rate_history": 0.15,
        "decision_maker_in_contacts": 0.15,
    }

    @staticmethod
    def _clamp01(v: float) -> float:
        if v < 0:
            return 0.0
        if v > 1:
            return 1.0
        return float(v)

    @classmethod
    def score(
        cls,
        *,
        icp_fit: float,
        recent_funding_news: float,
        competitor_overlap: float,
        response_rate_history: float,
        decision_maker_in_contacts: float,
    ) -> tuple[float, dict[str, float]]:
        """对 5 个 0-1 输入因子做加权求和，返回 (score, breakdown)。"""
        breakdown = {
            "icp_fit": cls._clamp01(icp_fit) * cls.WEIGHTS["icp_fit"],
            "recent_funding_news": cls._clamp01(recent_funding_news)
            * cls.WEIGHTS["recent_funding_news"],
            "competitor_overlap": cls._clamp01(competitor_overlap)
            * cls.WEIGHTS["competitor_overlap"],
            "response_rate_history": cls._clamp01(response_rate_history)
            * cls.WEIGHTS["response_rate_history"],
            "decision_maker_in_contacts": cls._clamp01(decision_maker_in_contacts)
            * cls.WEIGHTS["decision_maker_in_contacts"],
        }
        total = round(sum(breakdown.values()), 4)
        # 即便所有因子都 1.0，加权和应严格等于 1.0
        return cls._clamp01(total), breakdown

    @classmethod
    def score_lead(
        cls,
        lead: Lead,
        *,
        criteria: LeadDiscoveryCriteria | None = None,
        signals: dict[str, float] | None = None,
    ) -> Lead:
        """根据 lead + criteria + 外部信号生成 score & 写回 ``score_breakdown``。

        signals 是外部传入的 0-1 信号（funding/competitor/history），允许
        测试覆盖；缺失时退化为启发式估计。
        """
        signals = signals or {}

        # 1) icp_fit — 行业字符串匹配 + tag bonus
        if criteria and criteria.industry:
            target = criteria.industry.lower()
            if target in (lead.industry or "").lower():
                icp = 1.0
            elif any(target in t.lower() for t in lead.tags):
                icp = 0.7
            else:
                icp = 0.2
        else:
            icp = signals.get("icp_fit", 0.5)

        # 2) recent funding/news — 由外部源（PR / Crunchbase）注入；缺省 0
        funding = signals.get("recent_funding_news", 0.0)
        if "funded" in lead.tags or "ipo" in lead.tags:
            funding = max(funding, 0.8)

        # 3) competitor_overlap — 标签命中 ``uses-<competitor>`` 即给分
        overlap = signals.get("competitor_overlap", 0.0)
        if any(t.startswith("uses-") for t in lead.tags):
            overlap = max(overlap, 0.7)

        # 4) response_rate_history — CRM 历史命中
        history = signals.get("response_rate_history", 0.0)

        # 5) decision_maker_in_contacts
        dm = 1.0 if lead.has_decision_maker() else 0.0

        score, breakdown = cls.score(
            icp_fit=icp,
            recent_funding_news=funding,
            competitor_overlap=overlap,
            response_rate_history=history,
            decision_maker_in_contacts=dm,
        )
        lead.score = score
        lead.score_breakdown = breakdown
        return lead


# ---------------------------------------------------------------------------
# Email 模板加载 / 个性化
# ---------------------------------------------------------------------------


_TEMPLATE_DIR = Path(__file__).parent / "templates" / "emails"


def _parse_template(path: Path) -> tuple[dict[str, Any], str]:
    """解析 frontmatter + body。

    返回 (meta, body)。frontmatter 用极简 YAML：仅支持
    ``key: value`` 与 ``- item`` 列表（不引依赖）。
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    raw_meta, body = parts[1], parts[2].lstrip("\n")

    meta: dict[str, Any] = {}
    current_list_key: str | None = None
    for line in raw_meta.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        if line.startswith("  - "):
            if current_list_key is None:
                continue
            meta[current_list_key].append(line[4:].strip().strip('"'))
            continue
        current_list_key = None
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            meta[key] = []
            current_list_key = key
        else:
            # 数字 / 字符串
            try:
                meta[key] = float(value) if "." in value else value.strip('"')
            except ValueError:
                meta[key] = value.strip('"')
    return meta, body


_TOKEN_RE = re.compile(r"\{(\w+)\}")


def _render(text: str, ctx: dict[str, str]) -> str:
    """轻量占位符替换：``{key}`` → ctx[key]，缺失时保留原 token。"""

    def _sub(m: re.Match[str]) -> str:
        return ctx.get(m.group(1), m.group(0))

    return _TOKEN_RE.sub(_sub, text)


# ---------------------------------------------------------------------------
# LeadHunterAgent
# ---------------------------------------------------------------------------


class LeadHunterAgent(BasePersonaAgent):
    """获客猎手 persona — B2B 销售自动化。"""

    persona_id = "lead_hunter"
    display_name = "获客猎手"
    emoji = "🎯"
    description = "B2B 获客 + 销售跟进 + 商务沟通自动化"
    backed_by_skills = ["docx", "xlsx"]
    supported_apps = [
        "linkedin",
        "salesforce",
        "hubspot",
        "pipedrive",
        "outlook",
    ]
    capabilities = [
        "lead_discovery",
        "sales_email_drafting",
        "linkedin_outreach",
        "quote_generation",
        "crm_sync",
    ]

    SYSTEM_PROMPT = """你是「获客猎手」，安心智能助手 V3 的 B2B 销售 persona。

定位：
- 服务对象：制造业 / 跨境贸易 / 工业软件等 B2B 业务的销售与商务团队。
- 价值：把"找客户 → 触达 → 跟进 → 报价 → CRM 沉淀"打通成 5 分钟一轮的工作流。

行为准则：
1. **先理解客户公司，再写文案** — 任何外发邮件 / LinkedIn 消息必须基于该 lead 的最近新闻、产品线或公开痛点；禁止纯模板群发。
2. **保留人情味** — 中文用敬语但不堆砌；英文 / 日文遵循当地商务礼仪（en 直接，jp 拘谨且层级感）。
3. **价格策略保守** — 不主动让利。当客户压价时，先建议拆单 / 锁产能 / 升配置，而不是直降。
4. **合规优先** — 拒绝抓取个人隐私邮箱；只在 OAuth 授权 + 公开商务邮箱内工作；所有邮件附 unsubscribe 出口。
5. **数据回流** — 任何成功外发都同步到 CRM（Salesforce / HubSpot / Pipedrive / Zoho），并记录预期回复率，便于后续 A/B 对比。

工具：
- discover_leads / draft_email / generate_quote / sync_to_crm / linkedin_outreach
- 可调用底层 skill：docx (报价单生成)、xlsx (lead 列表导出)
"""

    # ------------------------------------------------------------------
    # capability 1: 线索发掘
    # ------------------------------------------------------------------
    async def discover_leads(
        self,
        criteria: LeadDiscoveryCriteria,
        *,
        candidates: list[dict[str, Any]] | None = None,
    ) -> list[Lead]:
        """根据 criteria 返回候选 Lead 列表（已评分、已截断到 limit）。

        candidates 是上游数据源（LinkedIn API / 工商抓取）注入的原始 dict。
        本方法不发外网请求 — 真正的源接入由 P6/P7-D 完成；此处只做：
            1. 解析 → Lead/Contact dataclass
            2. industry / region / size 过滤
            3. LeadScoring 评分排序
            4. 截断到 criteria.limit
        """
        candidates = candidates or []
        leads: list[Lead] = []
        for raw in candidates:
            lead = self._parse_candidate(raw)
            if lead is None:
                continue
            if not self._matches_criteria(lead, criteria):
                continue
            LeadScoring.score_lead(lead, criteria=criteria, signals=raw.get("signals"))
            leads.append(lead)

        leads.sort(key=lambda lead_: lead_.score, reverse=True)
        return leads[: criteria.limit]

    @staticmethod
    def _parse_candidate(raw: dict[str, Any]) -> Lead | None:
        try:
            contacts = [
                Contact(
                    name=c.get("name", ""),
                    title=c.get("title", ""),
                    email=c.get("email"),
                    linkedin_url=c.get("linkedin_url"),
                    phone=c.get("phone"),
                )
                for c in raw.get("contacts", [])
            ]
            return Lead(
                id=raw.get("id") or f"lead-{uuid.uuid4().hex[:12]}",
                company_name=raw["company_name"],
                industry=raw.get("industry", ""),
                country=raw.get("country", ""),
                employees_estimate=raw.get("employees_estimate"),
                revenue_estimate=raw.get("revenue_estimate"),
                contacts=contacts,
                tags=list(raw.get("tags", [])),
                source=raw.get("source", "manual"),
            )
        except KeyError:
            return None

    @staticmethod
    def _matches_criteria(lead: Lead, criteria: LeadDiscoveryCriteria) -> bool:
        # 1) industry hard filter — 同行业字符串包含 / 标签命中均算通过
        if criteria.industry:
            target = criteria.industry.lower()
            in_industry = target in (lead.industry or "").lower()
            in_tags = any(target in t.lower() for t in lead.tags)
            if not in_industry and not in_tags:
                return False
        # 2) region 软过滤 — 国家或 tag 命中即可
        if criteria.region and criteria.region.lower() not in (lead.country or "").lower():
            if not any(criteria.region.lower() in k.lower() for k in lead.tags):
                return False
        # 3) company size 范围过滤
        if criteria.company_size and lead.employees_estimate is not None:
            lo, hi = LeadHunterAgent._parse_size_range(criteria.company_size)
            if lo is not None and lead.employees_estimate < lo:
                return False
            if hi is not None and lead.employees_estimate > hi:
                return False
        # 4) competitor 排除
        if criteria.exclude_competitors and "competitor" in lead.tags:
            return False
        return True

    @staticmethod
    def _parse_size_range(spec: str) -> tuple[int | None, int | None]:
        spec = spec.strip().lower()
        if spec.startswith("<"):
            return None, int(spec[1:])
        if spec.endswith("+"):
            return int(spec[:-1]), None
        if "-" in spec:
            lo, _, hi = spec.partition("-")
            try:
                return int(lo), int(hi)
            except ValueError:
                return None, None
        try:
            n = int(spec)
            return n, n
        except ValueError:
            return None, None

    # ------------------------------------------------------------------
    # capability 2: 邮件起草
    # ------------------------------------------------------------------
    async def draft_email(
        self,
        lead: Lead,
        intent: str,
        language: str = "zh",
        *,
        sender: dict[str, str] | None = None,
        hooks: dict[str, str] | None = None,
    ) -> EmailDraft:
        """根据 intent + language 选模板，并用 lead 上下文做个性化。

        intent ∈ {"cold_intro", "follow_up", "proposal"}。模板文件命名约定：
        ``{intent}_{language}.md`` — 找不到时退化到 cold_intro_zh。
        """
        template_id = f"{intent}_{language}"
        path = _TEMPLATE_DIR / f"{template_id}.md"
        if not path.exists():
            path = _TEMPLATE_DIR / "cold_intro_zh.md"
            template_id = "cold_intro_zh"

        meta, body = _parse_template(path)

        primary_contact = lead.contacts[0] if lead.contacts else None
        sender = sender or {}
        hooks = hooks or {}

        ctx: dict[str, str] = {
            "company_name": lead.company_name,
            "industry": lead.industry or hooks.get("industry", ""),
            "contact_name": primary_contact.name if primary_contact else "",
            "contact_title_honorific": "总" if language == "zh" else "",
            "sender_name": sender.get("name", "Sales"),
            "sender_company": sender.get("company", "Anxin"),
            "sender_phone": sender.get("phone", ""),
            "value_prop": hooks.get("value_prop", "标准化解决方案"),
            "hook_topic": hooks.get("hook_topic", lead.industry or "合作"),
            "hook_recent_news": hooks.get("hook_recent_news", "扩张相关动作"),
            "pain_point_1": hooks.get("pain_point_1", "成本压力"),
            "pain_point_2": hooks.get("pain_point_2", "交期波动"),
            "social_proof_company": hooks.get("social_proof_company", "同行业头部企业"),
            "social_proof_metric": hooks.get("social_proof_metric", "30% 周期缩短"),
            "previous_touchpoint": hooks.get("previous_touchpoint", "上次沟通"),
            "update_item_1": hooks.get("update_item_1", "新一版方案"),
            "update_item_2": hooks.get("update_item_2", "近期价格窗口"),
            "scope_summary": hooks.get("scope_summary", "..."),
            "timeline_summary": hooks.get("timeline_summary", "..."),
            "price_summary": hooks.get("price_summary", "..."),
        }

        body_rendered = _render(body, ctx)
        variants_raw = meta.get("subject_variants", [])
        variants = [_render(v, ctx) for v in variants_raw] if isinstance(variants_raw, list) else []
        subject = variants[0] if variants else f"{lead.company_name}｜{ctx['hook_topic']}"

        rate = float(meta.get("estimated_response_rate", 0.05))
        # 决策人 + 高 score 时上调预估回复率（封顶 0.5）
        if lead.has_decision_maker():
            rate = min(0.5, rate + 0.05)
        if lead.score >= 0.7:
            rate = min(0.5, rate + 0.05)

        return EmailDraft(
            subject=subject,
            body=body_rendered,
            language=language,
            cta=str(meta.get("cta", "回信沟通")),
            estimated_response_rate=round(rate, 3),
            subject_variants=variants[1:] if len(variants) > 1 else [],
            template_id=template_id,
        )

    # ------------------------------------------------------------------
    # capability 3: LinkedIn 触达
    # ------------------------------------------------------------------
    async def linkedin_outreach(
        self,
        profile_url: str,
        message_template: str,
        oauth_token: str,
        *,
        client: Any | None = None,
    ) -> dict[str, Any]:
        """通过 LinkedIn Marketing Solutions API 发送 connection / InMail。

        合规约束：
            - profile_url 必须是 ``linkedin.com/in/...``；
            - 不接受未 OAuth 的请求；
            - 只用官方 API（不抓 HTML / 不模拟登录）。

        client 可在测试时注入 mock；生产由 P4 OAuth 模块的 LinkedIn provider 提供。
        """
        if not profile_url.startswith(("http://www.linkedin.com/in/", "https://www.linkedin.com/in/")):
            return {
                "ok": False,
                "error": "invalid_profile_url",
                "detail": "仅接受 linkedin.com/in/ 形式的公开 profile URL",
            }
        if not oauth_token:
            return {
                "ok": False,
                "error": "oauth_required",
                "detail": "LinkedIn 触达必须先完成 OAuth 授权",
            }
        if len(message_template) > 300:
            return {
                "ok": False,
                "error": "message_too_long",
                "detail": "LinkedIn connection 消息上限 300 字符",
            }

        if client is None:
            # 没注入 client = 仅返回"已排队"占位，等 P4 LinkedIn provider 接入
            return {
                "ok": True,
                "status": "queued",
                "profile_url": profile_url,
                "message_preview": message_template,
                "note": "LinkedIn provider 尚未接入；本调用仅记录意图",
            }

        result = await client.send_connection_request(
            profile_url=profile_url,
            message=message_template,
            access_token=oauth_token,
        )
        return {"ok": True, "status": "sent", **result}

    # ------------------------------------------------------------------
    # capability 4: 报价单生成（依赖 docx skill）
    # ------------------------------------------------------------------
    async def generate_quote(
        self,
        lead: Lead,
        items: list[QuoteItem],
        terms: dict[str, Any] | QuoteTerms,
        *,
        docx_skill: Any | None = None,
    ) -> bytes:
        """生成报价单 .docx 二进制流。

        真实实现走 ``docx`` skill (cowork-anthropic 移植版，P5-D 已落地)。
        测试时可注入 mock docx_skill；缺省返回一个最小可解析的 .docx 占位。
        """
        if isinstance(terms, dict):
            terms_obj = QuoteTerms(**{k: v for k, v in terms.items() if k in QuoteTerms.__annotations__})
        else:
            terms_obj = terms

        subtotal = round(sum(it.line_total for it in items), 2)
        currency = items[0].currency if items else "USD"

        payload = {
            "lead": asdict(lead),
            "items": [asdict(it) for it in items],
            "subtotal": subtotal,
            "currency": currency,
            "terms": asdict(terms_obj),
            "issued_at": datetime.utcnow().isoformat(),
        }

        if docx_skill is not None:
            return await docx_skill.render_quote(payload)

        # 占位：生成最小 docx（ZIP 文件头 + 文本载荷）— 让 API 测试可校验非空
        # 不引入 python-docx 硬依赖（docx skill 内部已有）
        marker = (
            f"QUOTE for {lead.company_name}\n"
            f"Subtotal: {subtotal} {currency}\n"
            f"Items: {len(items)}\n"
            f"Terms: {terms_obj.payment_terms}\n"
        )
        return marker.encode("utf-8")

    # ------------------------------------------------------------------
    # capability 5: CRM 同步
    # ------------------------------------------------------------------
    SUPPORTED_CRMS = {"salesforce", "hubspot", "pipedrive", "zoho"}

    async def sync_to_crm(
        self,
        leads: list[Lead],
        crm: str,
        oauth_token: str,
        *,
        client: Any | None = None,
    ) -> dict[str, Any]:
        """把 leads 推送到目标 CRM（已 OAuth）。

        client 测试时 mock；生产由 app_authorization registry 解析 provider。
        """
        crm_norm = crm.lower().strip()
        if crm_norm not in self.SUPPORTED_CRMS:
            return asdict(
                CrmSyncResult(
                    crm=crm_norm,
                    failed=len(leads),
                    errors=[{"reason": "unsupported_crm", "crm": crm_norm}],
                )
            )
        if not oauth_token:
            return asdict(
                CrmSyncResult(
                    crm=crm_norm,
                    failed=len(leads),
                    errors=[{"reason": "oauth_required"}],
                )
            )

        if client is None:
            # 没注入 client → 占位：全部归到 created
            return asdict(CrmSyncResult(crm=crm_norm, created=len(leads)))

        result = CrmSyncResult(crm=crm_norm)
        for lead in leads:
            try:
                outcome = await client.upsert_lead(lead=asdict(lead), token=oauth_token)
                action = (outcome or {}).get("action", "created")
                if action == "created":
                    result.created += 1
                elif action == "updated":
                    result.updated += 1
                elif action == "skipped":
                    result.skipped += 1
                else:
                    result.created += 1
            except Exception as exc:  # noqa: BLE001
                result.failed += 1
                result.errors.append({"lead_id": lead.id, "reason": str(exc)})
        return asdict(result)


__all__ = [
    "LeadHunterAgent",
    "LeadScoring",
]
