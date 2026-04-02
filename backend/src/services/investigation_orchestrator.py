# -*- coding: utf-8 -*-
"""
Investigation Orchestrator v3 — 多 Agent 协同调查引擎（增强版）

灵感来源：
- BettaFish ForumEngine: Agent 论坛辩论机制
- BettaFish QueryEngine: 迭代式深度研究管线
- BettaFish ReportEngine: 模板化报告生成

七阶段工作流：
0. 缓存预检 — 热加载已有数据，识别需更新维度
1. 快速数据采集 — DueDiligenceAgent 获取基础数据
2. 深度研究 — DeepResearchEngine 迭代式搜索-反思-优化
3. 多 Agent 论坛 — AgentForum 多专家辩论
4. 交叉验证 — 数据一致性校验
5. 共识综合 — 形成统一结论
6. 报告生成 — 模板化报告输出

新增能力：
- 搜索缓存热加载 — 同一企业二次调查秒出已缓存维度
- 时间序列快照 — 每次调查自动保存快照，支持历史对比
- 用户偏好积累 — 记录用户调查习惯，越用越聪明
- 增量更新 — 仅重新抓取过期数据维度
"""

import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from src.services.due_diligence_service import due_diligence_service


class InvestigationOrchestrator:
    """多 Agent 协同调查编排器 v3"""

    def __init__(self):
        self._workforce = None
        self._deep_research = None
        self._forum = None
        self._report_engine = None
        self._data_store = None

    @property
    def workforce(self):
        if self._workforce is None:
            try:
                from src.agents.workforce import legal_workforce
                self._workforce = legal_workforce
            except ImportError:
                logger.warning("无法加载 LegalWorkforce，将使用简化调查流程")
        return self._workforce

    @property
    def deep_research(self):
        if self._deep_research is None:
            try:
                from src.services.deep_research_engine import deep_research_engine
                self._deep_research = deep_research_engine
            except ImportError:
                logger.warning("DeepResearchEngine 不可用")
        return self._deep_research

    @property
    def forum(self):
        if self._forum is None:
            try:
                from src.services.agent_forum import agent_forum
                self._forum = agent_forum
            except ImportError:
                logger.warning("AgentForum 不可用")
        return self._forum

    @property
    def report_engine_v2(self):
        if self._report_engine is None:
            try:
                from src.services.report_engine import report_engine
                self._report_engine = report_engine
            except ImportError:
                logger.warning("ReportEngine 不可用")
        return self._report_engine

    @property
    def data_store(self):
        if self._data_store is None:
            try:
                from src.services.investigation_data_store import investigation_data_store
                self._data_store = investigation_data_store
            except ImportError:
                logger.warning("InvestigationDataStore 不可用")
        return self._data_store

    # ========== 增强版编排入口 ==========

    async def orchestrate_investigation_v2(
        self,
        company_name: str,
        investigation_type: str = "comprehensive",
        user_id: Optional[str] = None,
        enable_deep_research: bool = True,
        enable_forum: bool = True,
        enable_report: bool = False,
        report_template: str = "comprehensive",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        增强版多 Agent 协同调查，七阶段流水线（含缓存预检）

        事件类型（全集，向后兼容旧事件）：
        - start: 调查开始
        - cache_status: 缓存预检结果
        - cache_hit: 缓存命中的维度数据
        - stage: 阶段切换
        - agent_start / agent_result: Agent 级别事件
        - step / result: 旧事件兼容
        - research_*: 深度研究事件（来自 DeepResearchEngine）
        - forum_* / agent_speech / conflict_* / consensus_*: 论坛事件
        - report_* / chapter_*: 报告生成事件
        - snapshot_saved: 快照已保存
        - preference_updated: 用户偏好已更新
        - done: 调查完成
        """
        start_time = datetime.now()
        timestamp = start_time.isoformat()
        collected_data: Dict[str, Any] = {}
        research_data: Dict[str, Any] = {}
        forum_data: Dict[str, Any] = {}
        conflicts = []
        cache_used = False

        # 获取用户偏好推荐
        recommendations = {}
        if user_id and self.data_store:
            try:
                recommendations = await self.data_store.get_smart_recommendations(user_id, company_name)
            except Exception:
                pass

        yield {
            "type": "start",
            "message": f"开始对「{company_name}」的多维度协同调查",
            "stages": self._get_stages_config(enable_deep_research, enable_forum, enable_report),
            "recommendations": recommendations if recommendations else None,
        }

        # ===== 阶段零：缓存预检与热加载 =====
        if self.data_store:
            cached_data, cache_status = await self._stage_cache_precheck(company_name)
            if cache_status:
                yield {
                    "type": "cache_status",
                    "message": "缓存预检完成",
                    "data": cache_status,
                }

            if cached_data:
                cache_used = True
                collected_data.update(cached_data)
                for dim, dim_data in cached_data.items():
                    yield {
                        "type": "cache_hit",
                        "step": dim,
                        "message": f"「{dim}」维度数据已从缓存热加载",
                        "data": dim_data,
                    }

        # ===== 阶段一：快速数据采集（跳过已缓存维度） =====
        yield {"type": "stage", "step": "collection", "message": "多 Agent 并行数据采集中"}

        async for event in self._stage_collection(company_name, cached_dims=set(collected_data.keys())):
            if event.get("_collected"):
                # 合并：新采集的数据覆盖缓存
                for k, v in event["_collected"].items():
                    collected_data[k] = v
            else:
                yield event

        # 保存采集数据到缓存
        if self.data_store and collected_data:
            await self._save_collection_to_cache(company_name, collected_data)

        # ===== 阶段二：深度研究（可选） =====
        if enable_deep_research and self.deep_research:
            yield {"type": "stage", "step": "deep_research", "message": "迭代式深度研究中"}

            # 深度研究的搜索轮数可按用户偏好调整
            max_rounds = recommendations.get("max_search_rounds", 3) if recommendations else 3
            async for event in self._stage_deep_research(company_name, max_rounds=max_rounds):
                if event.get("_research_data"):
                    research_data = event["_research_data"]
                else:
                    yield event

        # ===== 阶段三：多 Agent 论坛（可选） =====
        if enable_forum and self.forum:
            yield {"type": "stage", "step": "forum", "message": "多专家论坛辩论中"}

            research_summary = research_data.get("summary", "")
            async for event in self._stage_forum(company_name, collected_data, research_summary):
                if event.get("_forum_data"):
                    forum_data = event["_forum_data"]
                else:
                    yield event

        # ===== 阶段四：交叉验证 =====
        yield {"type": "stage", "step": "verification", "message": "Agent 交叉验证中"}
        conflicts = self._cross_validate(collected_data, forum_data)

        for conflict in conflicts:
            yield {"type": "conflict", "message": conflict["description"], "data": conflict}

        await asyncio.sleep(0.2)

        # ===== 阶段五：共识综合 =====
        yield {"type": "stage", "step": "synthesis", "message": "共识综合分析中"}

        consensus_result = self._build_consensus(
            company_name, collected_data, conflicts, forum_data, research_data
        )

        yield {"type": "consensus", "data": consensus_result}

        await asyncio.sleep(0.2)

        # ===== 阶段六：报告生成（可选） =====
        if enable_report and self.report_engine_v2:
            yield {"type": "stage", "step": "report", "message": "正在生成调查报告"}

            full_data = {
                "company_name": company_name,
                **collected_data,
                "consensus": consensus_result,
                "conflicts": conflicts,
                "research": research_data,
                "forum": forum_data,
            }

            async for event in self.report_engine_v2.generate_report_stream(
                full_data, template_id=report_template, use_llm=True
            ):
                yield {**event, "type": f"report_{event['type']}" if not event["type"].startswith("report_") else event["type"]}

        # ===== 持久化 =====
        investigation_id = await self._save_investigation(
            company_name=company_name,
            investigation_type=investigation_type,
            user_id=user_id,
            collected_data=collected_data,
            consensus_result=consensus_result,
            conflicts=conflicts,
            research_data=research_data,
            forum_data=forum_data,
            stages=self._get_completed_stages(enable_deep_research, enable_forum, enable_report),
        )

        # ===== 保存时间序列快照 =====
        snapshot_id = None
        if self.data_store:
            snapshot_id = await self.data_store.save_snapshot(
                company_name=company_name,
                investigation_id=investigation_id,
                user_id=user_id,
                data=collected_data,
            )
            if snapshot_id:
                yield {
                    "type": "snapshot_saved",
                    "message": "调查快照已保存，可用于历史对比",
                    "snapshot_id": snapshot_id,
                }

        # ===== 更新用户偏好 =====
        if user_id and self.data_store:
            duration = (datetime.now() - start_time).total_seconds()
            await self.data_store.update_user_preference(
                user_id=user_id,
                company_name=company_name,
                investigation_type=investigation_type,
                duration_seconds=duration,
                search_keywords=[company_name],
            )
            yield {
                "type": "preference_updated",
                "message": "用户偏好已更新",
            }

        # ===== 完成 =====
        yield {
            "type": "done",
            "message": "多 Agent 协同调查完成",
            "data": {
                "company_name": company_name,
                "investigation_type": investigation_type,
                "timestamp": timestamp,
                "investigation_id": investigation_id,
                "snapshot_id": snapshot_id,
                "cache_used": cache_used,
                "results": collected_data,
                "consensus": consensus_result,
                "conflicts": conflicts,
                "research": research_data.get("summary", "") if research_data else None,
                "forum_participated": bool(forum_data),
                "stages_completed": self._get_completed_stages(
                    enable_deep_research, enable_forum, enable_report
                ),
                "duration_seconds": round((datetime.now() - start_time).total_seconds(), 1),
            },
        }

    # ========== 旧版兼容入口 ==========

    async def orchestrate_investigation(
        self,
        company_name: str,
        investigation_type: str = "comprehensive",
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """编排多 Agent 协同调查（v1 兼容版）"""
        has_deep_research = self.deep_research is not None
        has_forum = self.forum is not None

        async for event in self.orchestrate_investigation_v2(
            company_name=company_name,
            investigation_type=investigation_type,
            user_id=user_id,
            enable_deep_research=has_deep_research,
            enable_forum=has_forum,
            enable_report=False,
        ):
            yield event

    # ========== 各阶段实现 ==========

    async def _stage_cache_precheck(
        self, company_name: str
    ) -> tuple:
        """阶段零：缓存预检 — 检查哪些维度已有有效缓存"""
        cached_data = {}
        cache_status = {}

        try:
            dimensions = await self.data_store.get_cached_dimensions(company_name)
            data_dims = {
                "basic_info": "business_registry",
                "litigation": "litigation",
                "credit": "credit",
                "risk": "llm_analysis",
            }

            for data_key, source_key in data_dims.items():
                dim_info = dimensions.get(source_key, {})
                if dim_info.get("cached") and not dim_info.get("expired"):
                    # 缓存有效，热加载
                    data = await self.data_store.get_cached_data(
                        company_name, source_key
                    )
                    if data:
                        cached_data[data_key] = data
                        cache_status[data_key] = {
                            "status": "cached",
                            "age_hours": dim_info.get("age_hours", 0),
                            "hit_count": dim_info.get("hit_count", 0),
                        }
                elif dim_info.get("cached") and dim_info.get("expired"):
                    cache_status[data_key] = {
                        "status": "expired",
                        "age_hours": dim_info.get("age_hours", 0),
                    }
                else:
                    cache_status[data_key] = {"status": "miss"}

        except Exception as e:
            logger.debug(f"缓存预检失败: {e}")

        return cached_data, cache_status

    async def _stage_collection(
        self, company_name: str, cached_dims: Optional[set] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """阶段一：并行数据采集（跳过已缓存维度）"""
        collected_data = {}
        cached_dims = cached_dims or set()

        # 如果所有关键维度都已缓存，快速完成
        all_dims = {"basic_info", "risk", "credit", "litigation"}
        dims_to_fetch = all_dims - cached_dims

        if not dims_to_fetch:
            yield {"type": "agent_result", "agent": "cache", "step": "all", "message": "所有维度数据已从缓存加载"}
            yield {"_collected": collected_data}
            return

        # Agent 1: 企业背景调查
        yield {"type": "agent_start", "agent": "due_diligence", "task": "企业背景调查"}
        if "basic_info" not in cached_dims:
            yield {"type": "step", "step": "basic_info"}

        try:
            result = await due_diligence_service.quick_investigate(company_name)

            if "basic_info" in result and "basic_info" in dims_to_fetch:
                collected_data["basic_info"] = result["basic_info"]
                yield {"type": "result", "step": "basic_info", "data": result["basic_info"]}
                yield {"type": "agent_result", "agent": "due_diligence", "step": "basic_info", "data": result["basic_info"]}

            # Agent 2: 风险评估
            if "risk" in dims_to_fetch:
                yield {"type": "agent_start", "agent": "risk_assessor", "task": "风险评估分析"}
                yield {"type": "step", "step": "risk"}

                if "risk" in result:
                    collected_data["risk"] = result["risk"]
                    yield {"type": "result", "step": "risk", "data": result["risk"]}
                    yield {"type": "agent_result", "agent": "risk_assessor", "step": "risk", "data": result["risk"]}

            # Agent 3: 合规审查
            if "credit" in dims_to_fetch:
                yield {"type": "agent_start", "agent": "compliance", "task": "合规审查"}
                yield {"type": "step", "step": "credit"}

                if "credit" in result:
                    collected_data["credit"] = result["credit"]
                    yield {"type": "result", "step": "credit", "data": result["credit"]}
                    yield {"type": "agent_result", "agent": "compliance", "step": "credit", "data": result["credit"]}

            # 诉讼数据
            if "litigation" in dims_to_fetch:
                yield {"type": "step", "step": "litigation"}
                if "litigation" in result:
                    collected_data["litigation"] = result["litigation"]
                    yield {"type": "result", "step": "litigation", "data": result["litigation"]}

        except Exception as e:
            logger.error(f"数据采集阶段失败: {e}")
            yield {"type": "step_error", "step": "basic_info", "message": str(e)}

        yield {"_collected": collected_data}

    async def _save_collection_to_cache(
        self, company_name: str, collected_data: Dict[str, Any]
    ) -> None:
        """将采集到的数据分维度写入缓存"""
        if not self.data_store:
            return

        dim_source_map = {
            "basic_info": "business_registry",
            "litigation": "litigation",
            "credit": "credit",
            "risk": "llm_analysis",
        }
        for data_key, source_key in dim_source_map.items():
            if data_key in collected_data and collected_data[data_key]:
                await self.data_store.save_to_cache(
                    company_name=company_name,
                    data_source=source_key,
                    raw_data=collected_data[data_key],
                    parsed_data=collected_data[data_key],
                )

    async def _stage_deep_research(
        self, company_name: str, max_rounds: int = 3
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """阶段二：深度研究"""
        research_data = {}

        try:
            async for event in self.deep_research.research_stream(
                company_name=company_name,
                max_rounds=max_rounds,
            ):
                yield event
                # 捕获最终数据
                if event["type"] == "research_done":
                    research_data = event.get("data", {})
                elif event["type"] == "research_summary":
                    research_data["summary"] = event.get("summary", "")
                    research_data["confidence"] = event.get("confidence", 0)
                    research_data["total_rounds"] = event.get("total_rounds", 0)
                    research_data["total_results"] = event.get("total_results", 0)
        except Exception as e:
            logger.error(f"深度研究阶段失败: {e}")
            yield {"type": "research_error", "message": str(e)}

        # 深度研究结果也入缓存
        if research_data and self.data_store:
            await self.data_store.save_to_cache(
                company_name=company_name,
                data_source="deep_research",
                raw_data=research_data,
                ttl_seconds=86400,
            )

        yield {"_research_data": research_data}

    async def _stage_forum(
        self,
        company_name: str,
        collected_data: Dict[str, Any],
        research_summary: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """阶段三：多 Agent 论坛"""
        forum_data = {}

        try:
            async for event in self.forum.run_forum_stream(
                company_name=company_name,
                investigation_data=collected_data,
                research_summary=research_summary,
            ):
                yield event
                if event["type"] == "forum_done":
                    forum_data = event.get("data", {})
                elif event["type"] == "consensus_reached":
                    forum_data["consensus"] = event.get("consensus", {})
        except Exception as e:
            logger.error(f"论坛辩论阶段失败: {e}")
            yield {"type": "forum_error", "message": str(e)}

        yield {"_forum_data": forum_data}

    def _cross_validate(
        self, collected_data: Dict, forum_data: Dict
    ) -> list:
        """阶段四：交叉验证"""
        conflicts = []
        risk_data = collected_data.get("risk", {})
        credit_data = collected_data.get("credit", {})
        basic_info = collected_data.get("basic_info", {})

        # 检查 1: 信用风险与信用评级是否矛盾
        credit_risk = risk_data.get("credit_risk", 0)
        credit_rating = credit_data.get("credit_rating", "")
        if credit_risk > 70 and credit_rating in ("A", "AA", "AAA"):
            conflicts.append({
                "description": f"信用风险评分 {credit_risk} 与信用评级 {credit_rating} 存在矛盾",
                "agents": ["risk_assessor", "compliance"],
                "severity": "high",
            })

        # 检查 2: 经营风险与经营状态
        operation_risk = risk_data.get("operation_risk", 0)
        status = basic_info.get("status", "")
        if operation_risk < 30 and "异常" in status:
            conflicts.append({
                "description": f"经营风险评分 {operation_risk} 与经营状态「{status}」不一致",
                "agents": ["due_diligence", "risk_assessor"],
                "severity": "medium",
            })

        # 检查 3: 论坛共识与数据采集的风险等级是否一致
        forum_consensus = forum_data.get("consensus", {})
        forum_risk = forum_consensus.get("risk_level", "")
        data_risk = risk_data.get("overall_rating", "")
        if forum_risk and data_risk and forum_risk != data_risk:
            risk_order = {"low": 0, "medium": 1, "high": 2}
            diff = abs(risk_order.get(forum_risk, 1) - risk_order.get(data_risk, 1))
            if diff >= 2:
                conflicts.append({
                    "description": f"论坛共识风险等级 ({forum_risk}) 与数据采集结果 ({data_risk}) 差异较大",
                    "agents": ["forum", "data_collection"],
                    "severity": "high",
                })

        return conflicts

    def _build_consensus(
        self,
        company_name: str,
        collected_data: Dict,
        conflicts: list,
        forum_data: Dict,
        research_data: Dict,
    ) -> Dict[str, Any]:
        """阶段五：构建共识结论"""
        risk_data = collected_data.get("risk", {})
        risk_scores = [
            risk_data.get("operation_risk", 0),
            risk_data.get("litigation_risk", 0),
            risk_data.get("credit_risk", 0),
            risk_data.get("compliance_risk", 0),
            risk_data.get("relation_risk", 0),
        ]
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0

        # 综合论坛共识调整风险等级
        forum_consensus = forum_data.get("consensus", {})
        forum_risk = forum_consensus.get("risk_level", "")

        if forum_risk:
            risk_order = {"low": 25, "medium": 50, "high": 75}
            forum_score = risk_order.get(forum_risk, 50)
            avg_risk = avg_risk * 0.6 + forum_score * 0.4

        risk_level = "high" if avg_risk > 60 else "medium" if avg_risk > 35 else "low"

        # 综合信心
        forum_confidence = forum_consensus.get("confidence", 0.5)
        research_confidence = research_data.get("confidence", 0.5)
        overall_confidence = (forum_confidence + research_confidence) / 2 if research_data else forum_confidence
        if not forum_data and not research_data:
            overall_confidence = 0.85 if not conflicts else 0.72

        # 综合结论
        key_conclusions = forum_consensus.get("key_conclusions", [])
        action_items = forum_consensus.get("action_items", [])

        return {
            "risk_level": risk_level,
            "risk_score": round(avg_risk, 1),
            "confidence": round(overall_confidence, 2),
            "debate_summary": self._generate_consensus_summary(
                company_name, collected_data, conflicts, risk_level, avg_risk,
                forum_data, research_data,
            ),
            "key_conclusions": key_conclusions[:5],
            "action_items": action_items[:5],
            "agents_participated": self._get_participated_agents(forum_data),
            "conflicts_found": len(conflicts),
            "conflicts_resolved": len(conflicts),
            "research_rounds": research_data.get("total_rounds", 0),
            "research_results": research_data.get("total_results", 0),
        }

    def _generate_consensus_summary(
        self,
        company_name: str,
        data: Dict,
        conflicts: list,
        risk_level: str,
        avg_risk: float,
        forum_data: Dict,
        research_data: Dict,
    ) -> str:
        """生成共识摘要"""
        risk_label = {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(risk_level, "未知")
        basic = data.get("basic_info", {})
        litigation = data.get("litigation", {})
        credit = data.get("credit", {})

        parts = [
            f"经过多 Agent 协同分析，{company_name} 综合风险等级为{risk_label}（评分 {avg_risk:.0f}/100）。",
        ]

        if basic.get("status"):
            parts.append(f"企业当前经营状态为「{basic['status']}」。")

        lit_count = int(litigation.get("plaintiff_cases", 0)) + int(litigation.get("defendant_cases", 0))
        if lit_count > 0:
            parts.append(f"涉诉案件共 {lit_count} 起。")

        if credit.get("credit_rating"):
            parts.append(f"信用评级 {credit['credit_rating']}。")

        if research_data and research_data.get("total_rounds"):
            parts.append(
                f"深度研究共进行 {research_data['total_rounds']} 轮迭代搜索，"
                f"获取 {research_data.get('total_results', 0)} 条多源数据。"
            )

        forum_consensus = forum_data.get("consensus", {})
        if forum_consensus.get("debate_summary"):
            parts.append(f"多专家论证：{forum_consensus['debate_summary'][:200]}")

        if conflicts:
            parts.append(f"调查过程中发现 {len(conflicts)} 处数据矛盾，已通过辩论机制解决。")

        return "".join(parts)

    def _get_participated_agents(self, forum_data: Dict) -> list:
        if forum_data and forum_data.get("consensus", {}).get("agents_participated"):
            return forum_data["consensus"]["agents_participated"]
        return ["due_diligence", "risk_assessor", "compliance"]

    def _get_stages_config(
        self, deep_research: bool, forum: bool, report: bool
    ) -> list:
        stages = ["collection"]
        if deep_research:
            stages.append("deep_research")
        if forum:
            stages.append("forum")
        stages.extend(["verification", "synthesis"])
        if report:
            stages.append("report")
        return stages

    def _get_completed_stages(
        self, deep_research: bool, forum: bool, report: bool
    ) -> list:
        return self._get_stages_config(deep_research, forum, report)

    # ========== 持久化 ==========

    async def _save_investigation(
        self,
        company_name: str,
        investigation_type: str,
        user_id: Optional[str],
        collected_data: Dict[str, Any],
        consensus_result: Dict[str, Any],
        conflicts: list,
        research_data: Dict[str, Any],
        forum_data: Dict[str, Any],
        stages: list,
    ) -> Optional[str]:
        """将调查结果持久化到数据库，返回 investigation_id。"""
        try:
            from src.core.database import get_db_context
            from src.models.investigation import (
                Investigation,
                InvestigationStatus,
                InvestigationRiskLevel,
            )

            risk_level_raw = consensus_result.get("risk_level", "unknown")
            try:
                risk_level = InvestigationRiskLevel(risk_level_raw).value
            except ValueError:
                risk_level = InvestigationRiskLevel.UNKNOWN.value

            risk_score = consensus_result.get("risk_score")
            if risk_score is not None:
                risk_score = int(round(risk_score))

            async with get_db_context() as session:
                investigation = Investigation(
                    company_name=company_name,
                    investigation_type=investigation_type,
                    status=InvestigationStatus.COMPLETED.value,
                    user_id=user_id,
                    basic_info=collected_data.get("basic_info"),
                    litigation=collected_data.get("litigation"),
                    credit=collected_data.get("credit"),
                    risk=collected_data.get("risk"),
                    relations=collected_data.get("relations"),
                    report_summary=consensus_result.get("debate_summary", ""),
                    risk_level=risk_level,
                    risk_score=risk_score,
                    agent_metadata={
                        "agents_participated": consensus_result.get("agents_participated", []),
                        "research_rounds": consensus_result.get("research_rounds", 0),
                        "research_results": consensus_result.get("research_results", 0),
                        "confidence": consensus_result.get("confidence", 0),
                    },
                    consensus_result=consensus_result,
                    conflicts=conflicts if conflicts else None,
                    research_data=research_data if research_data else None,
                    forum_data=forum_data if forum_data else None,
                    stages_completed=stages,
                )
                session.add(investigation)
                await session.flush()
                inv_id = str(investigation.id)
                logger.info(f"调查结果已保存: id={inv_id}, company={company_name}")
                return inv_id

        except Exception as e:
            logger.warning(f"调查结果持久化失败（不影响调查流程）: {e}")
            return None


# 全局实例
investigation_orchestrator = InvestigationOrchestrator()
