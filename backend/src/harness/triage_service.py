# -*- coding: utf-8 -*-
"""
CREAO 自愈闭环 Slice 2 — Triage Service

输入: incidents 表里 status="open" 的记录
输出:
  - 每条 incident 的 triage_summary (人读总结)
  - 聚类: 同 (source, agent_name, route) tuple 归并展示
  - 趋势: 24h / 1h 出现次数对比, 标记上升 / 下降 / 平稳
  - state transition: open → triaged

设计:
  - 当前 Slice 2 全部是确定性逻辑 (无 LLM 调用), 保证幂等 + 可单测
  - LLM 总结 + 智能根因分析放到 Slice 2.5 (可选, 看 GitHub Issue 化 ROI)
  - Slice 3 (Builder + 人工 gate) 消费这里输出的聚类与 trace_id 关联做回归测试草稿
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.incident import Incident


@dataclass
class IncidentCluster:
    """同类 incident 聚合视图。"""

    source: str
    agent_name: str | None
    route: str | None
    severity_max: str  # P0/P1/P2/P3 — 取 cluster 内最严重
    incident_ids: list[str] = field(default_factory=list)
    fingerprints: list[str] = field(default_factory=list)
    total_occurrences: int = 0  # cluster 内全部 occurrence_count 之和
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    trend_24h: int = 0  # 过去 24h 出现次数
    trend_1h: int = 0   # 过去 1h 出现次数

    @property
    def trend_label(self) -> str:
        """简易趋势标签。"""
        # 24h 内 0 次视为已平息
        if self.trend_24h == 0:
            return "quiet"
        # 1h 出现频率超过 24h 平均频率 1.5 倍 → 上升
        hourly_avg = self.trend_24h / 24.0
        if hourly_avg <= 0:
            return "stable"
        ratio = self.trend_1h / hourly_avg
        if ratio >= 1.5:
            return "surging"
        if ratio <= 0.3:
            return "decaying"
        return "stable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "agent_name": self.agent_name,
            "route": self.route,
            "severity_max": self.severity_max,
            "incident_count": len(self.incident_ids),
            "incident_ids": list(self.incident_ids),
            "total_occurrences": self.total_occurrences,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "trend_24h": self.trend_24h,
            "trend_1h": self.trend_1h,
            "trend_label": self.trend_label,
        }


SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _max_severity(left: str, right: str) -> str:
    """返回 P0/P1/P2/P3 中较严重的那个 (P0 最严重)。"""
    if SEVERITY_RANK.get(left, 9) <= SEVERITY_RANK.get(right, 9):
        return left
    return right


def _format_triage_summary(cluster: IncidentCluster) -> str:
    """生成人读总结字符串。"""
    trend_zh = {
        "surging": "近 1h 频次升高",
        "decaying": "近 1h 频次下降",
        "stable": "频次稳定",
        "quiet": "近 24h 未再出现",
    }.get(cluster.trend_label, cluster.trend_label)
    parts = [
        f"[{cluster.severity_max}] {cluster.source}",
    ]
    if cluster.agent_name:
        parts.append(f"agent={cluster.agent_name}")
    if cluster.route:
        parts.append(f"route={cluster.route}")
    parts.append(
        f"聚合 {len(cluster.incident_ids)} 条记录, 累计 {cluster.total_occurrences} 次, {trend_zh}"
    )
    return " | ".join(parts)


async def triage_open_incidents(
    db: AsyncSession,
    *,
    limit: int = 200,
    transition_state: bool = True,
) -> dict[str, Any]:
    """处理 open 状态的 incidents, 生成 cluster 与 triage_summary。

    Args:
        db: AsyncSession
        limit: 单次处理上限 (按 last_seen_at desc 取最近的)
        transition_state: True 时将处理过的 incident status 改为 "triaged" 并填 triage_summary;
            False 时仅返回 cluster 视图, 不写库 (供 admin dry-run 调用)

    Returns:
        {
            "scanned": int,           # 扫描的 incident 数量
            "clusters": [IncidentCluster.to_dict()],
            "transitioned": int,      # 实际 transition 数量
            "generated_at": iso datetime,
        }
    """
    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_1h = now - timedelta(hours=1)

    # 取最近 open 的 incidents (按 last_seen_at desc)
    result = await db.execute(
        select(Incident)
        .where(Incident.status == "open")
        .order_by(Incident.last_seen_at.desc())
        .limit(limit)
    )
    open_incidents = list(result.scalars())

    if not open_incidents:
        return {
            "scanned": 0,
            "clusters": [],
            "transitioned": 0,
            "generated_at": now.isoformat(),
        }

    # 按 (source, agent_name, route) 聚类
    cluster_map: dict[tuple[str, str | None, str | None], IncidentCluster] = {}
    for inc in open_incidents:
        key = (inc.source, inc.agent_name, inc.route)
        c = cluster_map.get(key)
        if c is None:
            c = IncidentCluster(
                source=inc.source,
                agent_name=inc.agent_name,
                route=inc.route,
                severity_max=inc.severity,
                first_seen_at=inc.first_seen_at,
                last_seen_at=inc.last_seen_at,
            )
            cluster_map[key] = c

        c.incident_ids.append(str(inc.id))
        c.fingerprints.append(inc.fingerprint)
        c.total_occurrences += inc.occurrence_count or 1
        c.severity_max = _max_severity(c.severity_max, inc.severity)
        if inc.first_seen_at and (c.first_seen_at is None or inc.first_seen_at < c.first_seen_at):
            c.first_seen_at = inc.first_seen_at
        if inc.last_seen_at and (c.last_seen_at is None or inc.last_seen_at > c.last_seen_at):
            c.last_seen_at = inc.last_seen_at

        # 趋势计数: 用 last_seen_at 落在窗口内时计 occurrence_count
        if inc.last_seen_at:
            # 兼容 naive datetime (SQLite 测试场景)
            last_seen = inc.last_seen_at
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            if last_seen >= cutoff_24h:
                c.trend_24h += inc.occurrence_count or 1
            if last_seen >= cutoff_1h:
                c.trend_1h += inc.occurrence_count or 1

    # 状态机推进 + 写 triage_summary
    transitioned = 0
    if transition_state:
        for inc in open_incidents:
            key = (inc.source, inc.agent_name, inc.route)
            cluster = cluster_map[key]
            inc.triage_summary = _format_triage_summary(cluster)
            inc.status = "triaged"
            transitioned += 1
        await db.flush()

    # 输出按 severity → total_occurrences desc 排序
    clusters_sorted = sorted(
        cluster_map.values(),
        key=lambda c: (SEVERITY_RANK.get(c.severity_max, 9), -c.total_occurrences),
    )

    logger.info(
        f"[Triage] scanned={len(open_incidents)} clusters={len(clusters_sorted)} "
        f"transitioned={transitioned}"
    )
    return {
        "scanned": len(open_incidents),
        "clusters": [c.to_dict() for c in clusters_sorted],
        "transitioned": transitioned,
        "generated_at": now.isoformat(),
    }


async def get_triage_overview(db: AsyncSession) -> dict[str, Any]:
    """提供给 admin 监控面板的全局视图: 总数 / 按状态 / 按 severity / 最近趋势。"""

    counts_by_status = (await db.execute(
        select(Incident.status, func.count()).group_by(Incident.status)
    )).all()
    counts_by_severity = (await db.execute(
        select(Incident.severity, func.count()).group_by(Incident.severity)
    )).all()
    counts_by_source = (await db.execute(
        select(Incident.source, func.count()).group_by(Incident.source)
    )).all()

    return {
        "by_status": {row[0]: row[1] for row in counts_by_status},
        "by_severity": {row[0]: row[1] for row in counts_by_severity},
        "by_source": {row[0]: row[1] for row in counts_by_source},
    }
