# -*- coding: utf-8 -*-
"""
AutoDream — 后台记忆巩固引擎（做梦机制）

灵感来源：Claude Code autoDream 系统
- 映射人类 REM 睡眠：将短期记忆（会话日志、调查结果）巩固为长期存储（用户画像、知识沉淀）
- 双门触发：时间门控(24h) + 活动门控(N次操作)
- 四阶段巩固：Orient → Gather → Consolidate → Prune

适配安心法务场景：
- 对话记忆巩固 → 用户法律画像演化
- 调查结果沉淀 → 知识图谱自动扩充
- 跨会话模式识别 → 风险预警规则学习
- 过期/矛盾记忆修剪 → 保持记忆系统健康
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from loguru import logger


# ===== 触发门控配置 =====
DREAM_CONFIG = {
    "min_hours_since_last": 24,       # 距上次做梦至少 24 小时
    "min_activities_since_last": 5,    # 至少 5 次活动（调查/咨询/搜索）
    "max_consolidation_minutes": 10,   # 单次做梦最长 10 分钟
    "memory_index_max_lines": 200,     # 记忆索引最大行数
    "stale_memory_days": 30,           # 30 天未更新视为过期
}


class DreamState:
    """做梦状态追踪"""

    def __init__(self):
        self.last_dream_time: Optional[datetime] = None
        self.activities_since_last: int = 0
        self.is_dreaming: bool = False
        self.dream_history: List[Dict[str, Any]] = []

    def record_activity(self):
        """记录一次用户活动"""
        self.activities_since_last += 1

    def should_dream(self) -> bool:
        """双门触发检查"""
        if self.is_dreaming:
            return False

        # 时间门控
        if self.last_dream_time:
            hours_elapsed = (datetime.now() - self.last_dream_time).total_seconds() / 3600
            if hours_elapsed < DREAM_CONFIG["min_hours_since_last"]:
                return False

        # 活动门控
        if self.activities_since_last < DREAM_CONFIG["min_activities_since_last"]:
            return False

        return True

    def start_dream(self):
        self.is_dreaming = True

    def end_dream(self, summary: Dict[str, Any]):
        self.is_dreaming = False
        self.last_dream_time = datetime.now()
        self.activities_since_last = 0
        self.dream_history.append({
            "time": self.last_dream_time.isoformat(),
            "summary": summary,
        })
        # 只保留最近 20 次
        if len(self.dream_history) > 20:
            self.dream_history = self.dream_history[-20:]


class AutoDreamEngine:
    """
    后台记忆巩固引擎

    四阶段流程：
    1. Orient（定向）— 扫描当前记忆系统状态
    2. Gather（收集信号）— 从近期活动中提取模式
    3. Consolidate（巩固）— 合并、去重、更新记忆
    4. Prune（修剪）— 清理过期/矛盾记忆，更新索引
    """

    def __init__(self):
        self._state: Dict[str, DreamState] = {}  # per-user state

    def get_state(self, user_id: str) -> DreamState:
        if user_id not in self._state:
            self._state[user_id] = DreamState()
        return self._state[user_id]

    def record_activity(self, user_id: str, activity_type: str = "general"):
        """记录用户活动（由各服务调用）"""
        state = self.get_state(user_id)
        state.record_activity()

        # 检查是否应该触发做梦
        if state.should_dream():
            # 异步触发，不阻塞当前请求
            asyncio.create_task(self._dream_background(user_id))

    async def trigger_dream(self, user_id: str, force: bool = False) -> Dict[str, Any]:
        """手动触发做梦（管理接口或定时任务）"""
        state = self.get_state(user_id)
        if state.is_dreaming:
            return {"status": "already_dreaming"}
        if not force and not state.should_dream():
            return {"status": "not_ready", "activities": state.activities_since_last}

        return await self._dream(user_id)

    async def _dream_background(self, user_id: str):
        """后台执行做梦，不阻塞"""
        try:
            await self._dream(user_id)
        except Exception as e:
            logger.error(f"AutoDream 后台巩固失败 (user={user_id}): {e}")

    async def _dream(self, user_id: str) -> Dict[str, Any]:
        """执行完整的四阶段做梦流程"""
        state = self.get_state(user_id)
        state.start_dream()
        start_time = datetime.now()
        summary: Dict[str, Any] = {
            "user_id": user_id,
            "start_time": start_time.isoformat(),
            "phases": {},
        }

        try:
            # Phase 1: Orient — 扫描记忆现状
            orient_result = await self._phase_orient(user_id)
            summary["phases"]["orient"] = orient_result

            # Phase 2: Gather — 收集近期信号
            signals = await self._phase_gather(user_id, orient_result)
            summary["phases"]["gather"] = {
                "signals_found": len(signals),
                "signal_types": list(set(s.get("type", "unknown") for s in signals)),
            }

            # Phase 3: Consolidate — 巩固记忆
            consolidation = await self._phase_consolidate(user_id, orient_result, signals)
            summary["phases"]["consolidate"] = consolidation

            # Phase 4: Prune — 修剪和索引
            prune_result = await self._phase_prune(user_id)
            summary["phases"]["prune"] = prune_result

            duration = (datetime.now() - start_time).total_seconds()
            summary["duration_seconds"] = round(duration, 1)
            summary["status"] = "completed"

            logger.info(
                f"AutoDream 完成 (user={user_id}): "
                f"{consolidation.get('memories_updated', 0)} 条记忆更新, "
                f"{prune_result.get('memories_pruned', 0)} 条修剪, "
                f"耗时 {duration:.1f}s"
            )

        except Exception as e:
            summary["status"] = "failed"
            summary["error"] = str(e)
            logger.error(f"AutoDream 失败 (user={user_id}): {e}")

        finally:
            state.end_dream(summary)

        return summary

    # ===== Phase 1: Orient =====

    async def _phase_orient(self, user_id: str) -> Dict[str, Any]:
        """扫描当前记忆系统状态，建立心智地图"""
        result = {
            "user_profiles": {},
            "investigation_count": 0,
            "memory_entries": 0,
            "graph_entities": 0,
            "stale_memories": [],
        }

        try:
            # 扫描用户调查偏好
            from src.services.investigation_data_store import investigation_data_store
            if investigation_data_store:
                prefs = await investigation_data_store.get_user_preference(user_id)
                if prefs:
                    result["user_profiles"] = {
                        "total_investigations": prefs.get("total_investigations", 0),
                        "favorite_companies": prefs.get("favorite_companies", []),
                        "frequent_industries": prefs.get("frequent_industries", []),
                    }
                    result["investigation_count"] = prefs.get("total_investigations", 0)
        except Exception as e:
            logger.debug(f"Orient - 调查偏好扫描跳过: {e}")

        try:
            # 扫描情景记忆
            from src.services.episodic_memory_service import episodic_memory_service
            recent = await episodic_memory_service.get_recent_memories(limit=50)
            result["memory_entries"] = len(recent) if recent else 0

            # 识别过期记忆
            cutoff = datetime.now() - timedelta(days=DREAM_CONFIG["stale_memory_days"])
            for mem in (recent or []):
                mem_time = mem.get("timestamp", "")
                if mem_time and mem_time < cutoff.isoformat():
                    result["stale_memories"].append(mem.get("memory_id", ""))
        except Exception as e:
            logger.debug(f"Orient - 情景记忆扫描跳过: {e}")

        try:
            # 扫描知识图谱
            from src.services.graph_service import graph_service
            stats = await graph_service.get_graph_stats()
            result["graph_entities"] = stats.get("total_nodes", 0)
        except Exception as e:
            logger.debug(f"Orient - 图谱扫描跳过: {e}")

        return result

    # ===== Phase 2: Gather =====

    async def _phase_gather(
        self, user_id: str, orient: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """从近期活动中收集信号（模式识别）"""
        signals: List[Dict[str, Any]] = []

        try:
            # 信号1: 最近的调查结果
            from src.services.investigation_data_store import investigation_data_store
            if investigation_data_store:
                recent_investigations = await investigation_data_store.get_recent_investigations(
                    user_id, limit=10
                )
                for inv in (recent_investigations or []):
                    risk = inv.get("risk", {})
                    if risk:
                        # 识别高风险模式
                        for dim, score in risk.items():
                            if isinstance(score, (int, float)) and score > 60:
                                signals.append({
                                    "type": "high_risk_pattern",
                                    "company": inv.get("company_name", ""),
                                    "dimension": dim,
                                    "score": score,
                                    "time": inv.get("created_at", ""),
                                })
        except Exception as e:
            logger.debug(f"Gather - 调查信号收集跳过: {e}")

        try:
            # 信号2: 重复搜索的企业/关键词
            from src.services.investigation_data_store import investigation_data_store
            if investigation_data_store:
                prefs = await investigation_data_store.get_user_preference(user_id)
                if prefs:
                    favorites = prefs.get("favorite_companies", [])
                    for fav in (favorites or []):
                        if isinstance(fav, dict) and fav.get("count", 0) >= 3:
                            signals.append({
                                "type": "repeated_interest",
                                "company": fav.get("name", ""),
                                "count": fav.get("count", 0),
                            })
        except Exception as e:
            logger.debug(f"Gather - 重复模式识别跳过: {e}")

        try:
            # 信号3: 从情景记忆中提取跨会话模式
            from src.services.episodic_memory_service import episodic_memory_service
            recent = await episodic_memory_service.get_recent_memories(limit=20)
            if recent:
                # 统计高频任务类型
                task_types: Dict[str, int] = {}
                for mem in recent:
                    task = mem.get("task_type", mem.get("original_task", ""))
                    if task:
                        key = task[:50]  # 截断
                        task_types[key] = task_types.get(key, 0) + 1

                for task, count in task_types.items():
                    if count >= 3:
                        signals.append({
                            "type": "frequent_task",
                            "task": task,
                            "count": count,
                        })
        except Exception as e:
            logger.debug(f"Gather - 情景模式提取跳过: {e}")

        return signals

    # ===== Phase 3: Consolidate =====

    async def _phase_consolidate(
        self,
        user_id: str,
        orient: Dict[str, Any],
        signals: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        巩固记忆：将信号转化为长期记忆

        操作：
        1. 更新用户法律画像（行业偏好、风险关注点）
        2. 将高风险发现沉淀到知识图谱
        3. 合并重复的情景记忆
        4. 生成跨会话洞察
        """
        result = {
            "memories_updated": 0,
            "profiles_enriched": 0,
            "graph_entities_added": 0,
            "insights_generated": [],
        }

        # 1. 更新用户偏好画像
        try:
            from src.services.investigation_data_store import investigation_data_store
            if investigation_data_store:
                risk_signals = [s for s in signals if s["type"] == "high_risk_pattern"]
                if risk_signals:
                    # 统计用户最关注的风险维度
                    dim_counts: Dict[str, int] = {}
                    for s in risk_signals:
                        dim = s.get("dimension", "")
                        dim_counts[dim] = dim_counts.get(dim, 0) + 1

                    # 转化为权重
                    total = sum(dim_counts.values())
                    weights = {d: round(c / total, 2) for d, c in dim_counts.items()}

                    await investigation_data_store.update_user_preference(
                        user_id, risk_focus_weights=weights
                    )
                    result["profiles_enriched"] += 1
        except Exception as e:
            logger.debug(f"Consolidate - 画像更新跳过: {e}")

        # 2. 将调查发现沉淀到知识图谱
        try:
            from src.services.graph_service import graph_service
            high_risk_companies = set()
            for s in signals:
                if s["type"] == "high_risk_pattern" and s.get("company"):
                    high_risk_companies.add(s["company"])

            for company in high_risk_companies:
                try:
                    await graph_service.create_entity(
                        name=company,
                        entity_type="调查对象",
                        properties={"source": "auto_dream", "risk_level": "high"},
                    )
                    result["graph_entities_added"] += 1
                except Exception:
                    pass  # 实体可能已存在
        except Exception as e:
            logger.debug(f"Consolidate - 图谱沉淀跳过: {e}")

        # 3. 生成跨会话洞察
        repeated = [s for s in signals if s["type"] == "repeated_interest"]
        frequent_tasks = [s for s in signals if s["type"] == "frequent_task"]

        if repeated:
            companies = [s["company"] for s in repeated]
            result["insights_generated"].append(
                f"用户持续关注以下企业：{'、'.join(companies[:5])}，建议设置自动监控"
            )

        if frequent_tasks:
            tasks = [s["task"] for s in frequent_tasks[:3]]
            result["insights_generated"].append(
                f"用户高频操作模式：{'；'.join(tasks)}，可优化快捷入口"
            )

        result["memories_updated"] = result["profiles_enriched"] + result["graph_entities_added"]
        return result

    # ===== Phase 4: Prune =====

    async def _phase_prune(self, user_id: str) -> Dict[str, Any]:
        """修剪过期记忆，维护索引健康"""
        result = {
            "memories_pruned": 0,
            "cache_cleaned": 0,
        }

        # 清理过期搜索缓存
        try:
            from src.services.investigation_data_store import investigation_data_store
            if investigation_data_store:
                cleaned = await investigation_data_store.clean_expired_cache()
                result["cache_cleaned"] = cleaned or 0
        except Exception as e:
            logger.debug(f"Prune - 缓存清理跳过: {e}")

        return result

    # ===== 状态查询 =====

    def get_dream_status(self, user_id: str) -> Dict[str, Any]:
        """获取用户的做梦状态"""
        state = self.get_state(user_id)
        return {
            "is_dreaming": state.is_dreaming,
            "last_dream_time": state.last_dream_time.isoformat() if state.last_dream_time else None,
            "activities_since_last": state.activities_since_last,
            "ready_to_dream": state.should_dream(),
            "recent_dreams": state.dream_history[-5:],
            "config": DREAM_CONFIG,
        }


# 全局实例
auto_dream_engine = AutoDreamEngine()
