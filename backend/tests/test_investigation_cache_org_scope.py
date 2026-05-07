"""尽调搜索缓存组织隔离回归测试。"""

from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from src.core import database
from src.models.user import Organization
from src.services.investigation_data_store import InvestigationDataStore


def _patch_store_db_context(monkeypatch, db_session) -> None:
    @asynccontextmanager
    async def _test_db_context():
        try:
            yield db_session
            await db_session.flush()
        except Exception:
            await db_session.rollback()
            raise

    monkeypatch.setattr(database, "get_db_context", _test_db_context)


@pytest.mark.asyncio
async def test_cache_reads_and_writes_are_scoped_by_org(monkeypatch, db_session, test_organization):
    _patch_store_db_context(monkeypatch, db_session)
    store = InvestigationDataStore()
    other_org = Organization(id=str(uuid4()), name="另一测试组织")
    db_session.add(other_org)
    await db_session.flush()

    assert await store.save_to_cache(
        "同名测试公司",
        "business_registry",
        {"registry": "org-a"},
        parsed_data={"registry": "org-a"},
        org_id=test_organization.id,
    )
    assert await store.save_to_cache(
        "同名测试公司",
        "business_registry",
        {"registry": "org-b"},
        parsed_data={"registry": "org-b"},
        org_id=other_org.id,
    )

    assert await store.get_cached_data(
        "同名测试公司",
        "business_registry",
        org_id=test_organization.id,
    ) == {"registry": "org-a"}
    assert await store.get_cached_data(
        "同名测试公司",
        "business_registry",
        org_id=other_org.id,
    ) == {"registry": "org-b"}
    assert await store.get_cached_data("同名测试公司", "business_registry") is None


@pytest.mark.asyncio
async def test_dimensions_and_invalidation_only_touch_requested_org(
    monkeypatch,
    db_session,
    test_organization,
):
    _patch_store_db_context(monkeypatch, db_session)
    store = InvestigationDataStore()
    other_org = Organization(id=str(uuid4()), name="隔离测试组织")
    db_session.add(other_org)
    await db_session.flush()

    await store.save_to_cache(
        "目标企业",
        "litigation",
        {"case": "org-a"},
        org_id=test_organization.id,
    )
    await store.save_to_cache("目标企业", "credit", {"score": 80}, org_id=test_organization.id)
    await store.save_to_cache("目标企业", "litigation", {"case": "org-b"}, org_id=other_org.id)

    org_a_dimensions = await store.get_cached_dimensions(
        "目标企业",
        user_id="user-a",
        org_id=test_organization.id,
    )
    org_b_dimensions = await store.get_cached_dimensions(
        "目标企业",
        user_id="user-b",
        org_id=other_org.id,
    )

    assert set(org_a_dimensions) == {"litigation", "credit"}
    assert set(org_b_dimensions) == {"litigation"}

    invalidated = await store.invalidate_cache(
        "目标企业",
        user_id="user-a",
        org_id=test_organization.id,
    )

    assert invalidated == 2
    assert (
        await store.get_cached_data("目标企业", "litigation", org_id=test_organization.id)
        is None
    )
    assert await store.get_cached_data("目标企业", "litigation", org_id=other_org.id) == {
        "case": "org-b"
    }


@pytest.mark.asyncio
async def test_user_scoped_cache_calls_without_org_fail_closed(monkeypatch, db_session):
    _patch_store_db_context(monkeypatch, db_session)
    store = InvestigationDataStore()

    await store.save_to_cache("无组织企业", "business_registry", {"registry": "global"})

    assert await store.get_cached_dimensions("无组织企业", user_id="missing-org-user") == {}
    assert await store.invalidate_cache("无组织企业", user_id="missing-org-user") == 0
    assert await store.get_cached_data("无组织企业", "business_registry") == {"registry": "global"}
