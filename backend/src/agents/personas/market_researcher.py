# -*- coding: utf-8 -*-
"""MarketResearcherAgent —— 「市场研究员 📊」persona（P7-B）。

DeepTutor 风格的深度研究 agent：给制造业出题，agent 自己规划→检索→综合
→出新问题，最终交付一份带引文的 ``ResearchReport``。

四大对外能力：
    - ``investigate_company``    公司调研
    - ``monitor_competitors``    竞品监控
    - ``industry_trend_analysis`` 行业趋势分析
    - ``deep_research``          通用 DeepResearch 迭代算法

实现要点：
    1. **不耦合具体 LLM** —— 所有 LLM 调用经 ``self._synthesize`` 走 base
       persona 的 ``run_llm``，单测可注入 stub callable
    2. **不绕过 fetch_service** —— 所有外部抓取都走 ``services.fetch``
       门面（合规 / 限流 / 审计自动接管）；单测可在构造时注入 mock
    3. **DeepResearch 收敛** —— 4 道闸门见 ``deep_research`` 文档串
    4. **report 缓存** —— 进程内 ``_report_cache`` 保留最近 100 份，
       供 ``GET /research/{report_id}`` 复用；不持久化（P7-A 后续接 DB）
"""

from __future__ import annotations

import asyncio
import re
import time
from collections import OrderedDict
from typing import Any
from urllib.parse import quote_plus

from src.agents.personas.base_persona import BasePersonaAgent
from src.agents.personas.research_models import (
    Citation,
    ResearchReport,
    ResearchStep,
    compute_confidence,
)


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

#: 单次 deep_research 最多保留多少 finding，避免 LLM context 爆炸
_MAX_CITATIONS_PER_REPORT = 40

#: 单次 deep_research 衍生问题展开上限（每步只取前 N 个 next_question 入栈）
_MAX_NEXT_QUESTIONS_PER_STEP = 2

#: 报告缓存容量（LRU）
_REPORT_CACHE_CAP = 100


