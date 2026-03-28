import pytest
from src.services.signature_service import signature_service, SignStatus
from src.agents.contract_steward import ContractStewardAgent

@pytest.mark.asyncio
async def test_signature_flow():
    # 测试发起签约
    task = await signature_service.create_signature_task(
        "doc_123", [{"name": "UserA", "phone": "13800000000"}], "admin"
    )
    assert task["status"] == SignStatus.PENDING.value
    assert len(task["audit_trail"]) == 1
    
    # 测试签署
    updated_task = await signature_service.mock_sign_action(task["task_id"], "UserA")
    assert updated_task["status"] == SignStatus.SIGNED.value
    assert len(updated_task["audit_trail"]) == 2

@pytest.mark.asyncio
async def test_contract_steward_check():
    agent = ContractStewardAgent()
    
    # Mock LLM check
    async def mock_chat(msg):
        return '{"alerts": [{"type": "expiration", "message": "Contract expiring soon"}]}'
    agent.chat = mock_chat
    
    # 模拟还有10天到期
    metadata = {"expiration_date": "2026-02-15"} 
    
    response = await agent.process({
        "action": "check_status",
        "context": {"contract_metadata": metadata}
    })
    
    assert "Contract expiring soon" in response.content
