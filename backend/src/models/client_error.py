"""三端客户端错误 / Web Vitals / 性能事件聚合模型。

由 `src.api.routes.client_errors._try_persist` 写入，best-effort 持久化。
表会在 backend 启动时由 ``Base.metadata.create_all`` 自动创建（dev）。
生产环境若需保留 schema 演进追溯，可后续补 Alembic 迁移。

[S9 fix 2026-05-22]: 之前缺失此 model 导致每次前端上报都报
`No module named 'src.models.client_error'`（仅 debug log，不阻塞功能）。
"""

from __future__ import annotations

from typing import Any

# 与 ai_assistant.py / case.py 等保持一致：用通用 JSON 别名为 JSONB，
# 兼容 SQLite（测试内存库）与 PostgreSQL。该表由 create_all 自动建、无 Alembic
# 迁移，故改类型零迁移风险。原 `dialects.postgresql.JSONB` 在 SQLite 上无法编译，
# 会导致所有建 `client_errors` 表的测试在 setup 阶段报 visit_JSONB 错误。
from sqlalchemy import JSON as JSONB
from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class ClientError(Base, TimestampMixin):
    """三端（Web/Desktop/Mobile/MiniProgram）错误与性能事件聚合表。"""

    __tablename__ = "client_errors"

    # source: 上报方（如 'web' / 'desktop' / 'mobile' / 'mini-program'）
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="web")

    # error_type: 错误类型分类（'js-error' / 'web-vital' / 'unhandled-promise' / 'api-error' 等）
    error_type: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")

    # message: 主要错误消息（已截断 500 字）
    message: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    # stack: 堆栈（已截断 4000 字）
    stack: Mapped[str | None] = mapped_column(Text, nullable=True)

    # url: 上报时的页面 URL
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # context: 附加上下文（user_id / build_id / web-vital 指标值等）
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # fingerprint_hash: 用于去重 / 聚合的指纹哈希
    fingerprint_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    __table_args__ = (
        Index("ix_client_errors_source", "source"),
        Index("ix_client_errors_error_type", "error_type"),
        Index("ix_client_errors_fingerprint", "fingerprint_hash"),
        Index("ix_client_errors_created_at", "created_at"),
    )
