import pytest

from src.core.config import settings
from src.services.oa_integration_service import (
    DingTalkProvider,
    FeishuProvider,
    OAProviderConfigError,
    WeComProvider,
    oa_service,
)


@pytest.mark.asyncio
async def test_oa_notification():
    # Test Feishu
    res_feishu = await oa_service.send_notification("u1", "Test Title", "Test Content", "feishu")
    assert res_feishu is True

    # Test DingTalk
    res_ding = await oa_service.send_notification("u2", "Test Title", "Test Content", "dingtalk")
    assert res_ding is True

@pytest.mark.asyncio
async def test_oa_approval():
    # Test WeCom
    instance_id = await oa_service.initiate_approval(
        "Contract Review", {"amount": 1000}, "u_init", "wecom"
    )
    assert "wecom_sp" in instance_id

@pytest.mark.asyncio
async def test_org_sync():
    data = await oa_service.sync_org_structure("feishu")
    assert data["synced_count"] > 0
    assert data["users"][0]["name"] == "Feishu User 1"


@pytest.mark.asyncio
async def test_feishu_missing_credentials_fail_closed_in_commercial_environment(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.delenv("FEISHU_APP_ID", raising=False)
    monkeypatch.delenv("FEISHU_APP_SECRET", raising=False)
    provider = FeishuProvider()

    with pytest.raises(OAProviderConfigError, match="FEISHU_APP_ID"):
        await provider.send_notification("u1", "Title", "Content")


@pytest.mark.asyncio
async def test_dingtalk_missing_credentials_fail_closed_in_commercial_environment(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.delenv("DINGTALK_APP_KEY", raising=False)
    monkeypatch.delenv("DINGTALK_APP_SECRET", raising=False)
    provider = DingTalkProvider()

    with pytest.raises(OAProviderConfigError, match="DINGTALK_APP_KEY"):
        await provider.create_approval_instance("tpl", "u1", {"amount": 100})


@pytest.mark.asyncio
async def test_wecom_mock_org_sync_fail_closed_in_commercial_environment(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    provider = WeComProvider()

    with pytest.raises(OAProviderConfigError, match="组织架构同步"):
        await provider.sync_department_users("root")
