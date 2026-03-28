import pytest
from src.services.signature_service import signature_service, SignType
from src.agents.labor_compliance import LaborComplianceAgent

@pytest.mark.asyncio
async def test_bulk_policy_distribution():
    # 测试批量创建
    users = [
        {"name": "Emp1", "phone": "100"},
        {"name": "Emp2", "phone": "101"}
    ]
    res = await signature_service.create_batch_task(
        "policy_001", users, "admin", SignType.NOTICE_READ, "放假公告"
    )
    
    assert res["total_count"] == 2
    batch_id = res["batch_id"]
    
    # 检查进度
    prog = await signature_service.get_batch_progress(batch_id)
    assert prog["pending_count"] == 2
    assert prog["signed_count"] == 0
    
    # 模拟一人已读
    # 获取 task_id (需要访问私有属性或通过 create 接口返回)
    task_id_1 = signature_service._batches[batch_id][0]
    await signature_service.mock_sign_action(task_id_1, "Emp1", "agree")
    
    prog_updated = await signature_service.get_batch_progress(batch_id)
    assert prog_updated["signed_count"] == 1
    assert prog_updated["completion_rate"] == "50.0%"

@pytest.mark.asyncio
async def test_labor_compliance_publish_intent():
    # 模拟 LaborComplianceAgent 处理发布任务
    agent = LaborComplianceAgent()
    
    # Mock context
    context = {
        "policy_name": "员工手册2026",
        "employees": [{"name": "A"}, {"name": "B"}]
    }
    
    # 直接调用 process
    response = await agent.process({
        "action": "publish_policy", 
        "description": "发布手册",
        "context": context
    })
    
    assert "发起《员工手册2026》的全员宣贯" in response.content
    assert response.actions[0]["type"] == "start_batch_sign"
