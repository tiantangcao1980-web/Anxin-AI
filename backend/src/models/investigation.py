"""
调查持久化模型 — Investigation Model (v3)

支持：
- 调查主记录
- 时间序列快照（不同时期抓取对比）
- 搜索缓存（热加载）
- 用户偏好（越用越聪明）
"""

import enum
from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import GUID, Base, TimestampMixin


class InvestigationStatus(str, enum.Enum):
    """调查状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class InvestigationRiskLevel(str, enum.Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class Investigation(Base, TimestampMixin):
    """尽职调查记录"""
    __tablename__ = "investigations"

    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    investigation_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="comprehensive"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InvestigationStatus.PENDING.value,
    )
    user_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # 调查结果 (JSON)
    basic_info: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    litigation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    credit: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    risk: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    relations: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # 综合报告
    report_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InvestigationRiskLevel.UNKNOWN.value,
    )
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Agent 协同元数据
    agent_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    consensus_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    conflicts: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)

    # v2: 深度研究 & 论坛数据
    research_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    forum_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    stages_completed: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["created_at"] = str(d.get("created_at", ""))
        d["updated_at"] = str(d.get("updated_at", ""))
        return d


# ===== 时间序列快照 — 不同时期抓取的调查数据 =====

class InvestigationSnapshot(Base, TimestampMixin):
    """
    调查快照 — 同一企业在不同时间点的数据快照

    用途：
    - 跟踪被调查目标在不同时期的经营/运营变化
    - 对比不同时间点的风险等级变化趋势
    - 发现异常变动（如突然增加诉讼、信用评级下调等）
    """
    __tablename__ = "investigation_snapshots"
    __table_args__ = (
        Index("ix_snapshot_company_time", "company_name", "snapshot_time"),
        Index("ix_snapshot_user", "user_id"),
    )

    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    investigation_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("investigations.id", ondelete="SET NULL"), nullable=True
    )

    # 快照时间标记（便于排序对比）
    snapshot_time: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # 核心数据快照
    basic_info: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    litigation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    credit: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    risk: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    relations: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # 风险指标快照（方便快速查询趋势）
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 与上一快照的差异摘要
    diff_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    changes_detected: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["created_at"] = str(d.get("created_at", ""))
        d["updated_at"] = str(d.get("updated_at", ""))
        return d


# ===== 搜索缓存 — 热加载，避免重复抓取 =====

class SearchCache(Base, TimestampMixin):
    """
    搜索缓存 — 缓存每次搜索的原始结果

    用途：
    - 热加载：对同一企业的后续调查可直接使用缓存数据，减少等待
    - 增量更新：仅抓取缓存过期或缺失的数据维度
    - 离线模式：本地绝密模式下可完全基于缓存工作
    """
    __tablename__ = "search_cache"
    __table_args__ = (
        Index("ix_cache_key_source", "cache_key", "data_source"),
        Index("ix_cache_company", "company_name"),
        Index("ix_cache_org_key_source", "org_id", "cache_key", "data_source"),
        Index("ix_cache_org_company", "org_id", "company_name"),
    )

    # 缓存键（company_name + data_source + query_hash）
    cache_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    org_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_source: Mapped[str] = mapped_column(String(50), nullable=False)  # web_search / knowledge_base / business_registry / llm_analysis
    query_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 缓存数据
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    parsed_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, default=0)

    # 缓存控制
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=86400)  # 默认 24h
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["created_at"] = str(d.get("created_at", ""))
        d["updated_at"] = str(d.get("updated_at", ""))
        return d


# ===== 用户偏好 — 越用越聪明 =====

class UserInvestigationPreference(Base, TimestampMixin):
    """
    用户调查偏好 — 积累用户习惯，智能推荐

    用途：
    - 记录用户常调查的行业、区域、风险关注点
    - 自动推荐调查维度和报告模板
    - 个性化默认参数（深度搜索轮数、论坛是否开启等）
    - 常用企业快捷访问
    """
    __tablename__ = "user_investigation_preferences"
    __table_args__ = (
        Index("ix_user_pref_user", "user_id", unique=True),
    )

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # 调查偏好统计
    total_investigations: Mapped[int] = mapped_column(Integer, default=0)
    favorite_companies: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)  # [{name, count, last_investigated}]
    frequent_industries: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)  # [{industry, count}]
    frequent_regions: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)  # [{region, count}]

    # 风险关注偏好（哪些维度用户更关注）
    risk_focus_weights: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 例: {"litigation_risk": 0.9, "credit_risk": 0.8, "operation_risk": 0.5}

    # 调查参数偏好
    preferred_depth: Mapped[str] = mapped_column(String(20), default="deep")  # basic / deep / ultra
    preferred_report_template: Mapped[str] = mapped_column(String(50), default="comprehensive")
    enable_deep_research: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_forum: Mapped[bool] = mapped_column(Boolean, default=True)
    max_search_rounds: Mapped[int] = mapped_column(Integer, default=3)

    # 用户行为画像
    avg_investigation_duration: Mapped[float | None] = mapped_column(Float, nullable=True)  # 平均每次调查耗时（秒）
    most_viewed_sections: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # 最常查看的模块
    custom_dimensions: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)  # 用户自定义的调查维度

    # 搜索历史关键词（用于智能补全）
    search_keywords_history: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["created_at"] = str(d.get("created_at", ""))
        d["updated_at"] = str(d.get("updated_at", ""))
        return d
