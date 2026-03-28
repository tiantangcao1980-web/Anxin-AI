import pytest
from src.services.oa_integration_service import oa_service, OAProviderType

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
