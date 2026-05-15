"""P6-C 历史裁判文书 read-only 查询测试（内存 SQLite + 假数据）。"""

from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.services.fetch.sources.legal import (
    HistoricalWenshuSource,
    LawSearchQuery,
)


@pytest_asyncio.fixture
async def wenshu_engine() -> AsyncEngine:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
    )
    async with engine.begin() as conn:
        await conn.execute(text("""
                CREATE TABLE wenshu_historical (
                    case_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    court_name TEXT,
                    court_level TEXT,
                    case_type TEXT,
                    judgment_year INTEGER,
                    judgment_date TEXT,
                    summary TEXT,
                    full_text TEXT
                )
                """))
        await conn.execute(text("""
                INSERT INTO wenshu_historical VALUES
                ('CASE-001', '张三与李四民间借贷纠纷', '北京高院', '高级', '民事', 2023, '2023-06-15',
                 '借贷本金 50 万元', '本院认为：原告主张……'),
                ('CASE-002', '某公司与王五合同纠纷', '上海一中院', '中级', '民事', 2024, '2024-03-20',
                 '合同效力争议', '本院认为：合同条款……'),
                ('CASE-003', '赵六交通肇事案', '杭州西湖法院', '基层', '刑事', 2022, '2022-11-10',
                 '醉酒驾驶机动车', '本院认为：被告人……')
                """))
    yield engine
    await engine.dispose()


class TestHistoricalWenshuSearch:
    @pytest.mark.asyncio
    async def test_search_by_keyword(self, wenshu_engine: AsyncEngine) -> None:
        src = HistoricalWenshuSource(engine=wenshu_engine)
        results = await src.search(LawSearchQuery(keyword="合同"))
        assert len(results) == 1
        assert results[0].law_id == "CASE-002"
        assert results[0].title.startswith("某公司")
        assert results[0].source == "historical_wenshu"
        assert results[0].extra["court_level"] == "中级"
        assert results[0].extra["judgment_year"] == 2024

    @pytest.mark.asyncio
    async def test_search_filters_court_level(self, wenshu_engine: AsyncEngine) -> None:
        src = HistoricalWenshuSource(engine=wenshu_engine)
        results = await src.search(LawSearchQuery(keyword="本院", jurisdiction="基层"))
        assert len(results) == 1
        assert results[0].law_id == "CASE-003"

    @pytest.mark.asyncio
    async def test_search_filters_date_range(self, wenshu_engine: AsyncEngine) -> None:
        src = HistoricalWenshuSource(engine=wenshu_engine)
        results = await src.search(
            LawSearchQuery(
                keyword="本院",
                date_from=date(2023, 1, 1),
                date_to=date(2024, 12, 31),
            )
        )
        ids = {r.law_id for r in results}
        assert ids == {"CASE-001", "CASE-002"}

    @pytest.mark.asyncio
    async def test_get_full_text(self, wenshu_engine: AsyncEngine) -> None:
        src = HistoricalWenshuSource(engine=wenshu_engine)
        body = await src.get_full_text("CASE-001")
        assert "原告" in body

    @pytest.mark.asyncio
    async def test_get_full_text_unknown_returns_empty(self, wenshu_engine: AsyncEngine) -> None:
        src = HistoricalWenshuSource(engine=wenshu_engine)
        body = await src.get_full_text("NOT-EXIST")
        assert body == ""

    @pytest.mark.asyncio
    async def test_search_by_filters_helper(self, wenshu_engine: AsyncEngine) -> None:
        src = HistoricalWenshuSource(engine=wenshu_engine)
        results = await src.search_by_filters(keyword="本院", court_level="高级", year=2023)
        assert len(results) == 1
        assert results[0].law_id == "CASE-001"

    @pytest.mark.asyncio
    async def test_health_check(self, wenshu_engine: AsyncEngine) -> None:
        src = HistoricalWenshuSource(engine=wenshu_engine)
        assert await src.health_check() is True

    def test_invalid_table_name_rejected(self, wenshu_engine: AsyncEngine) -> None:
        with pytest.raises(ValueError):
            HistoricalWenshuSource(engine=wenshu_engine, table_name="bad; DROP TABLE x")
