# -*- coding: utf-8 -*-
"""合同管家 persona（P9-C）。

定位：合同全生命周期入口 —— 起草 / 审查 / 风险识别 / 模板 / 版本对比 /
归档。本 persona 不重新发明轮子，而是包装 6 个已有的 specialized agent，
对外暴露 6 大稳定 capability，并保持「persona = 用户视角」的语义一致性。

被包装的 6 个 specialized agent
-------------------------------
+------------------------+----------------------------+----------------------------------+
| 文件                    | 实际类名                    | 用途                              |
+========================+============================+==================================+
| contract_reviewer.py   | ContractReviewAgent        | 三层审查框架 + 法条引用           |
| contract_steward.py    | ContractStewardAgent       | 归档 / 履约状态扫描               |
| contract_investigator  | ContractInvestigatorAgent  | 前置要素提取（双循环第一步）      |
| review_checker.py      | ReviewCheckerAgent         | 审查结论质量验证                  |
| document_drafter.py    | DocumentDraftAgent         | 起草合同 / 函件 / 起诉状          |
| template_librarian.py  | TemplateLirarianAgent      | 模板库检索（注：原文件类名拼错）  |
+------------------------+----------------------------+----------------------------------+

设计取舍
--------
- **包装而非继承 / 改写**：6 个 specialized agent 已被 coordinator / 双循环
  / 前端旧路由依赖，不动它们以避免回归。本 persona 仅做 facade。
- **延迟实例化**：specialized agent 各自 `__init__` 都要 load prompt / 注册
  RAG，启动开销非零；persona 用 `@property` lazy 化，按需创建。
- **mock-friendly**：每个能力先写出「无 LLM 也能跑」的 fallback，方便
  CI 没有 LLM key 时跑通；真实 LLM 由 specialized agent 内部已有的
  ``BaseLegalAgent.chat()`` 链路接手。
- **docx 衔接**：``draft_contract`` 在拿到正文后，按需调用 P5-B docx
  skill（来自 ``services.document_export``）渲染 .docx，路径回填
  ``ContractDraft.docx_template_path``；测试 / CI 模式下若无 skill 注入，
  仅生成一个临时 .docx 占位即可。
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

from src.agents.personas.base_persona import BasePersonaAgent
from src.agents.personas.contract_models import (
    ArchiveResult,
    Citation,
    ContractDraft,
    ReviewIssue,
    ReviewReport,
    RiskAnalysis,
    Template,
    VersionDiff,
)


# ---------------------------------------------------------------------------
# Persona 实装
# ---------------------------------------------------------------------------


class ContractStewardPersona(BasePersonaAgent):
    """合同全生命周期 persona。"""

    persona_id = "contract_steward"
    display_name = "合同管家"
    emoji = "📜"
    description = "合同全生命周期：起草/审查/风险/模板/归档"
    backed_by_skills = ["docx", "pdf"]
    backed_by_agents = [
        "contract_reviewer",
        "contract_steward",
        "contract_investigator",
        "review_checker",
        "document_drafter",
        "template_librarian",
    ]
    supported_apps = ["fadada", "esign"]  # 电子签集成
    capabilities = [
        "contract_drafting",
        "contract_review",
        "risk_identification",
        "template_management",
        "version_comparison",
        "archival",
    ]

    SYSTEM_PROMPT = """你是「合同管家」📜，安心智能助手 V3 的合同全生命周期 persona。

定位：
- 一站式负责合同的起草 / 审查 / 风险识别 / 模板检索 / 版本对比 / 归档；
- 后端编排 6 个 specialized agent（ContractReviewAgent /
  ContractStewardAgent / ContractInvestigatorAgent / ReviewCheckerAgent /
  DocumentDraftAgent / TemplateLirarianAgent），用户只看到一个统一入口。

行为准则：
1. 风险优先 —— 审查与风险识别必须给出「严重程度 + 法律依据 + 修改建议」
   三件套；不写空话，每条问题都要落到具体条款定位。
2. 立场清晰 —— 审查时按 ``perspective`` (buyer/seller/neutral) 输出，
   绝不在 buyer 立场上替对方说好话。
3. 模板优先复用 —— 起草前先检索模板库；命中且适配度高时，引导用户
   下载模板自填，而非全程让 LLM 重写。
