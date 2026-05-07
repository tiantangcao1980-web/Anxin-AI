"""
Deep Research Engine — 迭代式深度研究引擎

灵感来源：BettaFish QueryEngine / InsightEngine
核心理念：search → reflect → refine → search again

流程：
1. 初始搜索 — 根据用户查询从多源采集数据
2. 反思分析 — LLM 审视搜索结果，识别信息缺口
3. 关键词优化 — 自动生成改进的搜索查询
4. 深度搜索 — 针对缺口进行定向补充搜索
5. 综合摘要 — 汇总所有发现，生成结构化结论

支持可配置的最大反思轮数 (MAX_REFLECTIONS)。
"""

import asyncio
import importlib
import json
import re
from collections.abc import AsyncGenerator, Awaitable
from datetime import datetime
from typing import Any

from loguru import logger

# ===== 搜索结果节点 =====

class SearchResult:
    """单条搜索结果"""

    def __init__(self, source: str, title: str, content: str, url: str = "", relevance: float = 0.0):
        self.source = source
        self.title = title
        self.content = content
        self.url = url
        self.relevance = relevance
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "content": self.content[:500],
            "url": self.url,
            "relevance": self.relevance,
            "timestamp": self.timestamp,
        }


class ReflectionResult:
    """反思结果"""

    def __init__(
        self,
        round_num: int,
        gaps: list[str],
        follow_up_queries: list[str],
        confidence: float,
        summary: str,
    ):
        self.round_num = round_num
        self.gaps = gaps
        self.follow_up_queries = follow_up_queries
        self.confidence = confidence
        self.summary = summary

    def to_dict(self) -> dict[str, Any]:
        return {
            "round": self.round_num,
            "gaps": self.gaps,
            "follow_up_queries": self.follow_up_queries,
            "confidence": self.confidence,
            "summary": self.summary,
        }


class ResearchState:
    """研究状态（贯穿整个管道）"""

    def __init__(self, company_name: str, query: str):
        self.company_name = company_name
        self.original_query = query
        self.current_queries: list[str] = [query]
        self.all_results: list[SearchResult] = []
        self.reflections: list[ReflectionResult] = []
        self.round_num: int = 0
        self.final_summary: str = ""
        self.confidence: float = 0.0
        self._time_range_start: str | None = None
        self._time_range_end: str | None = None
        self.started_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_name": self.company_name,
            "original_query": self.original_query,
            "total_results": len(self.all_results),
            "rounds_completed": self.round_num,
            "confidence": self.confidence,
            "reflections": [r.to_dict() for r in self.reflections],
            "duration_seconds": (datetime.now() - self.started_at).total_seconds(),
        }


# ===== 深度研究引擎 =====

