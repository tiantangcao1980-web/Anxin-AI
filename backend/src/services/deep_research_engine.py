# -*- coding: utf-8 -*-
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
import json
import re
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime
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

    def to_dict(self) -> Dict[str, Any]:
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
        gaps: List[str],
        follow_up_queries: List[str],
        confidence: float,
        summary: str,
    ):
        self.round_num = round_num
        self.gaps = gaps
        self.follow_up_queries = follow_up_queries
        self.confidence = confidence
        self.summary = summary

    def to_dict(self) -> Dict[str, Any]:
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
        self.current_queries: List[str] = [query]
        self.all_results: List[SearchResult] = []
        self.reflections: List[ReflectionResult] = []
        self.round_num: int = 0
        self.final_summary: str = ""
        self.confidence: float = 0.0
        self.started_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
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

    MAX_REFLECTIONS = 3          # 最大反思轮数
    MIN_CONFIDENCE = 0.85        # 提前终止的信心阈值
    SEARCH_TIMEOUT = 15.0        # 单次搜索超时（秒）

    def __init__(self):
        self._llm_agent = None
        self._web_searcher = None

    @property
    def llm_agent(self):
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
    def web_searcher(self):
        if self._web_searcher is None:
            try:
                from src.services.web_search_service import web_search_service
                self._web_searcher = web_search_service
            except ImportError:
                logger.warning("WebSearchService 不可用")
        return self._web_searcher

    # ========== 主入口：流式深度研究 ==========

    async def research_stream(
        self,
        company_name: str,
        research_dimensions: Optional[List[str]] = None,
        max_rounds: Optional[int] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
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
        """
        max_rounds = max_rounds or self.MAX_REFLECTIONS

        if not research_dimensions:
            research_dimensions = [
                "工商基本信息与经营状态",
                "涉诉记录与司法风险",
                "信用评级与行政处罚",
                "股权关系与实控人",
                "行业舆情与负面新闻",
            ]

        # 初始化研究状态
        initial_query = f"{company_name} 企业尽职调查"
        state = ResearchState(company_name, initial_query)

        yield {
            "type": "research_start",
            "message": f"开始对「{company_name}」的深度研究",
            "dimensions": research_dimensions,
            "max_rounds": max_rounds,
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
                state.current_queries, company_name
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
        research_dimensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
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
        self, queries: List[str], company_name: str
    ) -> List[SearchResult]:
        """并行执行一轮多查询搜索"""
        tasks = []
        for query in queries:
            tasks.append(self._search_single(query, company_name))

        results_nested = await asyncio.gather(*tasks, return_exceptions=True)
        all_results = []
        for item in results_nested:
            if isinstance(item, list):
                all_results.extend(item)
            elif isinstance(item, Exception):
                logger.warning(f"搜索任务失败: {item}")
        return all_results

    async def _search_single(
        self, query: str, company_name: str
    ) -> List[SearchResult]:
        """单次搜索：整合多个数据源"""
        results: List[SearchResult] = []

        # 数据源 1：Web 搜索
        if self.web_searcher:
            try:
                web_results = await asyncio.wait_for(
                    self.web_searcher.search(query, max_results=5),
                    timeout=self.SEARCH_TIMEOUT,
                )
                for wr in web_results:
                    results.append(SearchResult(
                        source="web_search",
                        title=wr.get("title", ""),
                        content=wr.get("snippet", wr.get("content", "")),
                        url=wr.get("url", ""),
                        relevance=wr.get("relevance", 0.5),
                    ))
            except Exception as e:
                logger.debug(f"Web 搜索失败: {e}")

        # 数据源 2：内部知识库
        try:
            from src.services.knowledge_service import knowledge_service
            kb_results = await asyncio.wait_for(
                knowledge_service.search(query, limit=3),
                timeout=self.SEARCH_TIMEOUT,
            )
            if kb_results:
                for kr in (kb_results if isinstance(kb_results, list) else []):
                    results.append(SearchResult(
                        source="knowledge_base",
                        title=kr.get("title", "知识库文档"),
                        content=kr.get("content", ""),
                        relevance=kr.get("score", 0.5),
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

        return results

    async def _reflect_on_results(
        self,
        state: ResearchState,
        dimensions: List[str],
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

        prompt = f"""你是一位资深的企业尽职调查研究员。请审视以下搜索结果并进行反思分析。

研究目标：对「{state.company_name}」进行全面尽职调查
调查维度：{', '.join(dimensions)}
当前是第 {round_num} 轮搜索。

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

            # 解析反思结果
            cleaned = re.sub(r'```(?:json)?\s*', '', response).strip()
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
        self, queries: List[str], company_name: str
    ) -> List[str]:
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
            cleaned = re.sub(r'```(?:json)?\s*', '', response).strip()
            cleaned = re.sub(r'```\s*$', '', cleaned).strip()
            json_match = re.search(r'\[[\s\S]*\]', cleaned)
            if json_match:
                optimized = json.loads(json_match.group())
                if isinstance(optimized, list) and optimized:
                    return [str(q) for q in optimized[:5]]
        except Exception as e:
            logger.warning(f"关键词优化失败: {e}")

        return queries[:5]

    async def _generate_final_summary(
        self, state: ResearchState, dimensions: List[str]
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
            return await agent.chat(
                message=prompt,
                system_prompt_override="你是资深企业调查分析师，擅长将多源信息综合为简明结论。",
            )
        except Exception as e:
            logger.warning(f"生成最终摘要失败: {e}")
            return f"对「{state.company_name}」的深度研究完成，共 {state.round_num} 轮搜索。"


# 全局实例
deep_research_engine = DeepResearchEngine()
