# -*- coding: utf-8 -*-
"""已落库历史裁判文书的 read-only 查询服务。

合规设计：
- 不再向 wenshu.court.gov.cn 发起任何请求（合规护栏会硬拒）
- 仅以 raw SQL 读取本地表（默认表名 ``wenshu_historical``，可通过 ``table_name`` 注入覆盖）
- 不修改 ORM model，避免污染 P6-A FetchService 的迁移体系

约定表结构（最小列；多余列允许）::

    case_id          TEXT PRIMARY KEY
    title            TEXT NOT NULL
    court_name       TEXT
    court_level      TEXT     -- 最高/高级/中级/基层
    case_type        TEXT
    judgment_year    INTEGER
    judgment_date    DATE
    summary          TEXT
    full_text        TEXT
"""

from __future__ import annotations

import logging
from datetime import date
from typing import ClassVar, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection

from .base import (
    BaseLegalSource,
    ComplianceError,
    LawSearchQuery,
    LawSearchResult,
    LawStatus,
    LawType,
    assert_url_compliant,
)

logger = logging.getLogger(__name__)


# 允许的表名字符集（白名单），杜绝 SQL 注入
import re as _re
_SAFE_TABLE_NAME = _re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


class HistoricalWenshuSource(BaseLegalSource):
    """已落库 33102 条裁判文书 read-only 查询。"""

    source_id: ClassVar[str] = "historical_wenshu"
    display_name: ClassVar[str] = "历史裁判文书库（已落库）"
    requires_credentials: ClassVar[bool] = False
    base_host: ClassVar[str] = ""  # 不走 HTTP

    DEFAULT_TABLE: ClassVar[str] = "wenshu_historical"

    def __init__(
        self,
        engine: AsyncEngine | Engine,
        table_name: str = DEFAULT_TABLE,
    ) -> None:
        if not _SAFE_TABLE_NAME.match(table_name):
            raise ValueError(f"非法表名: {table_name!r}")
        self._engine = engine
        self._table = table_name
        self._is_async = isinstance(engine, AsyncEngine)

    # ---- BaseLegalSource ----

    async def search(self, query: LawSearchQuery) -> list[LawSearchResult]:
        """关键词检索。

        - keyword 在 title / summary / full_text 上做 LIKE 模糊匹配
        - jurisdiction 映射到 court_level
        - date_from/date_to 映射到 judgment_date
        """
        # 合规：尽管不走 HTTP，仍兜底防御性校验避免上游错误调用
        if "wenshu.court.gov.cn" in (query.jurisdiction or ""):
            raise ComplianceError(
                "historical_wenshu: 拒绝任何指向 wenshu.court.gov.cn 的请求；本服务为 read-only 已落库查询。"
            )

        sql = (
            f"SELECT case_id, title, court_name, court_level, case_type, "
            f"       judgment_year, judgment_date, summary "
            f"FROM {self._table} "
            f"WHERE (title LIKE :kw OR summary LIKE :kw OR full_text LIKE :kw) "
        )
        params: dict = {"kw": f"%{query.keyword}%"}

        if query.jurisdiction:
            sql += "AND court_level = :court_level "
            params["court_level"] = query.jurisdiction
        if query.date_from is not None:
            sql += "AND judgment_date >= :date_from "
            params["date_from"] = query.date_from
        if query.date_to is not None:
            sql += "AND judgment_date <= :date_to "
            params["date_to"] = query.date_to

        sql += "ORDER BY judgment_date DESC LIMIT :limit OFFSET :offset"
        params["limit"] = query.limit
        params["offset"] = query.offset

        rows = await self._fetch_all(text(sql), params)
        return [self._row_to_result(row) for row in rows]

    async def get_full_text(self, law_id: str) -> str:
        """按 case_id 取全文。"""
        if not law_id:
            raise ValueError("case_id 不能为空")
        sql = text(f"SELECT full_text FROM {self._table} WHERE case_id = :cid LIMIT 1")
        rows = await self._fetch_all(sql, {"cid": law_id})
        if not rows:
            return ""
        return str(rows[0][0] or "")

    async def health_check(self) -> bool:
        try:
            sql = text(f"SELECT 1 FROM {self._table} LIMIT 1")
            await self._fetch_all(sql, {})
            return True
        except SQLAlchemyError as exc:
            logger.warning("historical_wenshu.health_check failed: %s", exc)
            return False

    # ---- 工具：附加便利接口（任务文档约定的签名）----

    async def search_by_filters(
        self,
        keyword: str,
        court_level: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 20,
    ) -> list[LawSearchResult]:
        """便利方法：search(keyword, court_level, year)。"""
        sql = (
            f"SELECT case_id, title, court_name, court_level, case_type, "
            f"       judgment_year, judgment_date, summary "
            f"FROM {self._table} "
            f"WHERE (title LIKE :kw OR summary LIKE :kw OR full_text LIKE :kw) "
        )
        params: dict = {"kw": f"%{keyword}%"}
        if court_level:
            sql += "AND court_level = :court_level "
            params["court_level"] = court_level
        if year is not None:
            sql += "AND judgment_year = :year "
            params["year"] = year
        sql += "ORDER BY judgment_date DESC LIMIT :limit"
        params["limit"] = limit

        rows = await self._fetch_all(text(sql), params)
        return [self._row_to_result(row) for row in rows]

    # ---- 内部 ----

    async def _fetch_all(self, sql, params: dict) -> list[tuple]:
        if self._is_async:
            async with self._engine.connect() as conn:  # type: ignore[union-attr]
                result = await conn.execute(sql, params)
                return list(result.fetchall())
        # 同步引擎：直接 run_in_executor 执行
        import asyncio

        def _run() -> list[tuple]:
            with self._engine.connect() as conn:  # type: ignore[union-attr]
                return list(conn.execute(sql, params).fetchall())

        return await asyncio.get_event_loop().run_in_executor(None, _run)

    def _row_to_result(self, row: tuple) -> LawSearchResult:
        (
            case_id,
            title,
            court_name,
            court_level,
            case_type,
            judgment_year,
            judgment_date,
            summary,
        ) = row
        # judgment_date 在 sqlite 里可能是 str
        jd: Optional[date] = None
        if isinstance(judgment_date, date):
            jd = judgment_date
        elif judgment_date:
            try:
                from datetime import datetime as _dt

                jd = _dt.fromisoformat(str(judgment_date)).date()
            except ValueError:
                jd = None

        return LawSearchResult(
            source=self.source_id,
            law_id=str(case_id),
            title=str(title),
            law_type=LawType.CASE.value,
            issuing_authority=str(court_name or ""),
            issued_date=jd,
            effective_date=jd,
            status=LawStatus.ACTIVE.value,
            full_text_url="",  # 内部库无外链；调用方按 case_id 反查全文
            summary=str(summary or "") or None,
            extra={
                "court_level": court_level,
                "case_type": case_type,
                "judgment_year": judgment_year,
            },
        )


__all__ = ["HistoricalWenshuSource"]
