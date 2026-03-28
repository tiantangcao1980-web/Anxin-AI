"""
案件服务测试
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.case_service import CaseService
from src.models.case import Case, CaseEvent, CaseStatus, CasePriority, CaseType
from src.models.user import User, Organization


# ============ CRUD操作测试 ============

class TestCaseServiceCRUD:
    """测试案件服务CRUD操作"""
    
    @pytest.mark.asyncio
    async def test_create_case(self, db_session: AsyncSession, test_user: User, test_organization: Organization):
        """测试创建案件"""
        service = CaseService(db_session)
        
        case = await service.create_case(
            title="测试合同审查案件",
            case_type="contract",
            description="这是一个测试案件",
            priority="high",
            org_id=test_organization.id,
            created_by=test_user.id,
        )
        
        assert case is not None
        assert case.title == "测试合同审查案件"
        assert case.case_type == CaseType.CONTRACT
        assert case.status == CaseStatus.PENDING
        assert case.priority == CasePriority.HIGH
        assert case.case_number is not None
        assert case.case_number.startswith("CASE-")
    
    @pytest.mark.asyncio
    async def test_create_case_with_parties(self, db_session: AsyncSession, test_user: User, test_organization: Organization):
        """测试创建带当事人信息的案件"""
        service = CaseService(db_session)
        
        parties = {
            "plaintiff": "甲公司",
            "defendant": "乙公司",
            "lawyers": ["张律师", "李律师"]
        }
        
        case = await service.create_case(
            title="合同纠纷案",
            case_type="litigation",
            parties=parties,
            org_id=test_organization.id,
            created_by=test_user.id,
        )
        
        assert case.parties is not None
        assert case.parties["plaintiff"] == "甲公司"
        assert len(case.parties["lawyers"]) == 2
    
    @pytest.mark.asyncio
    async def test_create_case_with_deadline(self, db_session: AsyncSession, test_user: User, test_organization: Organization):
        """测试创建带截止日期的案件"""
        service = CaseService(db_session)
        
        deadline = datetime.now() + timedelta(days=30)
        
        case = await service.create_case(
            title="限时处理案件",
            case_type="contract",
            deadline=deadline,
            org_id=test_organization.id,
            created_by=test_user.id,
        )
        
        assert case.deadline is not None
    
    @pytest.mark.asyncio
    async def test_get_case(self, db_session: AsyncSession, test_case: Case):
        """测试获取案件详情"""
        service = CaseService(db_session)
        
        case = await service.get_case(test_case.id)
        
        assert case is not None
        assert case.id == test_case.id
        assert case.title == test_case.title
    
    @pytest.mark.asyncio
    async def test_get_case_not_found(self, db_session: AsyncSession):
        """测试获取不存在的案件"""
        service = CaseService(db_session)
        
        case = await service.get_case(str(uuid.uuid4()))
        
        assert case is None
    
    @pytest.mark.asyncio
    async def test_list_cases(self, db_session: AsyncSession, test_cases: list[Case]):
        """测试获取案件列表"""
        service = CaseService(db_session)
        
        cases, total = await service.list_cases(page=1, page_size=10)
        
        assert len(cases) == 5
        assert total == 5
    
    @pytest.mark.asyncio
    async def test_list_cases_with_filter(self, db_session: AsyncSession, test_cases: list[Case]):
        """测试按条件筛选案件列表"""
        service = CaseService(db_session)
        
        # 按状态筛选
        cases, total = await service.list_cases(status="pending")
        assert total == 3  # 前3个是pending状态
        
        # 按类型筛选
        cases, total = await service.list_cases(case_type="contract")
        assert total == 3  # 偶数索引是contract类型
    
    @pytest.mark.asyncio
    async def test_list_cases_pagination(self, db_session: AsyncSession, test_cases: list[Case]):
        """测试案件列表分页"""
        service = CaseService(db_session)
        
        # 第一页
        cases1, total = await service.list_cases(page=1, page_size=2)
        assert len(cases1) == 2
        assert total == 5
        
        # 第二页
        cases2, total = await service.list_cases(page=2, page_size=2)
        assert len(cases2) == 2
        
        # 第三页
        cases3, total = await service.list_cases(page=3, page_size=2)
        assert len(cases3) == 1
    
    @pytest.mark.asyncio
    async def test_update_case(self, db_session: AsyncSession, test_case: Case):
        """测试更新案件"""
        service = CaseService(db_session)
        
        updated_case = await service.update_case(
            case_id=test_case.id,
            title="更新后的案件标题",
            status="in_progress",
            priority="urgent"
        )
        
        assert updated_case is not None
        assert updated_case.title == "更新后的案件标题"
        assert updated_case.status == CaseStatus.IN_PROGRESS
        assert updated_case.priority == CasePriority.URGENT
    
    @pytest.mark.asyncio
    async def test_update_case_not_found(self, db_session: AsyncSession):
        """测试更新不存在的案件"""
        service = CaseService(db_session)
        
        result = await service.update_case(
            case_id=str(uuid.uuid4()),
            title="新标题"
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_case(self, db_session: AsyncSession, test_case: Case):
        """测试删除案件"""
        service = CaseService(db_session)
        
        success = await service.delete_case(test_case.id)
        assert success is True
        
        # 验证已删除
        case = await service.get_case(test_case.id)
        assert case is None
    
    @pytest.mark.asyncio
    async def test_delete_case_not_found(self, db_session: AsyncSession):
        """测试删除不存在的案件"""
        service = CaseService(db_session)
        
        success = await service.delete_case(str(uuid.uuid4()))
        assert success is False


# ============ 事件/时间线测试 ============

class TestCaseServiceEvents:
    """测试案件事件功能"""
    
    @pytest.mark.asyncio
    async def test_add_event(self, db_session: AsyncSession, test_case: Case, test_user: User):
        """测试添加案件事件"""
        service = CaseService(db_session)
        
        event = await service.add_event(
            case_id=test_case.id,
            event_type="status_change",
            title="状态变更",
            description="案件状态从待处理变更为处理中",
            created_by=test_user.id
        )
        
        assert event is not None
        assert event.event_type == "status_change"
        assert event.title == "状态变更"
        assert event.case_id == test_case.id
    
    @pytest.mark.asyncio
    async def test_add_event_with_data(self, db_session: AsyncSession, test_case: Case):
        """测试添加带数据的事件"""
        service = CaseService(db_session)
        
        event_data = {
            "old_status": "pending",
            "new_status": "in_progress",
            "changed_by": "admin"
        }
        
        event = await service.add_event(
            case_id=test_case.id,
            event_type="status_change",
            title="状态变更",
            event_data=event_data
        )
        
        assert event.event_data is not None
        assert event.event_data["old_status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_get_timeline(self, db_session: AsyncSession, test_case: Case):
        """测试获取案件时间线"""
        service = CaseService(db_session)
        
        # 添加多个事件
        await service.add_event(test_case.id, "created", "案件创建")
        await service.add_event(test_case.id, "assigned", "案件分配")
        await service.add_event(test_case.id, "comment", "添加备注")
        
        timeline = await service.get_timeline(test_case.id)
        
        assert len(timeline) >= 3
        # 验证按时间倒序排列
        for i in range(len(timeline) - 1):
            assert timeline[i].event_time >= timeline[i + 1].event_time


# ============ 文档关联测试 ============

class TestCaseServiceDocuments:
    """测试案件文档关联功能"""
    
    @pytest.mark.asyncio
    async def test_link_document(self, db_session: AsyncSession, test_case: Case, test_document, test_user: User):
        """测试关联文档到案件"""
        service = CaseService(db_session)
        
        success = await service.link_document(
            case_id=test_case.id,
            document_id=test_document.id,
            created_by=test_user.id
        )
        
        assert success is True
        
        # 验证文档已关联
        documents = await service.get_case_documents(test_case.id)
        assert len(documents) == 1
        assert documents[0].id == test_document.id
    
    @pytest.mark.asyncio
    async def test_unlink_document(self, db_session: AsyncSession, test_case: Case, test_document, test_user: User):
        """测试取消文档关联"""
        service = CaseService(db_session)
        
        # 先关联
        await service.link_document(test_case.id, test_document.id, test_user.id)
        
        # 再取消关联
        success = await service.unlink_document(
            case_id=test_case.id,
            document_id=test_document.id,
            created_by=test_user.id
        )
        
        assert success is True
        
        # 验证文档已取消关联
        documents = await service.get_case_documents(test_case.id)
        assert len(documents) == 0
    
    @pytest.mark.asyncio
    async def test_get_case_documents(self, db_session: AsyncSession, test_case: Case):
        """测试获取案件文档列表"""
        service = CaseService(db_session)
        
        documents = await service.get_case_documents(test_case.id)
        
        assert isinstance(documents, list)


# ============ 统计功能测试 ============

class TestCaseServiceStatistics:
    """测试案件统计功能"""
    
    @pytest.mark.asyncio
    async def test_get_case_statistics(self, db_session: AsyncSession, test_cases: list[Case], test_organization: Organization):
        """测试获取案件统计信息"""
        service = CaseService(db_session)
        
        stats = await service.get_case_statistics(org_id=test_organization.id)
        
        assert "total" in stats
        assert "by_status" in stats
        assert "by_type" in stats
        assert "by_priority" in stats
        assert stats["total"] == 5
    
    @pytest.mark.asyncio
    async def test_get_case_statistics_empty(self, db_session: AsyncSession):
        """测试空数据库的统计信息"""
        service = CaseService(db_session)
        
        stats = await service.get_case_statistics()
        
        assert stats["total"] == 0
        assert all(v == 0 for v in stats["by_status"].values())


# ============ AI分析测试 ============

class TestCaseServiceAIAnalysis:
    """测试案件AI分析功能"""
    
    @pytest.mark.asyncio
    @patch('src.services.case_service.get_workforce')
    async def test_analyze_case(self, mock_get_workforce, db_session: AsyncSession, test_case: Case, test_user: User):
        """测试AI分析案件"""
        # Mock智能体团队
        mock_workforce = MagicMock()
        mock_workforce.process_task = AsyncMock(return_value={
            "task": "案件分析",
            "analysis": {"agents": ["legal_advisor", "risk_assessor"]},
            "agent_results": [],
            "final_result": {
                "summary": "该案件风险等级为中等",
                "recommendations": ["建议及时处理", "注意证据保全"]
            }
        })
        mock_get_workforce.return_value = mock_workforce
        
        service = CaseService(db_session)
        
        result = await service.analyze_case(test_case.id, user_id=test_user.id)
        
        assert result is not None
        assert "final_result" in result
        mock_workforce.process_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_case_not_found(self, db_session: AsyncSession):
        """测试分析不存在的案件"""
        service = CaseService(db_session)
        
        with pytest.raises(ValueError, match="案件不存在"):
            await service.analyze_case(str(uuid.uuid4()))


# ============ 边界条件测试 ============

class TestCaseServiceEdgeCases:
    """测试边界条件"""
    
    @pytest.mark.asyncio
    async def test_create_case_with_invalid_type(self, db_session: AsyncSession, test_user: User, test_organization: Organization):
        """测试创建无效类型的案件"""
        service = CaseService(db_session)
        
        case = await service.create_case(
            title="测试案件",
            case_type="invalid_type",  # 无效类型
            org_id=test_organization.id,
            created_by=test_user.id,
        )
        
        # 应该使用默认类型
        assert case.case_type == CaseType.OTHER
    
    @pytest.mark.asyncio
    async def test_create_case_with_invalid_priority(self, db_session: AsyncSession, test_user: User, test_organization: Organization):
        """测试创建无效优先级的案件"""
        service = CaseService(db_session)
        
        case = await service.create_case(
            title="测试案件",
            case_type="contract",
            priority="invalid_priority",  # 无效优先级
            org_id=test_organization.id,
            created_by=test_user.id,
        )
        
        # 应该使用默认优先级
        assert case.priority == CasePriority.MEDIUM
    
    @pytest.mark.asyncio
    async def test_list_cases_large_page(self, db_session: AsyncSession, test_cases: list[Case]):
        """测试大页码"""
        service = CaseService(db_session)
        
        cases, total = await service.list_cases(page=100, page_size=10)
        
        assert len(cases) == 0
        assert total == 5
    
    @pytest.mark.asyncio
    async def test_update_case_partial(self, db_session: AsyncSession, test_case: Case):
        """测试部分更新案件"""
        service = CaseService(db_session)
        
        original_title = test_case.title
        
        # 只更新状态
        updated_case = await service.update_case(
            case_id=test_case.id,
            status="completed"
        )
        
        assert updated_case.title == original_title  # 标题不变
        assert updated_case.status == CaseStatus.COMPLETED  # 状态已更新
