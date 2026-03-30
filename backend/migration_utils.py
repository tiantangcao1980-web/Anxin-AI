"""Alembic 迁移辅助函数。

目标：
- 让开发库在表/列已由 create_all 创建的情况下，历史迁移仍能安全前进
- 避免重复建表、重复建索引、重复加列导致的迁移中断
"""

from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy as sa
from alembic import op


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def table_exists(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    if not table_exists(table_name):
        return False
    columns = _inspector().get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def index_exists(table_name: str, index_name: str) -> bool:
    if not table_exists(table_name):
        return False
    indexes = _inspector().get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def unique_constraint_exists(table_name: str, constraint_name: str) -> bool:
    if not table_exists(table_name):
        return False
    constraints = _inspector().get_unique_constraints(table_name)
    return any(constraint["name"] == constraint_name for constraint in constraints)


def safe_add_column(table_name: str, column: sa.Column) -> None:
    if not column_exists(table_name, column.name):
        op.add_column(table_name, column)


def safe_create_table(table_name: str, *columns: sa.SchemaItem, **kwargs) -> None:
    if not table_exists(table_name):
        op.create_table(table_name, *columns, **kwargs)


def safe_create_index(
    index_name: str,
    table_name: str,
    columns: Iterable[str],
    *,
    unique: bool = False,
) -> None:
    if not index_exists(table_name, index_name):
        op.create_index(index_name, table_name, list(columns), unique=unique)


def safe_create_unique_constraint(
    constraint_name: str,
    table_name: str,
    columns: Iterable[str],
) -> None:
    if not unique_constraint_exists(table_name, constraint_name):
        op.create_unique_constraint(constraint_name, table_name, list(columns))
