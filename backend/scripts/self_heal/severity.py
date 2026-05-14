# -*- coding: utf-8 -*-
"""
自愈闭环 - 严重度评分（O2）

把 T1 cluster 元数据 + 业务面权重折成 0-1 分，并映射到 4 级。
纯函数：无副作用，便于单测与回放。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# 命中 chat / contract / dd 等核心面 → 业务面权重提升
_CORE_ROUTES = {
    "chat", "contract", "due_diligence", "research", "risk",
    "compliance", "esign",
}
# 进入这些路由的 cluster 永远提级到 CRITICAL（且禁自愈）
_FORBID_AUTO_HEAL_ROUTES = {
    "auth", "payment", "billing", "refund", "esign",
    "mode_switch", "alembic_migration",
}


@dataclass
class ClusterSignal:
    cluster_id: str
    occurrence_per_hour: float
    affected_users: int
    routes: list[str]               # 该 cluster 涉及的 routes 集合
    error_class: str                # llm | db | network | logic
    business_critical: bool = False  # 由 cluster_signature 中是否含敏感关键字决定


def _norm(value: float, scale: float) -> float:
    return min(max(value / scale, 0.0), 1.0)


def score_cluster(sig: ClusterSignal) -> tuple[float, dict]:
    """返回 (score, breakdown)；score ∈ [0, 1]"""
    occ = _norm(sig.occurrence_per_hour, 100)         # 100/h → 满分
    users = _norm(sig.affected_users, 50)             # 50 用户 → 满分
    surface = 1.0 if any(r in _CORE_ROUTES for r in sig.routes) else 0.4
    error_w = {"llm": 0.7, "db": 0.9, "network": 0.5, "logic": 0.6}.get(sig.error_class, 0.5)

    score = round(0.30 * occ + 0.30 * users + 0.20 * surface + 0.20 * error_w, 3)
    return score, {
        "occurrence_norm": occ,
        "affected_users_norm": users,
        "business_surface": surface,
        "error_class_weight": error_w,
    }


def to_severity(score: float, sig: ClusterSignal) -> Severity:
    if any(r in _FORBID_AUTO_HEAL_ROUTES for r in sig.routes) or sig.business_critical:
        return Severity.CRITICAL
    if score > 0.8:
        return Severity.CRITICAL
    if score > 0.5:
        return Severity.HIGH
    if score > 0.2:
        return Severity.MEDIUM
    return Severity.LOW


def is_auto_heal_allowed(sig: ClusterSignal) -> bool:
    """禁列在 _FORBID_AUTO_HEAL_ROUTES 的永远不自愈"""
    return not any(r in _FORBID_AUTO_HEAL_ROUTES for r in sig.routes) and not sig.business_critical
