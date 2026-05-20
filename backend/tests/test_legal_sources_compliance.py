"""P6-C 法律数据源 — 合规底线测试。

确保 wenshu.court.gov.cn / mp.weixin.qq.com 在任何调用路径上都被硬拒。
"""

from __future__ import annotations

import pytest

from src.services.fetch.sources.legal import (
    BANNED_HOSTS,
    ComplianceError,
    HistoricalWenshuSource,
    LawSearchQuery,
    assert_url_compliant,
)


class TestBannedHosts:
    def test_banned_hosts_set(self) -> None:
        assert "wenshu.court.gov.cn" in BANNED_HOSTS
        assert "mp.weixin.qq.com" in BANNED_HOSTS

    @pytest.mark.parametrize(
        "url",
        [
            "https://wenshu.court.gov.cn/website/wenshu/searchapi/search",
            "http://wenshu.court.gov.cn/list",
            "https://www.wenshu.court.gov.cn/",
            "https://mp.weixin.qq.com/s/abc123",
            "https://mp.weixin.qq.com/profile?biz=foo",
        ],
    )
    def test_assert_url_compliant_rejects_banned(self, url: str) -> None:
        with pytest.raises(ComplianceError) as exc:
            assert_url_compliant(url)
        msg = str(exc.value)
        assert "合规拒绝" in msg
        assert "P6-C" in msg

    @pytest.mark.parametrize(
        "url",
        [
            "https://flk.npc.gov.cn/api/",
            "https://public.creditchina.gov.cn/credit-publicity/search",
            "https://api.pkulaw.com/v1/laws/search",
            "https://api.wkinfo.com.cn/v1/search",
        ],
    )
    def test_assert_url_compliant_allows_whitelist(self, url: str) -> None:
        # 不抛即可
        assert_url_compliant(url)

    def test_assert_url_compliant_rejects_empty_host(self) -> None:
        with pytest.raises(ComplianceError):
            assert_url_compliant("not-a-url")


class TestHistoricalWenshuDefenseInDepth:
    """historical_wenshu 不该走 HTTP，但仍需对错误传参防御性拒绝。"""

    @pytest.mark.asyncio
    async def test_jurisdiction_referencing_wenshu_rejected(self) -> None:
        # 构造一个只用于"上游错误传参"测试的 source；engine 此处不会被调用
        class _DummyEngine:  # 仅占位，避免真实连接
            pass

        src = HistoricalWenshuSource(engine=_DummyEngine(), table_name="wenshu_historical")  # type: ignore[arg-type]

        bad_query = LawSearchQuery(
            keyword="合同纠纷",
            jurisdiction="wenshu.court.gov.cn",  # 上游错误传参
        )
        with pytest.raises(ComplianceError):
            await src.search(bad_query)