4. 归档可追溯 —— 任何归档动作必须返回 ``archive_url`` + ``retention_period``，
   并保留原始文本与 metadata，便于审计。
5. 红线兜底 —— 检测到「单方面任意终止」「保证最低销售额」「无限连带责任」
   等业内黑名单条款，强制升格为 critical 风险，不允许被 LLM 自行降级。

工具：
- 调用底层 specialized agent 完成深度推理
- backed_by_skills：docx (渲染交付件) / pdf (合同 PDF 版本读取)
- supported_apps：法大大 / e签宝（用于电子签流程对接）
"""

    # ------------------------------------------------------------------
    # specialized agent 懒加载属性
    # ------------------------------------------------------------------
    @property
    def _reviewer(self):  # pragma: no cover - 真实 agent 在 LLM 环境才用到
        if not hasattr(self, "_reviewer_inst") or self._reviewer_inst is None:
            from src.agents.contract_reviewer import ContractReviewAgent

            self._reviewer_inst = ContractReviewAgent()
        return self._reviewer_inst

    @property
    def _core_steward(self):  # pragma: no cover
        if not hasattr(self, "_core_steward_inst") or self._core_steward_inst is None:
            from src.agents.contract_steward import ContractStewardAgent

            self._core_steward_inst = ContractStewardAgent()
        return self._core_steward_inst

    @property
    def _investigator(self):  # pragma: no cover
        if not hasattr(self, "_investigator_inst") or self._investigator_inst is None:
            from src.agents.contract_investigator import ContractInvestigatorAgent

            self._investigator_inst = ContractInvestigatorAgent()
        return self._investigator_inst

    @property
    def _checker(self):  # pragma: no cover
        if not hasattr(self, "_checker_inst") or self._checker_inst is None:
            from src.agents.review_checker import ReviewCheckerAgent

            self._checker_inst = ReviewCheckerAgent()
        return self._checker_inst

    @property
    def _drafter(self):  # pragma: no cover
        if not hasattr(self, "_drafter_inst") or self._drafter_inst is None:
            from src.agents.document_drafter import DocumentDraftAgent

            self._drafter_inst = DocumentDraftAgent()
        return self._drafter_inst

    @property
    def _librarian(self):
        # 模板库无 LLM 调用 —— 即使在测试环境也直接用真品。
        if not hasattr(self, "_librarian_inst") or self._librarian_inst is None:
            from src.agents.template_librarian import (
                TEMPLATE_CATALOG,
                TemplateLirarianAgent,
            )

            self._librarian_inst = TemplateLirarianAgent()
            # 缓存 catalog 引用，方便 find_template 不再走 LLM Agent。
            self._template_catalog = list(TEMPLATE_CATALOG)
        return self._librarian_inst

    # ------------------------------------------------------------------
    # capability 1: 起草
    # ------------------------------------------------------------------
    async def draft_contract(
        self,
        contract_type: str,
        parties: list[dict],
        terms: dict,
        language: str = "zh",
        *,
        drafter: Any | None = None,
        docx_skill: Any | None = None,
    ) -> ContractDraft:
        """生成一份完整合同草稿。

        :param contract_type: 合同类型（``"采购合同"`` / ``"NDA"`` / ...）。
        :param parties: 当事方列表，每项 ``{role, name, type?}``。
        :param terms: 关键条款字典（``{"金额": ..., "期限": ...}``）。
        :param language: 输出语言，默认中文。
        :param drafter: 测试时可注入 ``DocumentDraftAgent`` mock；
            生产由懒加载 ``self._drafter`` 提供。
        :param docx_skill: 测试时可注入 docx 渲染器 mock；生产走 P5-B
            ``services.document_export`` 链路。

        返回 :class:`ContractDraft`，含 :attr:`docx_template_path`，前端
        可直接给出 .docx 下载入口。
        """
        if not contract_type:
            raise ValueError("contract_type 必须非空")
        if not parties:
            raise ValueError("parties 至少包含 1 个当事方")

        # parties: [{role, name, type}] → drafter 期望 {party_a, party_b}
        legacy_parties: dict[str, str] = {}
        for idx, p in enumerate(parties[:6]):
            slot = ["party_a", "party_b", "party_c", "party_d", "party_e", "party_f"][idx]
            legacy_parties[slot] = p.get("name", f"待填写-{idx + 1}")

        full_text = ""
        drafter_obj = drafter if drafter is not None else None
        if drafter_obj is None:
            try:
                drafter_obj = self._drafter
            except Exception:
                drafter_obj = None

        if drafter_obj is not None and hasattr(drafter_obj, "draft_contract"):
            try:
                full_text = await drafter_obj.draft_contract(
                    contract_type=contract_type,
                    parties=legacy_parties,
                    terms=terms or {},
                )
            except Exception as exc:  # noqa: BLE001
                full_text = self._draft_fallback(contract_type, parties, terms, str(exc))
        else:
            full_text = self._draft_fallback(contract_type, parties, terms, "drafter 未就绪")

        # 切分章节（粗粒度：按 "第X条" 切）
        sections = self._split_sections(full_text)

        # 建议追加条款（基于合同类型给固定推荐）
        suggested = self._recommend_clauses(contract_type)

        # 渲染 docx（衔接 P5-B docx skill）
        docx_path: Optional[str] = None
        if docx_skill is not None:
            try:
                docx_path = await docx_skill.render_contract(
                    {
                        "contract_type": contract_type,
                        "parties": parties,
                        "terms": terms,
                        "full_text": full_text,
                        "language": language,
                    }
                )
            except Exception:
                docx_path = None
        else:
            docx_path = self._write_docx_placeholder(contract_type, full_text)

        return ContractDraft(
            contract_type=contract_type,
            title=self._derive_title(contract_type, parties),
            full_text=full_text,
            sections=sections,
            suggested_clauses=suggested,
            estimated_word_count=len(full_text),
            language=language,
            docx_template_path=docx_path,
        )

    # ------------------------------------------------------------------
    # capability 2: 审查
    # ------------------------------------------------------------------
    async def review_contract(
        self,
        document_text: str,
        perspective: str = "buyer",
        *,
        reviewer: Any | None = None,
        checker: Any | None = None,
    ) -> ReviewReport:
        """对合同正文做立场化审查。

        - 调用 :class:`ContractReviewAgent.process` 拿初版结果；
        - 调用 :class:`ReviewCheckerAgent.process` 做质量交叉验证；
        - 把两者合并成统一 :class:`ReviewReport`。
        """
        if not document_text or not document_text.strip():
            raise ValueError("document_text 必须非空")
        if perspective not in {"buyer", "seller", "neutral"}:
            raise ValueError(f"非法 perspective: {perspective}")

        review_meta: dict[str, Any] = {}
        verification: dict[str, Any] = {}
        rev_obj = reviewer if reviewer is not None else None
        ck_obj = checker if checker is not None else None

        if rev_obj is None:
            try:
                rev_obj = self._reviewer
            except Exception:
                rev_obj = None

        if rev_obj is not None and hasattr(rev_obj, "process"):
            try:
                resp = await rev_obj.process(
                    {"description": document_text, "context": {"perspective": perspective}}
                )
                review_meta = getattr(resp, "metadata", None) or {}
            except Exception:
                review_meta = {}

        if ck_obj is None:
            try:
                ck_obj = self._checker
            except Exception:
                ck_obj = None

        if ck_obj is not None and hasattr(ck_obj, "process") and review_meta:
            try:
                resp = await ck_obj.process(
                    {
                        "description": "审查质量验证",
                        "context": {"review_result": review_meta, "investigation": {}},
                    }
                )
                verification = getattr(resp, "metadata", None) or {}
            except Exception:
                verification = {}

        return self._build_review_report(
            document_text=document_text,
            perspective=perspective,
            review_meta=review_meta,
            verification=verification,
        )

    # ------------------------------------------------------------------
    # capability 3: 风险识别
    # ------------------------------------------------------------------
    async def identify_risks(
        self,
        document_text: str,
        *,
        investigator: Any | None = None,
    ) -> RiskAnalysis:
        """专项识别合同风险（不输出修改建议，专注「风险地图」）。

        与 ``review_contract`` 的差异：
        - 审查 = 立场化、给改稿建议；
        - 风险识别 = 中立、给风险评级 + 法条 + 缓解措施。
        """
        if not document_text or not document_text.strip():
            raise ValueError("document_text 必须非空")

        investigation: dict[str, Any] = {}
        inv_obj = investigator if investigator is not None else None
        if inv_obj is None:
            try:
                inv_obj = self._investigator
            except Exception:
                inv_obj = None

        if inv_obj is not None and hasattr(inv_obj, "process"):
            try:
                resp = await inv_obj.process({"description": document_text, "context": {}})
                investigation = getattr(resp, "metadata", None) or {}
            except Exception:
                investigation = {}

        # 黑名单关键词扫描（不依赖 LLM，规则级别兜底）
        blacklist_hits = self._scan_blacklist_clauses(document_text)

        risks: list[dict] = []
        # 1) investigator 给的初步风险
        for raw in investigation.get("preliminary_risks", []) or []:
            risks.append(
                {
                    "category": "general",
                    "description": str(raw)[:300],
                    "likelihood": 0.5,
                    "impact": 0.5,
                    "mitigation": "建议在审查阶段进一步定位条款并修订。",
                }
            )
        # 2) 黑名单条款 → critical
        for hit in blacklist_hits:
            risks.append(
                {
                    "category": "blacklist",
                    "description": f"触发禁用条款关键词：{hit}",
                    "likelihood": 0.9,
                    "impact": 0.9,
                    "mitigation": "建议删除或重写为对等约束。",
                }
            )

        # 整体等级：有黑名单 → critical；缺失 ≥3 → high；其他根据 risks 数量
        missing_count = len(investigation.get("missing_elements", []) or [])
        if blacklist_hits:
            level = "critical"
        elif missing_count >= 3 or len(risks) >= 5:
            level = "high"
        elif risks:
            level = "medium"
        else:
            level = "low"

        # 法律依据（暂用 investigator 给的 applicable_laws 转 Citation）
        legal_basis = [
            Citation(
                source="legal_kb",
                url="",
                title=str(law),
                excerpt="",
                confidence=0.6,
            )
            for law in (investigation.get("applicable_laws", []) or [])[:5]
        ]

        return RiskAnalysis(
            overall_risk_level=level,
            risks=risks,
            blacklist_clauses=blacklist_hits,
            legal_basis=legal_basis,
        )

    # ------------------------------------------------------------------
    # capability 4: 模板检索
    # ------------------------------------------------------------------
    async def find_template(
        self,
        query: str,
        contract_type: str | None = None,
    ) -> list[Template]:
        """模板库关键词检索。

        走 ``TemplateLirarianAgent`` 内置的 ``TEMPLATE_CATALOG``（无 LLM
        调用）。``contract_type`` 命中时优先返回同 sub_category 的条目。
        """
        if not query or not query.strip():
            raise ValueError("query 必须非空")

        # 触发懒加载，并填充 self._template_catalog
        _ = self._librarian
        catalog: list[dict] = list(getattr(self, "_template_catalog", []))

        q = query.lower().strip()
        results: list[Template] = []
        for tpl in catalog:
            keywords = [k.lower() for k in tpl.get("applicable_keywords", [])]
            name = tpl.get("name", "").lower()
            sub = tpl.get("sub_category", "").lower()
            hit = (
                q in name
                or any(q in kw or kw in q for kw in keywords)
                or (contract_type and contract_type.lower() in sub)
            )
            if not hit:
                continue
            results.append(
                Template(
                    template_id=tpl.get("id", ""),
                    name=tpl.get("name", ""),
                    contract_type=tpl.get("sub_category", ""),
                    description=tpl.get("description", ""),
                    use_case=tpl.get("category", ""),
                    language="zh",
                    word_count=0,
                    last_used=None,
                    download_url=tpl.get("download_path", ""),
                )
            )
        return results

    # ------------------------------------------------------------------
    # capability 5: 版本对比
    # ------------------------------------------------------------------
    async def compare_versions(
        self,
        v1_text: str,
        v2_text: str,
    ) -> VersionDiff:
        """对两版合同做结构 + 语义对比。

        本能力不依赖 LLM：用 ``difflib.SequenceMatcher`` 在「条款级」做
        opcodes 比对（按 "第X条" 切分），再用启发式从条款增删 / 关键词
        变化中产出 ``semantic_changes``。
        """
        if v1_text is None or v2_text is None:
            raise ValueError("v1_text / v2_text 必须非空")

        v1_clauses = self._split_sections(v1_text)
        v2_clauses = self._split_sections(v2_text)
        v1_titles = [c.get("title", "") for c in v1_clauses]
        v2_titles = [c.get("title", "") for c in v2_clauses]

        sm = SequenceMatcher(a=v1_titles, b=v2_titles, autojunk=False)
        additions: list[dict] = []
        deletions: list[dict] = []
        modifications: list[dict] = []

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                # 标题相同 → 比内容；不同则记 modifications
                for k in range(i2 - i1):
                    a = v1_clauses[i1 + k]
                    b = v2_clauses[j1 + k]
                    if (a.get("content") or "") != (b.get("content") or ""):
                        modifications.append(
                            {
                                "location": a.get("title", ""),
                                "before": a.get("content", "")[:500],
                                "after": b.get("content", "")[:500],
                                "reason": "条款内容变化",
                            }
                        )
            elif tag == "insert":
                for k in range(j1, j2):
                    additions.append(
                        {
                            "location": v2_clauses[k].get("title", ""),
                            "text": v2_clauses[k].get("content", "")[:500],
                            "type": "clause_added",
                        }
                    )
            elif tag == "delete":
                for k in range(i1, i2):
                    deletions.append(
                        {
                            "location": v1_clauses[k].get("title", ""),
                            "text": v1_clauses[k].get("content", "")[:500],
                            "type": "clause_removed",
                        }
                    )
            elif tag == "replace":
                for k in range(i1, i2):
                    deletions.append(
                        {
                            "location": v1_clauses[k].get("title", ""),
                            "text": v1_clauses[k].get("content", "")[:500],
                            "type": "clause_removed",
                        }
                    )
                for k in range(j1, j2):
                    additions.append(
                        {
                            "location": v2_clauses[k].get("title", ""),
                            "text": v2_clauses[k].get("content", "")[:500],
                            "type": "clause_added",
                        }
                    )

        # 语义级关键变化（启发式）
        semantic: list[str] = []
        if any("违约金" in d["location"] for d in modifications):
            semantic.append("违约金条款发生变化，请确认幅度是否在合理区间。")
        if any("管辖" in d["location"] or "争议" in d["location"] for d in modifications):
            semantic.append("争议解决 / 管辖条款发生变化，请核对管辖法院或仲裁机构。")
        if additions:
            semantic.append(f"v2 新增 {len(additions)} 个条款。")
        if deletions:
            semantic.append(f"v2 删除 {len(deletions)} 个条款，注意权利义务对等。")
        if not semantic:
            semantic.append("未识别出关键语义变化（仅文字润色级差异）。")

        return VersionDiff(
            v1_summary=f"共 {len(v1_clauses)} 个条款，约 {len(v1_text)} 字。",
            v2_summary=f"共 {len(v2_clauses)} 个条款，约 {len(v2_text)} 字。",
            additions=additions,
            deletions=deletions,
            modifications=modifications,
            semantic_changes=semantic,
        )

    # ------------------------------------------------------------------
    # capability 6: 归档
    # ------------------------------------------------------------------
    async def archive(
        self,
        contract_id: str,
        metadata: dict,
        *,
        retention_period_days: int | None = None,
    ) -> ArchiveResult:
        """归档合同 metadata 到结构化存储。

        本能力不依赖 LLM；走 ``ContractStewardAgent._archive_contract``
        的语义但规则化：返回 archive_url + 默认保留期。

        :param retention_period_days: 自定义保留期；缺省按 ``metadata.contract_type``
            匹配，未识别则采用 5 年（1825 天）。
        """
        if not contract_id:
            raise ValueError("contract_id 必须非空")

        ctype = (metadata or {}).get("contract_type", "").strip()
        if retention_period_days is None:
            retention_period_days = self._default_retention_days(ctype)

        # archive_url 在真实环境会指向 OSS / 静态托管；当前阶段返回伪路径
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", contract_id)[:60] or uuid.uuid4().hex[:12]
        archive_url = f"/api/v1/personas/contract/archives/{slug}"

        return ArchiveResult(
            contract_id=contract_id,
            archive_url=archive_url,
            metadata=dict(metadata or {}),
            archived_at=datetime.utcnow(),
            retention_period_days=retention_period_days,
        )

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    @staticmethod
    def _draft_fallback(
        contract_type: str,
        parties: list[dict],
        terms: dict,
        reason: str,
    ) -> str:
        """drafter 不可用时的占位文本（保证下游链路不阻塞）。"""
        lines: list[str] = [f"# {contract_type}", ""]
        for idx, p in enumerate(parties or []):
            role = p.get("role") or f"当事方{idx + 1}"
            lines.append(f"- {role}：{p.get('name', '【待填写】')}")
        lines.append("")
        lines.append("（草稿生成 fallback 模式 — 原因：" + reason + "）")
        lines.append("")
        if terms:
            lines.append("## 主要条款")
            for k, v in terms.items():
                lines.append(f"- {k}：{v}")
        lines.extend(
            [
                "",
                "## 第一条 合同标的",
                "（请补充标的、规格、数量。）",
                "## 第二条 价款与支付",
                "（请补充总价、币种、支付节点。）",
                "## 第三条 履行期限",
                "（请补充开始 / 结束日期。）",
                "## 第四条 违约责任",
                "（建议明确违约金比例或计算方式。）",
                "## 第五条 争议解决",
                "（建议明确管辖法院或仲裁机构。）",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _derive_title(contract_type: str, parties: list[dict]) -> str:
        names = [p.get("name", "").strip() for p in parties if p.get("name")]
        if len(names) >= 2:
            return f"{names[0]}与{names[1]}{contract_type}"
        if names:
            return f"{names[0]}{contract_type}"
        return contract_type

    @staticmethod
    def _split_sections(text: str) -> list[dict]:
        """按 "第X条" / "##" 简单切分；保留章节标题与正文。"""
        if not text:
            return []
        # 兼容 "第一条"/"第1条"/"## 标题"
        pattern = re.compile(r"(第[一二三四五六七八九十百0-9]+条[^\n]*|##+\s+[^\n]+)")
        positions = [(m.start(), m.group()) for m in pattern.finditer(text)]
        if not positions:
            return [{"title": "正文", "content": text, "optional": False}]
        sections: list[dict] = []
        for idx, (start, title) in enumerate(positions):
            end = positions[idx + 1][0] if idx + 1 < len(positions) else len(text)
            content = text[start:end].strip()
            # 去掉标题行本身保留正文
            content = content[len(title):].strip()
            sections.append(
                {"title": title.strip(), "content": content, "optional": False}
            )
        return sections

    @staticmethod
    def _recommend_clauses(contract_type: str) -> list[dict]:
        """按合同类型推荐可选追加条款。"""
        common = [
            {
                "title": "不可抗力",
                "rationale": "明确不可抗力的范围与通知义务，降低履行风险。",
                "content": "因不可抗力造成无法履行的，受影响方应自事件发生之日起 N 日内书面通知对方……",
            },
            {
                "title": "保密",
                "rationale": "约定保密信息范围与期限，保护双方商业秘密。",
                "content": "双方对履行本合同所知悉的对方商业秘密及其他保密信息负有保密义务……",
            },
        ]
        if "采购" in contract_type or "买卖" in contract_type:
            common.append(
                {
                    "title": "质量异议期",
                    "rationale": "明确收货后多久内可提出质量异议，避免长期不确定。",
                    "content": "买方应在收到货物之日起 N 日内进行验收，逾期未提异议视为质量合格……",
                }
            )
        if "服务" in contract_type:
            common.append(
                {
                    "title": "服务水平协议（SLA）",
                    "rationale": "明确响应时长 / 解决时长 / 故障定级，便于绩效管理。",
                    "content": "服务方按以下 SLA 提供服务：响应 ≤ N 分钟、解决 ≤ N 小时……",
                }
            )
        if "数据" in contract_type or "信息" in contract_type:
            common.append(
                {
                    "title": "数据与个人信息保护",
                    "rationale": "符合《个人信息保护法》与《数据安全法》要求。",
                    "content": "处理个人信息应取得授权同意，并采取必要的安全保障措施……",
                }
            )
        return common

    BLACKLIST_PATTERNS = (
        "保证最低销售额",
        "单方面任意终止",
        "无限连带责任",
        "放弃一切抗辩",
        "免除一切责任",
        "本合同最终解释权归",
    )

    @classmethod
    def _scan_blacklist_clauses(cls, text: str) -> list[str]:
        text = text or ""
        return [pat for pat in cls.BLACKLIST_PATTERNS if pat in text]

    @staticmethod
    def _default_retention_days(contract_type: str) -> int:
        """按合同类型给默认保留天数。

        - 税务凭证类（发票 / 应税合同）→ 3650 (10 年)
        - 劳动合同 → 7300 (20 年，覆盖工伤追诉)
        - 普通商事合同 → 1825 (5 年，覆盖一般诉讼时效)
        """
        if any(k in contract_type for k in ("税", "发票")):
            return 3650
        if "劳动" in contract_type:
            return 7300
        return 1825

    @staticmethod
    def _build_review_report(
        document_text: str,
        perspective: str,
        review_meta: dict,
        verification: dict,
    ) -> ReviewReport:
        risks_raw = (review_meta or {}).get("risks", []) or []
        issues: list[ReviewIssue] = []
        for raw in risks_raw[:20]:
            issues.append(
                ReviewIssue(
                    clause_text=str(raw.get("title", ""))[:200],
                    issue_type=str(raw.get("issue_type") or "ambiguous"),
                    severity=str(raw.get("level") or raw.get("severity") or "medium"),
                    description=str(raw.get("description", ""))[:500],
                    suggested_revision=str(raw.get("suggested_text") or raw.get("suggestion") or ""),
                    location={"section": raw.get("clause") or raw.get("location", "")},
                )
            )

        # score：默认 65；review_meta.risk_score 若是 0-1 浮点则换算到 0-100
        rs = review_meta.get("risk_score") if review_meta else None
        if isinstance(rs, (int, float)):
            risk_factor = float(rs) if rs > 1 else float(rs) * 100
            score = max(0.0, min(100.0, 100.0 - risk_factor))
        else:
            score = 65.0

        # recommendation：根据 risk_level + verification.confidence
        risk_level = (review_meta or {}).get("risk_level", "medium")
        if risk_level == "critical":
            recommendation = "reject"
        elif risk_level == "high":
            recommendation = "redline"
        elif risk_level == "low":
            recommendation = "sign_as_is"
        else:
            recommendation = "negotiate"

        overall = (
            (review_meta or {}).get("summary")
            or (verification or {}).get("summary")
            or f"已对该合同从 {perspective} 立场完成审查，请关注下列风险点。"
        )
        return ReviewReport(
            overall_assessment=str(overall)[:1000],
            perspective=perspective,
            score=round(score, 2),
            issues=issues,
            missing_clauses=list((review_meta or {}).get("missing_clauses", []))[:30],
            redundant_clauses=[],
            recommendation=recommendation,
        )

    @staticmethod
    def _write_docx_placeholder(contract_type: str, full_text: str) -> Optional[str]:
        """无 docx skill 注入时，写一个最小 .docx 占位文件。

        目的：让前端「下载 docx」按钮有非空目标；并不依赖 python-docx
        硬装（生产由 services.document_export.export_docx 接管）。
        """
        try:
            tmp_dir = Path("/tmp/anxin_contract_drafts")
            tmp_dir.mkdir(parents=True, exist_ok=True)
            safe_type = re.sub(r"[^\w-]+", "_", contract_type)[:30] or "contract"
            path = tmp_dir / f"{safe_type}-{uuid.uuid4().hex[:8]}.docx"
            # 写一个最小可识别的 ZIP 占位（不需 python-docx）
            path.write_bytes(b"PK\x03\x04" + full_text[:4096].encode("utf-8", errors="ignore"))
            return str(path)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# 兼容性 alias —— `__init__.py` 任务文档用的是 ContractStewardPersona，
# 但部分调用方习惯写 `from ... import ContractStewardAgent`，提供别名。
# 注意：这与底层 specialized agent ``src.agents.contract_steward.ContractStewardAgent``
# 同名但不同模块，不会被 Python import 系统冲突。
# ---------------------------------------------------------------------------
ContractStewardAgent = ContractStewardPersona


__all__ = [
    "ContractStewardPersona",
    "ContractStewardAgent",
]