SYSTEM_PROMPT = """你是「安心智能助手」V3 中的市场研究员（market_researcher）。

风格：客观、克制、给出可追溯证据。每个结论都附引文（来源 + URL + 原文片段）。

工作流：
1. 先拆解问题（找出可调研的子问题）
2. 优先查内部知识库 / 历史会话；其次查官方源（政府 / 上市披露 / 官网）；
   最后查第三方资讯
3. 综合多源后再下结论；同源孤证降低置信度
4. 衍生新问题时只关注「直接服务于母问题的 1-2 个高价值方向」
5. 输出结构化要点 + 引文 + 建议下一步

禁忌：
- 不臆造数据 / 引文
- 不混淆「报道」与「事实」（标注「据 X 报道」）
- 不输出超出来源的断言
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class MarketResearcherAgent(BasePersonaAgent):
    """市场研究员 persona，调度 fetch + skill_executor + LLM 生成调研报告。"""

    persona_id = "market_researcher"
    display_name = "市场研究员"
    emoji = "📊"
    description = "DeepTutor 模式深度研究：公司/竞品/行业/趋势"
    backed_by_skills = ["xlsx", "docx", "pptx"]
    supported_apps = ["reddit", "twitter_x", "linkedin", "youtube"]
    capabilities = [
        "company_investigation",
        "competitor_monitoring",
        "industry_trends",
        "deep_research_iterative",
        "citation_tracking",
    ]

    SYSTEM_PROMPT = SYSTEM_PROMPT

    def __init__(
        self,
        *,
        llm_callable: Any | None = None,
        fetch_service: Any | None = None,
        skill_executor: Any | None = None,
        kb_search: Any | None = None,
        web_search: Any | None = None,
    ) -> None:
        super().__init__(
            llm_callable=llm_callable,
            fetch_service=fetch_service,
            skill_executor=skill_executor,
            kb_search=kb_search,
        )
        # web_search: 可选的「先搜后抓」入口（如 SerpAPI / Brave Search）
        # 不强求；deep_research 只要 fetch_service 也能跑（直接抓首页 + RSS）
        self.web_search = web_search
        self._report_cache: "OrderedDict[str, ResearchReport]" = OrderedDict()

    # ------------------------------------------------------------------
    # 对外能力
    # ------------------------------------------------------------------

    async def investigate_company(
        self,
        company_name: str,
        depth: int = 2,
    ) -> ResearchReport:
        """公司调研：人物 / 股权 / 产品 / 客户 / 财务公开信息。

        ``depth`` ↦ deep_research 最大迭代次数；通常 2~3 足够覆盖一个新名字。
        """
        question = f"调研公司「{company_name}」：业务 / 产品 / 客户 / 高管 / 公开财务 / 近期动态"
        report = await self.deep_research(
            question=question,
            max_iterations=max(1, depth),
            seed_queries=[
                f"{company_name} 官网 主营业务",
                f"{company_name} 工商 股东 高管",
                f"{company_name} 近期 新闻",
            ],
        )
        report.suggested_actions = [
            f"将「{company_name}」加入竞品监控周报",
            "导出报告到 docx / pptx 给业务决策",
        ]
        return report

    async def monitor_competitors(
        self,
        competitor_names: list[str],
        aspects: list[str] | None = None,
    ) -> dict[str, ResearchReport]:
        """竞品监控：每家分别跑一份精简调研，并行执行。

        ``aspects`` 例：``["产品矩阵", "定价", "营销动作", "招聘信号"]``
        默认 = 全部 4 项。
        """
        aspects = aspects or ["产品矩阵", "定价", "营销动作", "招聘信号"]
        if not competitor_names:
            return {}

        async def _one(name: str) -> tuple[str, ResearchReport]:
            q = f"竞品监控「{name}」: " + " / ".join(aspects)
            report = await self.deep_research(
                question=q,
                max_iterations=2,
                seed_queries=[
                    f"{name} 官网 新闻动态",
                    f"{name} 价格 套餐",
                    f"{name} 招聘 团队规模",
                ],
            )
            report.suggested_actions = [
                f"将「{name}」纳入每周二早 9:00 飞书周报推送",
            ]
            return name, report

        results = await asyncio.gather(*(_one(n) for n in competitor_names))
        return dict(results)

    async def industry_trend_analysis(
        self,
        industry: str,
        lookback_days: int = 90,
    ) -> dict[str, Any]:
        """行业趋势：政策 + 技术 + 资本 + 市场 4 维度交叉。

        返回结构（非 ``ResearchReport``，因为聚合粒度更粗）::

            {
                "industry": "...",
                "lookback_days": 90,
                "report": ResearchReport,            # 主体
                "axes": {                            # 4 维度切片
                    "policy":  [Citation, ...],
                    "tech":    [Citation, ...],
                    "capital": [Citation, ...],
                    "market":  [Citation, ...],
                },
            }
        """
        question = (
            f"分析「{industry}」行业近 {lookback_days} 天的趋势："
            "政策 / 技术 / 资本 / 市场"
        )
        report = await self.deep_research(
            question=question,
            max_iterations=3,
            seed_queries=[
                f"{industry} 政策 法规 {lookback_days} 天",
                f"{industry} 新技术 突破",
                f"{industry} 融资 并购",
                f"{industry} 市场容量 增速",
            ],
        )
        # 4 维度切片：根据 source / url 启发式分类
        axes: dict[str, list[Citation]] = {
            "policy": [],
            "tech": [],
            "capital": [],
            "market": [],
        }
        for c in report.citations:
            tag = self._classify_citation_axis(c)
            axes[tag].append(c)
        return {
            "industry": industry,
            "lookback_days": lookback_days,
            "report": report,
            "axes": {k: [c.to_dict() for c in v] for k, v in axes.items()},
        }

    async def deep_research(
        self,
        question: str,
        max_iterations: int = 5,
        *,
        seed_queries: list[str] | None = None,
    ) -> ResearchReport:
        """DeepResearch 迭代算法核心。

        收敛策略（4 道闸门）：
            1. ``max_iterations`` 硬上限（默认 5）
            2. ``pending_questions`` 空 → 提前停
            3. ``citations >= _MAX_CITATIONS_PER_REPORT`` → 提前停
            4. **去重**：每步综合后用 ``query`` 文本和已访问集合做 dedup，
               避免环路（A → 推 B，B 又推回 A）

        每步 next_questions 只取 ``_MAX_NEXT_QUESTIONS_PER_STEP`` 入栈，
        防止指数级爆炸。
        """
        started = time.perf_counter()
        report = ResearchReport(question=question)

        # 初始问题集：用户题目 + seed_queries
        pending: list[str] = [question]
        if seed_queries:
            pending.extend(seed_queries)
        visited: set[str] = set()

        for i in range(max(1, max_iterations)):
            if not pending:
                break
            if len(report.citations) >= _MAX_CITATIONS_PER_REPORT:
                break

            q = pending.pop(0)
            q_norm = self._normalize_query(q)
            if q_norm in visited:
                continue
            visited.add(q_norm)

            step_started = time.perf_counter()
            kb_hits = await self._kb_search(q)
            web_hits = await self._fetch_with_router(q)
            citations = self._dedup_citations(kb_hits + web_hits)

            synth = await self._synthesize(q, citations)
            step = ResearchStep(
                step_id=i + 1,
                query=q,
                rationale=synth.get("rationale", ""),
                findings=citations,
                next_questions=synth.get("next_questions", [])[
                    :_MAX_NEXT_QUESTIONS_PER_STEP
                ],
                duration_ms=int((time.perf_counter() - step_started) * 1000),
            )
            report.steps.append(step)
            report.citations.extend(citations)
            report.findings.append(
                {
                    "query": q,
                    "summary": synth.get("summary", ""),
                    "citation_ids": [c.url for c in citations],
                }
            )
            # 衍生问题入栈（仍走去重闸门）
            for nq in step.next_questions:
                if self._normalize_query(nq) not in visited:
                    pending.append(nq)

        # 截断 citations 到上限
        report.citations = report.citations[:_MAX_CITATIONS_PER_REPORT]
        report.summary = await self._compose_summary(question, report)
        report.confidence_score = compute_confidence(report.steps)
        report.duration_ms = int((time.perf_counter() - started) * 1000)

        self._cache_report(report)
        return report

    # ------------------------------------------------------------------
    # 报告缓存（GET /research/{report_id} 用）
    # ------------------------------------------------------------------

    def get_report(self, report_id: str) -> ResearchReport | None:
        return self._report_cache.get(report_id)

    def list_reports(self, limit: int = 20) -> list[ResearchReport]:
        return list(self._report_cache.values())[-limit:][::-1]

    def _cache_report(self, report: ResearchReport) -> None:
        self._report_cache[report.report_id] = report
        while len(self._report_cache) > _REPORT_CACHE_CAP:
            self._report_cache.popitem(last=False)

    # ------------------------------------------------------------------
    # 内部 —— 检索 / 综合
    # ------------------------------------------------------------------

    async def _kb_search(self, query: str) -> list[Citation]:
        """走注入的 ``kb_search`` callable；缺省返回空列表。

        约定签名：``async def kb_search(query: str, top_k: int = 5)
        -> list[dict]``，每条 dict 至少含 ``{title, url|source, excerpt}``
        """
        if self.kb_search is None:
            return []
        try:
            res = self.kb_search(query, 5)
            if hasattr(res, "__await__"):
                res = await res
        except Exception:
            return []
        out: list[Citation] = []
        for item in (res or [])[:5]:
            if not isinstance(item, dict):
                continue
            out.append(
                Citation(
                    source=item.get("source") or "knowledge_base",
                    url=item.get("url") or item.get("source") or "",
                    title=item.get("title") or "",
                    excerpt=(item.get("excerpt") or item.get("content") or "")[:500],
                    confidence=float(item.get("confidence") or 0.7),
                )
            )
        return out

    async def _fetch_with_router(self, query: str) -> list[Citation]:
        """优先走 web_search，其次直接抓官方源 / 政府源 / RSS。

        没有 fetch_service 时返回空（保证可单测）。
        """
        if self.fetch_service is None:
            return []

        urls = await self._discover_urls(query)
        if not urls:
            return []

        # 通过 fetch_service 自身构造 request；保持 lazy + 可被 mock。
        # （直接引用 ``src.services.fetch.models.FetchRequest`` 会触发
        # ``services.fetch.__init__`` → ``service.py`` → ``tiers`` 链，
        # 在某些环境下会因 tiers 层副作用 import 失败而连累我们。）
        try:
            FetchRequestCls = self._resolve_fetch_request_cls()
        except Exception:
            return []

        requests = [FetchRequestCls(url=u, timeout=15) for u in urls[:3]]
        try:
            responses = await self.fetch_service.fetch_batch(requests, concurrency=3)
        except Exception:
            return []

        out: list[Citation] = []
        for resp in responses:
            if not getattr(resp, "ok", False):
                continue
            text = (resp.text or "")[:500]
            url = resp.request.url
            tier = getattr(resp.tier_used, "value", str(resp.tier_used))
            # 政府源给更高置信度
            conf = 0.85 if ".gov.cn" in url or ".gov." in url else 0.6
            out.append(
                Citation(
                    source=f"fetch:{tier}",
                    url=url,
                    title=self._extract_title(resp.text or "") or url,
                    excerpt=text,
                    confidence=conf,
                )
            )
        return out

    async def _discover_urls(self, query: str) -> list[str]:
        """先用 web_search，找不到时回落到 hard-coded 公共目录搜索。

        Hard-code 兜底是为了「即使没接 SerpAPI 也能跑」。
        """
        if self.web_search is not None:
            try:
                hits = self.web_search(query, 5)
                if hasattr(hits, "__await__"):
                    hits = await hits
                urls = [
                    h.get("url") if isinstance(h, dict) else str(h)
                    for h in (hits or [])
                ]
                urls = [u for u in urls if u and u.startswith("http")]
                if urls:
                    return urls[:5]
            except Exception:
                pass
        # 兜底：通用搜索引擎入口（不抓结果页只放探索 URL，让上层决定）
        q = quote_plus(query)
        return [
            f"https://www.bing.com/search?q={q}",
        ]

    async def _synthesize(
        self,
        query: str,
        citations: list[Citation],
    ) -> dict[str, Any]:
        """LLM 综合：根据查到的引文产出 ``summary / rationale / next_questions``。

        prompt 结构对 LLM 极简洁友好：把每条引文的 ``title + excerpt``
        塞进 user prompt，要 LLM 回 JSON。
        """
        if not citations:
            return {
                "summary": "未检索到相关证据。",
                "rationale": "本步无 finding，建议改换关键词或提高检索深度。",
                "next_questions": [],
            }
        user_parts = [f"## 子问题: {query}", "", "## 证据片段:"]
        for i, c in enumerate(citations, 1):
            user_parts.append(
                f"[{i}] 来源={c.source} url={c.url}\n  标题={c.title}\n  片段={c.excerpt[:200]}"
            )
        user_parts.append(
            "\n请输出 JSON: {summary, rationale, next_questions: [..最多 2 个..]}"
        )
        raw = await self.run_llm(self.SYSTEM_PROMPT, "\n".join(user_parts))
        # LLM 可能回非严格 JSON；做宽松解析
        return self._parse_synth_response(raw)

    async def _compose_summary(
        self,
        question: str,
        report: ResearchReport,
    ) -> str:
        """所有 step 跑完后，让 LLM 写一段 200-500 字总览。"""
        if not report.steps:
            return "未产出任何调研步骤。"
        bullet = "\n".join(
            f"- 步 {s.step_id}: {s.query} → {len(s.findings)} 条证据" for s in report.steps
        )
        prompt = (
            f"## 母问题\n{question}\n\n"
            f"## 思维链\n{bullet}\n\n"
            "请以「200-500 字 + 3 个核心结论 + 风险提示」的格式输出总览。"
        )
        try:
            return await self.run_llm(self.SYSTEM_PROMPT, prompt)
        except Exception:
            return f"（compose_summary 失败，已收集 {len(report.steps)} 步证据）"

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_fetch_request_cls():
        """避开 ``services.fetch.__init__`` 副作用，按文件路径直接导入
        ``models.py`` 拿 ``FetchRequest``。

        如果失败（路径不可达 / 文件改名），回落到一个 ``SimpleNamespace``
        风格的轻量 dataclass 兼容物，足以让 fetch_service.fetch_batch
        的 mock 实现接收。
        """
        import importlib.util
        import pathlib
        import sys

        mod_name = "_market_researcher_fetch_models"
        if mod_name in sys.modules:
            return sys.modules[mod_name].FetchRequest  # type: ignore[attr-defined]

        path = (
            pathlib.Path(__file__).resolve().parents[2]
            / "services"
            / "fetch"
            / "models.py"
        )
        if not path.exists():
            from dataclasses import dataclass

            @dataclass
            class _LiteFetchRequest:
                url: str
                timeout: int = 30

            return _LiteFetchRequest

        spec = importlib.util.spec_from_file_location(mod_name, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)
        return module.FetchRequest

    @staticmethod
    def _normalize_query(q: str) -> str:
        return re.sub(r"\s+", " ", (q or "").strip().lower())

    @staticmethod
    def _dedup_citations(items: list[Citation]) -> list[Citation]:
        seen: set[str] = set()
        out: list[Citation] = []
        for c in items:
            key = (c.url or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(c)
        return out

    @staticmethod
    def _extract_title(html_or_text: str) -> str:
        """从 HTML 抽 <title>；非 HTML 取首个非空行前 80 字。"""
        if not html_or_text:
            return ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html_or_text, re.IGNORECASE | re.DOTALL)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()[:120]
        for line in html_or_text.splitlines():
            line = line.strip()
            if line:
                return line[:80]
        return ""

    @staticmethod
    def _classify_citation_axis(c: Citation) -> str:
        text = f"{c.url} {c.title} {c.excerpt}".lower()
        if any(k in text for k in (".gov.", "政策", "法规", "通知", "公告")):
            return "policy"
        if any(k in text for k in ("融资", "并购", "上市", "投资", "ipo", "估值")):
            return "capital"
        if any(k in text for k in ("技术", "研发", "专利", "突破", "tech", "patent")):
            return "tech"
        return "market"

    @staticmethod
    def _parse_synth_response(raw: str) -> dict[str, Any]:
        """宽松解析 LLM 综合响应。

        优先尝试整段 JSON；失败则用正则抽 ``next_questions`` 列表 + 把全文
        当 summary。
        """
        import json

        if not raw:
            return {"summary": "", "rationale": "", "next_questions": []}
        # 尝试找第一个 { ... } 块
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                if isinstance(data, dict):
                    nq = data.get("next_questions") or []
                    if not isinstance(nq, list):
                        nq = []
                    return {
                        "summary": str(data.get("summary") or ""),
                        "rationale": str(data.get("rationale") or ""),
                        "next_questions": [str(x) for x in nq][:5],
                    }
            except Exception:
                pass
        # 兜底：把整段塞 summary
        return {
            "summary": raw[:1000],
            "rationale": "",
            "next_questions": [],
        }


__all__ = ["MarketResearcherAgent", "SYSTEM_PROMPT"]
