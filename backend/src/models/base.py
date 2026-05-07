"""
???????
"""

import enum as _enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, DateTime, TypeDecorator, func
from sqlalchemy import Enum as _SAEnum
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def value_enum(enum_cls: type[_enum.Enum], **kwargs: Any) -> Any:
    """
    统一的 Enum 列类型 — 使用 enum.value（小写）而非 enum.name（大写）写入 DB，
    与 PostgreSQL 已创建的小写枚举类型匹配。
    """
    kwargs.setdefault("values_callable", lambda x: [e.value for e in x])
    return _SAEnum(enum_cls, **kwargs)


ValueEnum = value_enum  # noqa: N816


class GUID(TypeDecorator[str]):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as string.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(postgresql.UUID(as_uuid=False))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)


class Base(DeclarativeBase):
    """SQLAlchemy ??"""

    id: Mapped[str] = mapped_column(
        GUID(),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    def to_dict(self) -> dict[str, Any]:
        """?????"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class TimestampMixin:
    """??????"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
