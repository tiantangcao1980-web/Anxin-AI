# -*- coding: utf-8 -*-
"""
UserTokenUsage 模型 — A4 (2026-05-14)

cost_tracker 进程内内存累计的持久化层. 关键字段:
  - (user_id, period_start, period_end) 标识一个计费周期
  - archived=False 表示当前活跃周期 (正在累计)
  - archived=True 表示已结束的周期 (历史归档, 可用作账单导出)

启动时只 restore archived=False 的行到内存; 周期切换 cron 把
archived=True 行落库后清零内存。
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class UserTokenUsage(Base):
    """用户级 token 用量持久化记录。"""

    __tablename__ = "user_token_usage"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("0")
    )
    call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<UserTokenUsage user_id={self.user_id} period={self.period_start}~{self.period_end} "
            f"tokens={self.tokens_used} archived={self.archived}>"
        )