class DeepResearchEngine:
    """
    迭代式深度研究引擎

    借鉴 BettaFish 的 search-reflect-refine 循环：
    每轮搜索后由 LLM 反思结果质量，识别信息缺口，
    自动生成优化的后续查询，直到信息充分或达到最大轮数。
    """

    MAX_REFLECTIONS = 5          # 最大反思轮数（从 3 提升到 5）
    MIN_CONFIDENCE = 0.88        # 提前终止的信心阈值（从 0.85 提升到 0.88）
    SEARCH_TIMEOUT = 20.0        # 单次搜索超时（秒）
    MAX_RESULTS_PER_SOURCE = 8   # 每个数据源最多返回条数

    # 更丰富的研究维度
    DEFAULT_DIMENSIONS = [
        "工商基本信息与经营状态",
        "涉诉记录与司法风险",
        "信用评级与行政处罚",
        "股权关系与实控人穿透",
        "行业舆情与负面新闻",
        "财务状况与经营数据",
        "知识产权与技术资产",
        "关联交易与担保链",
    ]

    def __init__(self) -> None:
        self._llm_agent: Any | None = None
        self._web_searcher: Any | None = None
        self._data_store: Any | None = None

    @property
    def llm_agent(self) -> Any | None:
        if self._llm_agent is None:
            try:
                from src.agents.workforce import get_workforce
                wf = get_workforce()
                self._llm_agent = (
                    wf.agents.get("due_diligence")
                    or wf.agents.get("legal_advisor")
                    or (list(wf.agents.values())[0] if wf.agents else None)
                )
            except Exception as e:
                logger.warning(f"无法加载 LLM Agent: {e}")
        return self._llm_agent

    @property
    def web_searcher(self) -> Any | None:
        if self._web_searcher is None:
            try:
                from src.services.web_search_service import web_search_service
                self._web_searcher = web_search_service
            except ImportError:
                logger.warning("WebSearchService 不可用")
        return self._web_searcher

    @property
    def data_store(self) -> Any | None:
        if self._data_store is None:
            try:
                from src.services.investigation_data_store import investigation_data_store
                self._data_store = investigation_data_store
            except ImportError:
                pass
        return self._data_store

    # ========== 主入口：流式深度研究 ==========

    async def research_stream(
        self,
        company_name: str,
        research_dimensions: list[str] | None = None,
        max_rounds: int | None = None,
        time_range_start: str | None = None,
        time_range_end: str | None = None,
        org_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        流式深度研究，通过 SSE 事件返回每一步进度

        事件类型：
        - research_start: 研究开始
        - search_round: 新一轮搜索开始
        - search_results: 搜索结果返回
        - reflection: 反思分析完成
        - keyword_optimized: 优化后的搜索关键词
        - research_summary: 最终研究摘要
        - research_done: 研究完成

        时间范围参数：
        - time_range_start: 搜索起始日期 "2023-01-01"
        - time_range_end: 搜索结束日期 "2024-12-31"
        """
        max_rounds = max_rounds or self.MAX_REFLECTIONS

        if not research_dimensions:
            research_dimensions = self.DEFAULT_DIMENSIONS

        # 构建时间范围感知的初始查询
        time_suffix = ""
        if time_range_start or time_range_end:
            start = time_range_start or "2010-01-01"
            end = time_range_end or datetime.now().strftime("%Y-%m-%d")
            time_suffix = f" {start}至{end}"

        initial_query = f"{company_name} 企业尽职调查{time_suffix}"
        state = ResearchState(company_name, initial_query)
        # 保存时间范围到 state，供后续轮次使用
        state._time_range_start = time_range_start
        state._time_range_end = time_range_end

        time_range_desc = ""
        if time_range_start or time_range_end:
            time_range_desc = f"（时间范围：{time_range_start or '最早'} ~ {time_range_end or '至今'}）"

        yield {
            "type": "research_start",
            "message": f"开始对「{company_name}」的深度研究{time_range_desc}",
            "dimensions": research_dimensions,
            "max_rounds": max_rounds,
            "time_range": {"start": time_range_start, "end": time_range_end} if (time_range_start or time_range_end) else None,
        }

        # ===== 轮次循环：search → reflect → refine =====
        for round_num in range(1, max_rounds + 1):
            state.round_num = round_num

            yield {
                "type": "search_round",
                "round": round_num,
                "queries": state.current_queries,
                "message": f"第 {round_num} 轮搜索（共 {len(state.current_queries)} 个查询）",
            }

            # —— 搜索阶段 ——
            round_results = await self._execute_search_round(
                state.current_queries, company_name,
                time_range_start=getattr(state, '_time_range_start', None),
                time_range_end=getattr(state, '_time_range_end', None),
                org_id=org_id,
            )
            state.all_results.extend(round_results)

            yield {
                "type": "search_results",
                "round": round_num,
                "new_results": len(round_results),
                "total_results": len(state.all_results),
                "results_preview": [r.to_dict() for r in round_results[:5]],
            }

            # —— 反思阶段 ——
            reflection = await self._reflect_on_results(
                state, research_dimensions, round_num
            )
            state.reflections.append(reflection)
            state.confidence = reflection.confidence

            yield {
                "type": "reflection",
                "round": round_num,
                "confidence": reflection.confidence,
                "gaps": reflection.gaps,
                "summary": reflection.summary,
            }

            # 信心达标，提前终止
            if reflection.confidence >= self.MIN_CONFIDENCE:
                yield {
                    "type": "early_stop",
                    "round": round_num,
                    "reason": f"研究信心 {reflection.confidence:.0%} 达到阈值，提前结束",
                }
                break

            # 还有更多轮次：优化关键词
            if round_num < max_rounds and reflection.follow_up_queries:
                optimized = await self._optimize_keywords(
                    reflection.follow_up_queries, company_name
                )
                state.current_queries = optimized

                yield {
                    "type": "keyword_optimized",
                    "round": round_num,
                    "original": reflection.follow_up_queries,
                    "optimized": optimized,
                }

        # ===== 最终综合摘要 =====
        final_summary = await self._generate_final_summary(state, research_dimensions)
        state.final_summary = final_summary

        yield {
            "type": "research_summary",
            "summary": final_summary,
            "total_rounds": state.round_num,
            "total_results": len(state.all_results),
            "confidence": state.confidence,
        }

        yield {
            "type": "research_done",
            "data": state.to_dict(),
        }

    # ========== 非流式入口 ==========

    async def research(
        self,
        company_name: str,
        research_dimensions: list[str] | None = None,
    ) -> dict[str, Any]:
        """非流式深度研究，返回最终结果"""
        result = {}
        async for event in self.research_stream(company_name, research_dimensions):
            if event["type"] == "research_done":
                result = event["data"]
            elif event["type"] == "research_summary":
                result["summary"] = event["summary"]
        return result

    # ========== 内部方法 ==========

    async def _execute_search_round(
        self,
        queries: list[str],
        company_name: str,
        time_range_start: str | None = None,
        time_range_end: str | None = None,
        org_id: str | None = None,
    ) -> list[SearchResult]:
        """并行执行一轮多查询搜索"""
        tasks: list[Awaitable[list[SearchResult]]] = []
        for query in queries:
            tasks.append(
                self._search_single(
                    query,
                    company_name,
                    time_range_start,
                    time_range_end,
                    org_id=org_id,
                )
            )

        results_nested = await asyncio.gather(*tasks, return_exceptions=True)
        all_results: list[SearchResult] = []
        for item in results_nested:
            if isinstance(item, list):
                all_results.extend(item)
            elif isinstance(item, BaseException):
                logger.warning(f"搜索任务失败: {item}")
        return all_results

    async def _search_single(
        self,
        query: str,
        company_name: str,
        time_range_start: str | None = None,
        time_range_end: str | None = None,
        org_id: str | None = None,
    ) -> list[SearchResult]:
        """单次搜索：整合多个数据源，结果自动入缓存"""
        results: list[SearchResult] = []

        # 有时间范围时跳过缓存（历史搜索通常需要新数据）
        use_cache = not (time_range_start or time_range_end)

        # 先检查缓存
        if use_cache and self.data_store:
            cached = await self.data_store.get_cached_data(
                company_name, "web_search", query_text=query,
                max_age_seconds=43200,  # Web 搜索缓存 12 小时
                org_id=org_id,
            )
            if cached:
                logger.debug(f"深度研究缓存命中: {query[:30]}")
                cached_items = cached.get("results", []) if isinstance(cached, dict) else []
                for item in cached_items:
                    if not isinstance(item, dict):
                        continue
                    results.append(SearchResult(
                        source=self._coerce_str(item.get("source"), "cache"),
                        title=self._coerce_str(item.get("title")),
                        content=self._coerce_str(item.get("content")),
                        url=self._coerce_str(item.get("url")),
                        relevance=self._coerce_float(item.get("relevance"), 0.6),
                    ))
                if results:
                    return results

        # 计算 Web 搜索 API 的 time_range 参数
        web_time_range = self._compute_web_time_range(time_range_start, time_range_end)

        # 对历史搜索，自动将时间信息附加到查询以提升召回
        effective_query = query
        if time_range_start and time_range_start not in query:
            # 提取年份信息附加到查询
            try:
                from datetime import datetime as _dt
                start_year = _dt.strptime(time_range_start, "%Y-%m-%d").year
                end_year = _dt.strptime(time_range_end, "%Y-%m-%d").year if time_range_end else _dt.now().year
                if start_year == end_year:
                    effective_query = f"{query} {start_year}年"
                else:
                    effective_query = f"{query} {start_year}-{end_year}年"
            except Exception:
                effective_query = f"{query} {time_range_start}"

        # 数据源 1：Web 搜索（通用 + 新闻 + 法律专项）
        if self.web_searcher:
            search_tasks: list[Awaitable[list[SearchResult]]] = [
                self._safe_web_search(effective_query, max_results=self.MAX_RESULTS_PER_SOURCE, time_range=web_time_range),
            ]
            # 新闻搜索
            if any(kw in query for kw in ["舆情", "新闻", "负面", "事件"]):
                search_tasks.append(self._safe_news_search(effective_query, max_results=5))
            # 法律专项搜索
            if any(kw in query for kw in ["诉讼", "判决", "裁定", "执行", "失信"]):
                search_tasks.append(self._safe_legal_search(effective_query, max_results=5))

            # 历史搜索时，额外按年份分段搜索，挖掘更多历史数据
            if time_range_start:
                search_tasks.extend(self._build_historical_search_tasks(
                    query, company_name, time_range_start, time_range_end
                ))

            all_web = await asyncio.gather(*search_tasks, return_exceptions=True)
            for batch in all_web:
                if isinstance(batch, list):
                    results.extend(batch)
                elif isinstance(batch, BaseException):
                    logger.debug(f"Web 子任务失败: {batch}")

        # 数据源 2：内部知识库
        try:
            knowledge_service_module = importlib.import_module("src.services.knowledge_service")
            knowledge_service = getattr(knowledge_service_module, "knowledge_service", None)
            if knowledge_service is not None:
                kb_results = await asyncio.wait_for(
                    knowledge_service.search(query, limit=5),
                    timeout=self.SEARCH_TIMEOUT,
                )
                if isinstance(kb_results, list):
                    for kr in kb_results:
                        if not isinstance(kr, dict):
                            continue
                        results.append(SearchResult(
                            source="knowledge_base",
                            title=self._coerce_str(kr.get("title"), "知识库文档"),
                            content=self._coerce_str(kr.get("content")),
                            relevance=self._coerce_float(kr.get("score"), 0.5),
                        ))
        except Exception as e:
            logger.debug(f"知识库搜索失败: {e}")

        # 数据源 3：工商数据源
        try:
            from src.services.due_diligence_service import due_diligence_service
            if company_name in query:
                real_data = await asyncio.wait_for(
                    due_diligence_service._fetch_real_company_data(company_name),
                    timeout=self.SEARCH_TIMEOUT,
                )
                if real_data:
                    results.append(SearchResult(
                        source="business_registry",
                        title=f"{company_name} 工商登记信息",
                        content=json.dumps(real_data, ensure_ascii=False),
                        relevance=0.95,
                    ))
        except Exception as e:
            logger.debug(f"工商数据获取失败: {e}")

        # 搜索结果去重 + 质量评分
        if results:
            try:
                from src.services.search_dedup_service import search_dedup_service
                result_dicts = [r.to_dict() if hasattr(r, 'to_dict') else {"title": r.title, "snippet": r.content, "url": getattr(r, 'url', ''), "relevance": r.relevance, "source": r.source} for r in results]
                deduped = search_dedup_service.deduplicate(result_dicts)
                # 重建 SearchResult 列表
                new_results: list[SearchResult] = []
                for d in deduped:
                    if not isinstance(d, dict):
                        continue
                    new_results.append(SearchResult(
                        source=self._coerce_str(d.get("source")),
                        title=self._coerce_str(d.get("title")),
                        content=self._coerce_str(d.get("snippet"), self._coerce_str(d.get("content"))),
                        url=self._coerce_str(d.get("url")),
                        relevance=self._coerce_float(d.get("relevance"), 0.5),
                    ))
                original_count = len(results)
                results = new_results
                if original_count != len(results):
                    logger.debug(f"深度研究去重: {original_count} → {len(results)} 条")
            except Exception as dedup_err:
                logger.debug(f"去重跳过: {dedup_err}")

        # 搜索结果入缓存
        if results and self.data_store:
            cache_data = {"results": [r.to_dict() for r in results]}
            await self.data_store.save_to_cache(
                company_name=company_name,
                data_source="web_search",
                raw_data=cache_data,
                query_text=query,
                ttl_seconds=43200,
                org_id=org_id,
            )

        return results

    async def _safe_web_search(self, query: str, max_results: int = 8, time_range: str | None = None) -> list[SearchResult]:
        """安全封装的 Web 搜索"""
        searcher = self.web_searcher
        if searcher is None:
            return []
        try:
            web_results = await asyncio.wait_for(
                searcher.search(query, max_results=max_results, time_range=time_range),
                timeout=self.SEARCH_TIMEOUT,
            )
            return [
                SearchResult(
                    source="web_search",
                    title=self._coerce_str(wr.get("title")),
                    content=self._coerce_str(wr.get("snippet"), self._coerce_str(wr.get("content"))),
                    url=self._coerce_str(wr.get("url")),
                    relevance=self._coerce_float(wr.get("relevance"), 0.5),
                )
                for wr in web_results
                if isinstance(wr, dict)
            ]
        except Exception as e:
            logger.debug(f"Web 搜索失败: {e}")
            return []

    async def _safe_news_search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """安全封装的新闻搜索"""
        searcher = self.web_searcher
        if searcher is None:
            return []
        try:
            news_results = await asyncio.wait_for(
                searcher.search_news(query, max_results=max_results),
                timeout=self.SEARCH_TIMEOUT,
            )
            return [
                SearchResult(
                    source="news",
                    title=self._coerce_str(nr.get("title")),
                    content=self._coerce_str(nr.get("snippet"), self._coerce_str(nr.get("content"))),
                    url=self._coerce_str(nr.get("url")),
                    relevance=self._coerce_float(nr.get("relevance"), 0.6),
                )
                for nr in news_results
                if isinstance(nr, dict)
            ]
        except Exception as e:
            logger.debug(f"新闻搜索失败: {e}")
            return []

    async def _safe_legal_search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """安全封装的法律专项搜索"""
        searcher = self.web_searcher
        if searcher is None:
            return []
        try:
            legal_results = await asyncio.wait_for(
                searcher.search_legal(query, max_results=max_results),
                timeout=self.SEARCH_TIMEOUT,
            )
            return [
                SearchResult(
                    source="legal_database",
                    title=self._coerce_str(lr.get("title")),
                    content=self._coerce_str(lr.get("snippet"), self._coerce_str(lr.get("content"))),
                    url=self._coerce_str(lr.get("url")),
                    relevance=self._coerce_float(lr.get("relevance"), 0.7),
                )
                for lr in legal_results
                if isinstance(lr, dict)
            ]
        except Exception as e:
            logger.debug(f"法律搜索失败: {e}")
            return []

    async def _reflect_on_results(
        self,
        state: ResearchState,
        dimensions: list[str],
        round_num: int,
    ) -> ReflectionResult:
        """LLM 反思搜索结果，识别信息缺口"""
        agent = self.llm_agent
        if not agent:
            # 无 LLM 可用时返回默认反思
            return ReflectionResult(
                round_num=round_num,
                gaps=["无法进行 LLM 反思分析"],
                follow_up_queries=[],
                confidence=0.5,
                summary="LLM 不可用，跳过反思阶段",
            )

        # 汇总当前搜索结果
        results_summary = "\n".join(
            f"- [{r.source}] {r.title}: {r.content[:200]}"
            for r in state.all_results[-20:]  # 取最近 20 条
        )

        time_range_hint = ""
        if getattr(state, '_time_range_start', None):
            start = state._time_range_start
            end = getattr(state, '_time_range_end', None) or "至今"
            time_range_hint = f"\n时间范围要求：{start} ~ {end}（请重点关注该时间段内的历史事件和变化）"

        prompt = f"""你是一位资深的企业尽职调查研究员。请审视以下搜索结果并进行反思分析。

研究目标：对「{state.company_name}」进行全面尽职调查
调查维度：{', '.join(dimensions)}
当前是第 {round_num} 轮搜索。{time_range_hint}

已有搜索结果：
{results_summary if results_summary else '（暂无结果）'}

请分析并以 JSON 格式返回：
{{
    "confidence": 0.0-1.0,        // 对当前信息充分程度的信心
    "summary": "当前搜索发现摘要",
    "gaps": ["信息缺口1", "信息缺口2"],  // 尚未覆盖的重要信息
    "follow_up_queries": ["后续查询1", "后续查询2"]  // 建议的后续搜索关键词
}}

请直接返回 JSON，不要其他文字。"""

        try:
            response = await agent.chat(
                message=prompt,
                system_prompt_override="你是专业的企业调查研究员，擅长信息分析和研究策略制定。请直接返回 JSON 格式。",
            )
            response_text = str(response)

            # 解析反思结果
            cleaned = re.sub(r'```(?:json)?\s*', '', response_text).strip()
            cleaned = re.sub(r'```\s*$', '', cleaned).strip()
            json_match = re.search(r'\{[\s\S]*\}', cleaned)

            if json_match:
                data = json.loads(json_match.group())
                return ReflectionResult(
                    round_num=round_num,
                    gaps=data.get("gaps", []),
                    follow_up_queries=data.get("follow_up_queries", []),
                    confidence=min(1.0, max(0.0, float(data.get("confidence", 0.5)))),
                    summary=data.get("summary", ""),
                )
        except Exception as e:
            logger.warning(f"反思分析失败: {e}")

        return ReflectionResult(
            round_num=round_num,
            gaps=["反思分析解析失败"],
            follow_up_queries=[f"{state.company_name} 风险", f"{state.company_name} 诉讼"],
            confidence=0.4,
            summary="反思阶段异常，使用默认后续查询",
        )

    async def _optimize_keywords(
        self, queries: list[str], company_name: str
    ) -> list[str]:
        """
        关键词优化器（灵感：BettaFish InsightEngine 的 keyword_optimizer）
        对后续搜索查询进行优化，提升召回率和精度
        """
        agent = self.llm_agent
        if not agent:
            return queries[:5]

        prompt = f"""你是搜索关键词优化专家。请优化以下搜索查询，使其更精准有效。

原始查询：
{chr(10).join(f'- {q}' for q in queries)}

目标企业：{company_name}

优化规则：
1. 保留核心语义，添加法律/商业领域限定词
2. 拆分过长查询为多个精准短查询
3. 每个优化后的查询不超过 20 字
4. 返回 3-5 个优化后的查询

请以 JSON 数组格式返回，如：["查询1", "查询2", "查询3"]
请直接返回 JSON，不要其他文字。"""

        try:
            response = await agent.chat(
                message=prompt,
                system_prompt_override="你是搜索关键词优化专家。请直接返回 JSON 数组。",
            )
            response_text = str(response)
            cleaned = re.sub(r'```(?:json)?\s*', '', response_text).strip()
            cleaned = re.sub(r'```\s*$', '', cleaned).strip()
            json_match = re.search(r'\[[\s\S]*\]', cleaned)
            if json_match:
                optimized = json.loads(json_match.group())
                if isinstance(optimized, list) and optimized:
                    return [str(q) for q in optimized[:5]]
        except Exception as e:
            logger.warning(f"关键词优化失败: {e}")

        return queries[:5]

    def _compute_web_time_range(
        self,
        time_range_start: str | None,
        time_range_end: str | None,
    ) -> str | None:
        """将日期范围转换为 Web 搜索 API 的 time_range 参数"""
        if not time_range_start:
            return None

        try:
            start = datetime.strptime(time_range_start, "%Y-%m-%d")
            end = datetime.strptime(time_range_end, "%Y-%m-%d") if time_range_end else datetime.now()
            days_span = (end - start).days

            if days_span <= 1:
                return "day"
            elif days_span <= 7:
                return "week"
            elif days_span <= 31:
                return "month"
            elif days_span <= 365:
                return "year"
            else:
                return None  # 超过 1 年，不限制（通过查询词包含年份来过滤）
        except (ValueError, TypeError):
            return None

    def _build_historical_search_tasks(
        self,
        query: str,
        company_name: str,
        time_range_start: str,
        time_range_end: str | None,
    ) -> list[Awaitable[list[SearchResult]]]:
        """
        构建按年份分段的历史搜索任务

        例如用户选择 2020-2023，会分别搜索每年的数据：
        - "腾讯 诉讼 2020年"
        - "腾讯 诉讼 2021年"
        - "腾讯 诉讼 2022年"
        - "腾讯 诉讼 2023年"

        这样可以更精确地获取不同年份的历史信息。
        """
        tasks: list[Awaitable[list[SearchResult]]] = []
        try:
            start = datetime.strptime(time_range_start, "%Y-%m-%d")
            end = datetime.strptime(time_range_end, "%Y-%m-%d") if time_range_end else datetime.now()

            start_year = start.year
            end_year = end.year

            # 最多搜索 5 个年份（避免请求过多）
            years = list(range(start_year, end_year + 1))
            if len(years) > 5:
                # 取首尾和均匀分布的中间年份
                step = len(years) // 4
                years = [years[0], years[step], years[step * 2], years[step * 3], years[-1]]

            # 关键的历史搜索维度
            historical_keywords = ["经营状况", "诉讼", "处罚", "变更", "新闻"]

            for year in years:
                # 每年选一个最重要的维度搜索
                kw = historical_keywords[year % len(historical_keywords)]
                year_query = f"{company_name} {kw} {year}年"
                tasks.append(self._safe_web_search(year_query, max_results=3))

        except (ValueError, TypeError) as e:
            logger.debug(f"构建历史搜索任务失败: {e}")

        return tasks

    @staticmethod
    def _coerce_str(value: Any, default: str = "") -> str:
        if value is None:
            return default
        return str(value)

    @staticmethod
    def _coerce_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    async def _generate_final_summary(
        self, state: ResearchState, dimensions: list[str]
    ) -> str:
        """生成最终研究综合摘要"""
        agent = self.llm_agent
        if not agent:
            return f"对「{state.company_name}」的深度研究完成，共 {state.round_num} 轮搜索，获取 {len(state.all_results)} 条结果。"

        results_summary = "\n".join(
            f"[{r.source}] {r.title}: {r.content[:300]}"
            for r in state.all_results[:30]
        )

        reflections_summary = "\n".join(
            f"第{r.round_num}轮反思：{r.summary} (信心: {r.confidence:.0%})"
            for r in state.reflections
        )

        prompt = f"""请对以下深度研究结果进行综合摘要。

研究对象：{state.company_name}
调查维度：{', '.join(dimensions)}
搜索轮数：{state.round_num}
搜索结果数：{len(state.all_results)}

各轮反思：
{reflections_summary}

关键搜索结果：
{results_summary}

请从以下维度生成结构化摘要：
1. 企业基本情况
2. 主要风险发现
3. 信息完整度评估
4. 需要进一步核实的事项

不超过 500 字。"""

        try:
            summary = await agent.chat(
                message=prompt,
                system_prompt_override="你是资深企业调查分析师，擅长将多源信息综合为简明结论。",
            )
            return str(summary)
        except Exception as e:
            logger.warning(f"生成最终摘要失败: {e}")
            return f"对「{state.company_name}」的深度研究完成，共 {state.round_num} 轮搜索。"


# 全局实例
deep_research_engine = DeepResearchEngine()
