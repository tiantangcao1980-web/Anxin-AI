"""
Investigation Data Store — 调查数据持久化与缓存层

核心功能：
1. 搜索缓存热加载 — 同一企业二次调查秒出结果
2. 时间序列快照 — 不同时期数据对比，发现变化趋势
3. 用户偏好积累 — 越用越聪明，智能推荐
4. 增量更新 — 仅抓取缓存过期的维度

支持云端数据库（PostgreSQL）和本地绝密模式（SQLite）。
"""

import hashlib
from datetime import datetime
from typing import Any

from loguru import logger


class InvestigationDataStore:
    """调查数据存储服务"""

    # 各数据源的缓存 TTL（秒）
    CACHE_TTL = {
        "business_registry": 7 * 86400,   # 工商数据 7 天
        "web_search": 86400,              # 网络搜索 1 天
        "knowledge_base": 3 * 86400,      # 知识库 3 天
        "llm_analysis": 2 * 86400,        # LLM 分析 2 天
        "litigation": 3 * 86400,          # 诉讼数据 3 天
        "credit": 7 * 86400,             # 信用数据 7 天
        "news": 43200,                    # 新闻舆情 12 小时
    }

    # ========== 搜索缓存 ==========

    async def get_cached_data(
        self,
        company_name: str,
        data_source: str,
        query_text: str = "",
        max_age_seconds: int | None = None,
        org_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        从缓存获取数据。如命中且未过期，返回缓存数据并更新命中计数。

        Args:
            company_name: 企业名称
            data_source: 数据源类型
            query_text: 搜索查询文本
            max_age_seconds: 最大缓存年龄，None 则使用默认 TTL
            org_id: 组织 ID；为空时只读取全局/本地缓存，不读取其他组织缓存

        Returns:
            缓存的数据字典，或 None（未命中/已过期）
        """
        try:
            from sqlalchemy import and_, select

            from src.core.database import get_db_context
            from src.models.investigation import SearchCache

            cache_key = self._make_cache_key(company_name, data_source, query_text)
            ttl = max_age_seconds or self.CACHE_TTL.get(data_source, 86400)
            scope_org_id = self._normalize_org_id(org_id)

            async with get_db_context() as session:
                stmt = select(SearchCache).where(
                    and_(
                        SearchCache.cache_key == cache_key,
                        SearchCache.is_valid.is_(True),
                        self._org_scope_condition(SearchCache, scope_org_id),
                    )
                )
                result = await session.execute(stmt)
                cache = result.scalar_one_or_none()

                if not cache:
                    return None

                # 检查是否过期
                age = (datetime.utcnow() - cache.created_at.replace(tzinfo=None)).total_seconds()
                if age > ttl:
                    logger.debug(f"缓存过期: {cache_key} (age={age:.0f}s > ttl={ttl}s)")
                    return None

                # 命中：更新计数
                cache.hit_count += 1
                await session.flush()

                logger.info(
                    f"缓存命中: {company_name}/{data_source} "
                    f"org={scope_org_id or 'global'} (hits={cache.hit_count})"
                )
                return cache.parsed_data or cache.raw_data

        except Exception as e:
            logger.debug(f"缓存查询失败: {e}")
            return None

    async def save_to_cache(
        self,
        company_name: str,
        data_source: str,
        raw_data: Any,
        parsed_data: dict[str, Any] | None = None,
        query_text: str = "",
        ttl_seconds: int | None = None,
        org_id: str | None = None,
    ) -> bool:
        """
        保存搜索结果到缓存。如已有相同 key 的缓存，则更新。
        """
        try:
            from sqlalchemy import and_, select

            from src.core.database import get_db_context
            from src.models.investigation import SearchCache

            cache_key = self._make_cache_key(company_name, data_source, query_text)
            ttl = ttl_seconds or self.CACHE_TTL.get(data_source, 86400)
            scope_org_id = self._normalize_org_id(org_id)

            # 序列化
            if not isinstance(raw_data, dict):
                raw_data = {"data": raw_data} if raw_data else {}

            result_count = 0
            if isinstance(raw_data, dict):
                results = raw_data.get("results")
                if isinstance(results, list):
                    result_count = len(results)
                else:
                    items = raw_data.get("items")
                    if isinstance(items, list):
                        result_count = len(items)
                    else:
                        result_count = len(raw_data)

            async with get_db_context() as session:
                # 查找已有缓存
                stmt = select(SearchCache).where(
                    and_(
                        SearchCache.cache_key == cache_key,
                        self._org_scope_condition(SearchCache, scope_org_id),
                    )
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.org_id = scope_org_id
                    existing.raw_data = raw_data
                    existing.parsed_data = parsed_data
                    existing.result_count = result_count
                    existing.ttl_seconds = ttl
                    existing.is_valid = True
                    existing.hit_count = 0  # 重置命中计数
                else:
                    cache = SearchCache(
                        cache_key=cache_key,
                        org_id=scope_org_id,
                        company_name=company_name,
                        data_source=data_source,
                        query_text=query_text,
                        raw_data=raw_data,
                        parsed_data=parsed_data,
                        result_count=result_count,
                        ttl_seconds=ttl,
                    )
                    session.add(cache)

                logger.debug(
                    f"缓存已保存: {company_name}/{data_source} org={scope_org_id or 'global'}"
                )
                return True

        except Exception as e:
            logger.warning(f"缓存保存失败: {e}")
            return False

    async def get_cached_dimensions(
        self,
        company_name: str,
        user_id: str | None = None,
        org_id: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        获取某企业所有已缓存维度的状态

        Returns:
            {
                "business_registry": {"cached": True, "age_hours": 2.5, "hit_count": 3},
                "litigation": {"cached": True, "age_hours": 48.1, "expired": True},
                "web_search": {"cached": False},
            }
        """
        try:
            from sqlalchemy import and_, select

            from src.core.database import get_db_context
            from src.models.investigation import SearchCache

            scope_org_id = self._normalize_org_id(org_id)
            if user_id and not scope_org_id:
                return {}

            async with get_db_context() as session:
                stmt = select(SearchCache).where(
                    and_(
                        SearchCache.company_name == company_name,
                        SearchCache.is_valid.is_(True),
                        self._org_scope_condition(SearchCache, scope_org_id),
                    )
                )
                result = await session.execute(stmt)
                caches = result.scalars().all()

                dimensions = {}
                for cache in caches:
                    age_seconds = (
                        datetime.utcnow() - cache.created_at.replace(tzinfo=None)
                    ).total_seconds()
                    age_hours = age_seconds / 3600
                    expired = age_seconds > cache.ttl_seconds

                    dimensions[cache.data_source] = {
                        "cached": True,
                        "age_hours": round(age_hours, 1),
                        "expired": expired,
                        "hit_count": cache.hit_count,
                        "result_count": cache.result_count,
                        "cache_key": cache.cache_key,
                    }

                return dimensions

        except Exception as e:
            logger.debug(f"查询缓存维度失败: {e}")
            return {}

    async def invalidate_cache(
        self,
        company_name: str,
        data_source: str | None = None,
        user_id: str | None = None,
        org_id: str | None = None,
    ) -> int:
        """使某企业的缓存失效。返回失效条数。"""
        try:
            from sqlalchemy import and_, update

            from src.core.database import get_db_context
            from src.models.investigation import SearchCache

            scope_org_id = self._normalize_org_id(org_id)
            if user_id and not scope_org_id:
                return 0

            async with get_db_context() as session:
                conditions = [
                    SearchCache.company_name == company_name,
                    self._org_scope_condition(SearchCache, scope_org_id),
                ]
                if data_source:
                    conditions.append(SearchCache.data_source == data_source)

                stmt = (
                    update(SearchCache)
                    .where(and_(*conditions))
                    .values(is_valid=False)
                )
                result = await session.execute(stmt)
                count = int(getattr(result, "rowcount", 0) or 0)
                logger.info(
                    f"缓存已失效: {company_name}/{data_source or 'all'} "
                    f"org={scope_org_id or 'global'} ({count} 条)"
                )
                return count

        except Exception as e:
            logger.warning(f"缓存失效操作失败: {e}")
            return 0

    # ========== 时间序列快照 ==========

    async def save_snapshot(
        self,
        company_name: str,
        investigation_id: str | None,
        user_id: str | None,
        data: dict[str, Any],
    ) -> str | None:
        """
        保存调查快照 — 记录某一时刻的企业数据状态

        自动与上一快照对比生成差异摘要。
        """
        try:
            from src.core.database import get_db_context
            from src.models.investigation import InvestigationSnapshot

            snapshot_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            risk_data = data.get("risk", {})
            risk_scores = [
                risk_data.get("operation_risk", 0),
                risk_data.get("litigation_risk", 0),
                risk_data.get("credit_risk", 0),
                risk_data.get("compliance_risk", 0),
                risk_data.get("relation_risk", 0),
            ]
            avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
            risk_level = "high" if avg_risk > 60 else "medium" if avg_risk > 35 else "low"

            # 获取上一快照做差异对比
            prev_snapshot = await self._get_latest_snapshot(company_name)
            diff_summary, changes = self._compute_diff(prev_snapshot, data, risk_level)

            async with get_db_context() as session:
                snapshot = InvestigationSnapshot(
                    company_name=company_name,
                    user_id=user_id,
                    investigation_id=investigation_id,
                    snapshot_time=snapshot_time,
                    basic_info=data.get("basic_info"),
                    litigation=data.get("litigation"),
                    credit=data.get("credit"),
                    risk=data.get("risk"),
                    relations=data.get("relations"),
                    risk_score=int(round(avg_risk)),
                    risk_level=risk_level,
                    diff_summary=diff_summary,
                    changes_detected=changes,
                )
                session.add(snapshot)
                await session.flush()
                snap_id = str(snapshot.id)
                logger.info(f"快照已保存: {company_name} @ {snapshot_time} (id={snap_id})")
                return snap_id

        except Exception as e:
            logger.warning(f"快照保存失败: {e}")
            return None

    async def get_snapshots(
        self,
        company_name: str,
        limit: int = 20,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取某企业的历史快照列表（按时间倒序）"""
        try:
            from sqlalchemy import and_, desc, select

            from src.core.database import get_db_context
            from src.models.investigation import InvestigationSnapshot

            async with get_db_context() as session:
                conditions = [InvestigationSnapshot.company_name == company_name]
                if user_id:
                    conditions.append(InvestigationSnapshot.user_id == user_id)

                stmt = (
                    select(InvestigationSnapshot)
                    .where(and_(*conditions))
                    .order_by(desc(InvestigationSnapshot.created_at))
                    .limit(limit)
                )
                result = await session.execute(stmt)
                snapshots = result.scalars().all()
                return [s.to_dict() for s in snapshots]

        except Exception as e:
            logger.debug(f"查询快照失败: {e}")
            return []

    async def get_risk_trend(
        self,
        company_name: str,
        limit: int = 30,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取企业风险趋势数据（用于前端折线图）"""
        try:
            from sqlalchemy import asc, select

            from src.core.database import get_db_context
            from src.models.investigation import InvestigationSnapshot

            async with get_db_context() as session:
                stmt = (
                    select(
                        InvestigationSnapshot.snapshot_time,
                        InvestigationSnapshot.risk_score,
                        InvestigationSnapshot.risk_level,
                        InvestigationSnapshot.changes_detected,
                    )
                    .where(InvestigationSnapshot.company_name == company_name)
                    .order_by(asc(InvestigationSnapshot.created_at))
                    .limit(limit)
                )
                if user_id:
                    stmt = stmt.where(InvestigationSnapshot.user_id == user_id)
                result = await session.execute(stmt)
                rows = result.all()

                return [
                    {
                        "time": row[0],
                        "risk_score": row[1],
                        "risk_level": row[2],
                        "has_changes": bool(row[3]),
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.debug(f"查询风险趋势失败: {e}")
            return []

    async def compare_snapshots(
        self,
        snapshot_id_a: str,
        snapshot_id_b: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """对比两个快照的差异"""
        try:
            from src.core.database import get_db_context
            from src.models.investigation import InvestigationSnapshot

            async with get_db_context() as session:
                snap_a = await session.get(InvestigationSnapshot, snapshot_id_a)
                snap_b = await session.get(InvestigationSnapshot, snapshot_id_b)

                if not snap_a or not snap_b:
                    return {"error": "快照不存在"}
                if user_id and (
                    str(snap_a.user_id) != str(user_id)
                    or str(snap_b.user_id) != str(user_id)
                ):
                    return {"error": "无权访问指定快照"}

                data_a = {
                    "basic_info": snap_a.basic_info or {},
                    "litigation": snap_a.litigation or {},
                    "credit": snap_a.credit or {},
                    "risk": snap_a.risk or {},
                }
                data_b = {
                    "basic_info": snap_b.basic_info or {},
                    "litigation": snap_b.litigation or {},
                    "credit": snap_b.credit or {},
                    "risk": snap_b.risk or {},
                }

                diff_summary, changes = self._compute_diff_between(data_a, data_b)

                return {
                    "snapshot_a": {"id": snapshot_id_a, "time": snap_a.snapshot_time, "risk_score": snap_a.risk_score},
                    "snapshot_b": {"id": snapshot_id_b, "time": snap_b.snapshot_time, "risk_score": snap_b.risk_score},
                    "risk_score_change": (snap_b.risk_score or 0) - (snap_a.risk_score or 0),
                    "diff_summary": diff_summary,
                    "changes": changes,
                }

        except Exception as e:
            logger.debug(f"对比快照失败: {e}")
            return {"error": str(e)}

    # ========== 用户偏好 ==========

    async def update_user_preference(
        self,
        user_id: str,
        company_name: str,
        investigation_type: str = "comprehensive",
        duration_seconds: float | None = None,
        sections_viewed: list[str] | None = None,
        search_keywords: list[str] | None = None,
    ) -> bool:
        """
        更新用户调查偏好 — 每次调查完成后调用

        自动积累：
        - 常调查的企业
        - 常用的调查类型
        - 平均调查耗时
        - 最常查看的报告模块
        - 搜索关键词历史
        """
        try:
            from sqlalchemy import select

            from src.core.database import get_db_context
            from src.models.investigation import UserInvestigationPreference

            async with get_db_context() as session:
                stmt = select(UserInvestigationPreference).where(
                    UserInvestigationPreference.user_id == user_id
                )
                result = await session.execute(stmt)
                pref = result.scalar_one_or_none()

                if not pref:
                    pref = UserInvestigationPreference(user_id=user_id)
                    session.add(pref)

                # 更新调查次数
                pref.total_investigations = (pref.total_investigations or 0) + 1

                # 更新常调查企业 top 20
                favorites = pref.favorite_companies or []
                found = False
                for fav in favorites:
                    if fav.get("name") == company_name:
                        fav["count"] = fav.get("count", 0) + 1
                        fav["last_investigated"] = datetime.now().isoformat()
                        found = True
                        break
                if not found:
                    favorites.append({
                        "name": company_name,
                        "count": 1,
                        "last_investigated": datetime.now().isoformat(),
                    })
                # 按次数排序，保留 top 20
                favorites.sort(key=lambda x: x.get("count", 0), reverse=True)
                pref.favorite_companies = favorites[:20]

                # 更新平均调查耗时
                if duration_seconds is not None:
                    old_avg = pref.avg_investigation_duration or 0
                    old_count = max((pref.total_investigations or 1) - 1, 0)
                    if old_count > 0:
                        pref.avg_investigation_duration = (old_avg * old_count + duration_seconds) / (old_count + 1)
                    else:
                        pref.avg_investigation_duration = duration_seconds

                # 更新最常查看的模块
                if sections_viewed:
                    view_counts = pref.most_viewed_sections or {}
                    for section in sections_viewed:
                        view_counts[section] = view_counts.get(section, 0) + 1
                    pref.most_viewed_sections = view_counts

                # 追加搜索关键词历史（保留最近 100 个）
                if search_keywords:
                    history = pref.search_keywords_history or []
                    for kw in search_keywords:
                        if kw not in history:
                            history.append(kw)
                    pref.search_keywords_history = history[-100:]

                await session.flush()
                logger.debug(f"用户偏好已更新: user={user_id}, investigations={pref.total_investigations}")
                return True

        except Exception as e:
            logger.warning(f"更新用户偏好失败: {e}")
            return False

    async def get_user_preference(self, user_id: str) -> dict[str, Any] | None:
        """获取用户调查偏好"""
        try:
            from sqlalchemy import select

            from src.core.database import get_db_context
            from src.models.investigation import UserInvestigationPreference

            async with get_db_context() as session:
                stmt = select(UserInvestigationPreference).where(
                    UserInvestigationPreference.user_id == user_id
                )
                result = await session.execute(stmt)
                pref = result.scalar_one_or_none()

                if not pref:
                    return None

                return pref.to_dict()

        except Exception as e:
            logger.debug(f"查询用户偏好失败: {e}")
            return None

    async def get_smart_recommendations(
        self, user_id: str, company_name: str | None = None
    ) -> dict[str, Any]:
        """
        基于用户偏好生成智能推荐

        Returns:
            {
                "suggested_depth": "deep",
                "suggested_template": "risk_focus",
                "suggested_dimensions": ["诉讼风险", "信用风险"],
                "related_companies": ["同行业A", "关联企业B"],
                "quick_access": [{"name": "常查企业", "count": 5}],
            }
        """
        try:
            pref = await self.get_user_preference(user_id)
            if not pref:
                return {
                    "suggested_depth": "deep",
                    "suggested_template": "comprehensive",
                    "suggested_dimensions": [],
                    "quick_access": [],
                }

            # 根据偏好推荐调查深度
            total = pref.get("total_investigations", 0)
            suggested_depth = pref.get("preferred_depth", "deep")

            # 根据风险关注度推荐模板
            risk_weights = pref.get("risk_focus_weights", {})
            if risk_weights:
                max_risk = max(risk_weights, key=risk_weights.get, default="")
                if "litigation" in max_risk:
                    suggested_template = "litigation"
                elif "credit" in max_risk:
                    suggested_template = "credit"
                elif "compliance" in max_risk:
                    suggested_template = "compliance"
                else:
                    suggested_template = pref.get("preferred_report_template", "comprehensive")
            else:
                suggested_template = pref.get("preferred_report_template", "comprehensive")

            # 推荐调查维度
            most_viewed = pref.get("most_viewed_sections", {})
            dimension_map = {
                "risk": "风险评估",
                "litigation": "诉讼分析",
                "credit": "信用合规",
                "graph": "关系图谱",
                "sentiment": "舆情监控",
            }
            suggested_dims = []
            for section, _count in sorted(most_viewed.items(), key=lambda x: -x[1]):
                if section in dimension_map:
                    suggested_dims.append(dimension_map[section])
                if len(suggested_dims) >= 3:
                    break

            # 快捷访问企业
            quick_access = pref.get("favorite_companies", [])[:5]

            return {
                "suggested_depth": suggested_depth,
                "suggested_template": suggested_template,
                "suggested_dimensions": suggested_dims,
                "quick_access": quick_access,
                "total_investigations": total,
                "search_keywords": (pref.get("search_keywords_history") or [])[-10:],
            }

        except Exception as e:
            logger.debug(f"生成推荐失败: {e}")
            return {"suggested_depth": "deep", "suggested_template": "comprehensive"}

    # ========== 内部方法 ==========

    def _normalize_org_id(self, org_id: str | None) -> str | None:
        """Normalize organization scope values before cache queries."""
        if org_id is None:
            return None
        normalized = str(org_id).strip()
        return normalized or None

    def _org_scope_condition(self, cache_model: Any, org_id: str | None) -> Any:
        """Build the organization-scope filter used by every cache operation."""
        if org_id:
            return cache_model.org_id == org_id
        return cache_model.org_id.is_(None)

    def _make_cache_key(self, company_name: str, data_source: str, query_text: str = "") -> str:
        """生成缓存 key"""
        raw = f"{company_name}|{data_source}|{query_text}"
        return hashlib.md5(raw.encode()).hexdigest()

    async def _get_latest_snapshot(self, company_name: str) -> dict[str, Any] | None:
        """获取最新一个快照的数据"""
        try:
            from sqlalchemy import desc, select

            from src.core.database import get_db_context
            from src.models.investigation import InvestigationSnapshot

            async with get_db_context() as session:
                stmt = (
                    select(InvestigationSnapshot)
                    .where(InvestigationSnapshot.company_name == company_name)
                    .order_by(desc(InvestigationSnapshot.created_at))
                    .limit(1)
                )
                result = await session.execute(stmt)
                snap = result.scalar_one_or_none()

                if snap:
                    return {
                        "basic_info": snap.basic_info or {},
                        "litigation": snap.litigation or {},
                        "credit": snap.credit or {},
                        "risk": snap.risk or {},
                        "risk_score": snap.risk_score,
                        "risk_level": snap.risk_level,
                    }
        except Exception:
            pass
        return None

    def _compute_diff(
        self,
        prev: dict[str, Any] | None,
        current_data: dict[str, Any],
        current_risk_level: str,
    ) -> tuple[str, dict[str, Any]]:
        """计算当前数据与上一快照的差异"""
        if not prev:
            return "首次快照，无对比数据", {}

        return self._compute_diff_between(prev, current_data)

    def _compute_diff_between(
        self,
        data_a: dict[str, Any],
        data_b: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """对比两份数据的差异"""
        changes: dict[str, Any] = {}
        summary_parts: list[str] = []

        # 对比风险评分
        risk_a = data_a.get("risk", {})
        risk_b = data_b.get("risk", {})
        risk_dimensions = [
            ("operation_risk", "经营风险"),
            ("litigation_risk", "诉讼风险"),
            ("credit_risk", "信用风险"),
            ("compliance_risk", "合规风险"),
            ("relation_risk", "关联风险"),
        ]
        for key, label in risk_dimensions:
            old_val = risk_a.get(key, 0)
            new_val = risk_b.get(key, 0)
            if old_val != new_val:
                delta = new_val - old_val
                direction = "上升" if delta > 0 else "下降"
                changes[key] = {"old": old_val, "new": new_val, "delta": delta}
                if abs(delta) >= 10:
                    summary_parts.append(f"{label}{direction} {abs(delta)} 分")

        # 对比诉讼数据
        lit_a = data_a.get("litigation", {})
        lit_b = data_b.get("litigation", {})
        for key, label in [
            ("plaintiff_cases", "原告案件"),
            ("defendant_cases", "被告案件"),
            ("execution_cases", "执行案件"),
        ]:
            old_val = int(lit_a.get(key, 0))
            new_val = int(lit_b.get(key, 0))
            if old_val != new_val:
                delta = new_val - old_val
                direction = "增加" if delta > 0 else "减少"
                changes[f"litigation.{key}"] = {"old": old_val, "new": new_val, "delta": delta}
                if abs(delta) >= 1:
                    summary_parts.append(f"{label}{direction} {abs(delta)} 件")

        # 对比信用评级
        credit_a = data_a.get("credit", {})
        credit_b = data_b.get("credit", {})
        old_rating = credit_a.get("credit_rating", "")
        new_rating = credit_b.get("credit_rating", "")
        if old_rating and new_rating and old_rating != new_rating:
            changes["credit_rating"] = {"old": old_rating, "new": new_rating}
            summary_parts.append(f"信用评级从 {old_rating} 变为 {new_rating}")

        # 对比经营状态
        basic_a = data_a.get("basic_info", {})
        basic_b = data_b.get("basic_info", {})
        old_status = basic_a.get("status", "")
        new_status = basic_b.get("status", "")
        if old_status and new_status and old_status != new_status:
            changes["business_status"] = {"old": old_status, "new": new_status}
            summary_parts.append(f"经营状态从「{old_status}」变为「{new_status}」")

        summary = "；".join(summary_parts) if summary_parts else "无显著变化"
        return summary, changes


# 全局实例
investigation_data_store = InvestigationDataStore()
