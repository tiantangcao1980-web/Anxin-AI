"""
舆情服务测试
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.sentiment_service import SentimentService
from src.models.sentiment import (
    SentimentRecord, SentimentAlert, SentimentMonitor,
    SentimentType, RiskLevel, AlertLevel, AlertType
)
from src.models.user import User, Organization


# ============ 监控配置测试 ============

class TestSentimentMonitorCRUD:
    """测试监控配置CRUD操作"""
    
    @pytest.mark.asyncio
    async def test_create_monitor(self, db_session: AsyncSession, test_user: User, test_organization: Organization):
        """测试创建监控配置"""
        service = SentimentService(db_session)
        
        monitor = await service.create_monitor(
            name="法务舆情监控",
            keywords=["法务", "诉讼", "合同纠纷"],
            sources=["news", "social_media"],
            alert_threshold=0.7,
            org_id=test_organization.id,
            created_by=test_user.id,
        )
        
        assert monitor is not None
        assert monitor.name == "法务舆情监控"
        assert len(monitor.keywords) == 3
        assert monitor.alert_threshold == 0.7
        assert monitor.is_active is True
    
    @pytest.mark.asyncio
    async def test_get_monitor(self, db_session: AsyncSession, test_monitor: SentimentMonitor):
        """测试获取监控配置"""
        service = SentimentService(db_session)
        
        monitor = await service.get_monitor(test_monitor.id)
        
        assert monitor is not None
        assert monitor.id == test_monitor.id
    
    @pytest.mark.asyncio
    async def test_list_monitors(self, db_session: AsyncSession, test_monitor: SentimentMonitor):
        """测试获取监控配置列表"""
        service = SentimentService(db_session)
        
        monitors, total = await service.list_monitors()
        
        assert len(monitors) >= 1
        assert total >= 1
    
    @pytest.mark.asyncio
    async def test_update_monitor(self, db_session: AsyncSession, test_monitor: SentimentMonitor):
        """测试更新监控配置"""
        service = SentimentService(db_session)
        
        updated = await service.update_monitor(
            monitor_id=test_monitor.id,
            name="更新后的监控",
            alert_threshold=0.8
        )
        
        assert updated is not None
        assert updated.name == "更新后的监控"
        assert updated.alert_threshold == 0.8
    
    @pytest.mark.asyncio
    async def test_toggle_monitor(self, db_session: AsyncSession, test_monitor: SentimentMonitor):
        """测试启用/禁用监控"""
        service = SentimentService(db_session)
        
        # 禁用
        monitor = await service.toggle_monitor(test_monitor.id, False)
        assert monitor.is_active is False
        
        # 启用
        monitor = await service.toggle_monitor(test_monitor.id, True)
        assert monitor.is_active is True
    
    @pytest.mark.asyncio
    async def test_delete_monitor(self, db_session: AsyncSession, test_monitor: SentimentMonitor):
        """测试删除监控配置"""
        service = SentimentService(db_session)
        
        success = await service.delete_monitor(test_monitor.id)
        assert success is True
        
        # 验证已删除
        monitor = await service.get_monitor(test_monitor.id)
        assert monitor is None


# ============ 舆情分析测试 ============

class TestSentimentAnalysis:
    """测试舆情分析功能"""
    
    @pytest.mark.asyncio
    @patch('src.services.sentiment_service.SentimentAnalysisAgent')
    async def test_analyze_content_positive(self, mock_agent_class, db_session: AsyncSession, test_organization: Organization):
        """测试分析正面舆情"""
        # Mock Agent
        mock_agent = MagicMock()
        mock_agent.analyze_sentiment = AsyncMock(return_value={"analysis": "正面分析结果"})
        mock_agent.assess_risk = AsyncMock(return_value={"risk_assessment": "低风险"})
        mock_agent_class.return_value = mock_agent
        
        service = SentimentService(db_session)
        service._agent = mock_agent
        
        result = await service.analyze_content(
            content="公司法务团队获得年度优秀团队表彰，合规工作成效显著",
            keyword="法务",
            org_id=test_organization.id,
            save_record=True
        )
        
        assert result is not None
        assert "sentiment_type" in result
        assert "risk_level" in result
    
    @pytest.mark.asyncio
    @patch('src.services.sentiment_service.SentimentAnalysisAgent')
    async def test_analyze_content_negative(self, mock_agent_class, db_session: AsyncSession, test_organization: Organization):
        """测试分析负面舆情"""
        mock_agent = MagicMock()
        mock_agent.analyze_sentiment = AsyncMock(return_value={"analysis": "负面分析结果"})
        mock_agent.assess_risk = AsyncMock(return_value={"risk_assessment": "高风险"})
        mock_agent_class.return_value = mock_agent
        
        service = SentimentService(db_session)
        service._agent = mock_agent
        
        result = await service.analyze_content(
            content="公司因合同违约被起诉，涉及金额巨大，面临诉讼风险",
            keyword="诉讼",
            org_id=test_organization.id,
            save_record=True
        )
        
        assert result is not None
        # 包含负面关键词应该被识别为负面/高风险
        assert result["sentiment_type"] in ["negative", "neutral"]


# ============ 舆情记录测试 ============

class TestSentimentRecords:
    """测试舆情记录功能"""
    
    @pytest.mark.asyncio
    async def test_list_records(self, db_session: AsyncSession, test_sentiment_records):
        """测试获取舆情记录列表"""
        service = SentimentService(db_session)
        
        records, total = await service.list_records()
        
        assert len(records) == 3
        assert total == 3
    
    @pytest.mark.asyncio
    async def test_list_records_with_filter(self, db_session: AsyncSession, test_sentiment_records):
        """测试按条件筛选舆情记录"""
        service = SentimentService(db_session)
        
        # 按情感类型筛选
        records, total = await service.list_records(sentiment_type="negative")
        assert total == 1
        
        # 按风险等级筛选
        records, total = await service.list_records(risk_level="high")
        assert total == 1
    
    @pytest.mark.asyncio
    async def test_get_record(self, db_session: AsyncSession, test_sentiment_records):
        """测试获取舆情记录详情"""
        service = SentimentService(db_session)
        
        record = await service.get_record(test_sentiment_records[0].id)
        
        assert record is not None
        assert record.id == test_sentiment_records[0].id


# ============ 预警管理测试 ============

class TestSentimentAlerts:
    """测试预警管理功能"""
    
    @pytest.mark.asyncio
    async def test_list_alerts(self, db_session: AsyncSession, test_organization: Organization):
        """测试获取预警列表"""
        service = SentimentService(db_session)
        
        # 创建测试预警
        alert = SentimentAlert(
            alert_type=AlertType.HIGH_RISK,
            alert_level=AlertLevel.WARNING,
            title="测试预警",
            message="这是一条测试预警消息",
            org_id=test_organization.id,
        )
        db_session.add(alert)
        await db_session.flush()
        
        alerts, total = await service.list_alerts(org_id=test_organization.id)
        
        assert len(alerts) >= 1
        assert total >= 1
    
    @pytest.mark.asyncio
    async def test_mark_alert_read(self, db_session: AsyncSession, test_organization: Organization):
        """测试标记预警已读"""
        service = SentimentService(db_session)
        
        # 创建测试预警
        alert = SentimentAlert(
            alert_type=AlertType.KEYWORD_MATCH,
            alert_level=AlertLevel.INFO,
            title="测试预警",
            message="这是一条测试预警消息",
            org_id=test_organization.id,
            is_read=False,
        )
        db_session.add(alert)
        await db_session.flush()
        
        # 标记已读
        updated = await service.mark_alert_read(alert.id)
        
        assert updated is not None
        assert updated.is_read is True
    
    @pytest.mark.asyncio
    async def test_handle_alert(self, db_session: AsyncSession, test_user: User, test_organization: Organization):
        """测试处理预警"""
        service = SentimentService(db_session)
        
        # 创建测试预警
        alert = SentimentAlert(
            alert_type=AlertType.NEGATIVE_SURGE,
            alert_level=AlertLevel.DANGER,
            title="测试预警",
            message="这是一条测试预警消息",
            org_id=test_organization.id,
        )
        db_session.add(alert)
        await db_session.flush()
        
        # 处理预警
        updated = await service.handle_alert(
            alert_id=alert.id,
            handled_by=test_user.id,
            handle_note="已处理，问题已解决"
        )
        
        assert updated is not None
        assert updated.is_handled is True
        assert updated.handled_by == test_user.id
        assert updated.handle_note == "已处理，问题已解决"


# ============ 统计报告测试 ============

class TestSentimentStatistics:
    """测试统计报告功能"""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, db_session: AsyncSession, test_sentiment_records, test_organization: Organization):
        """测试获取统计信息"""
        service = SentimentService(db_session)
        
        stats = await service.get_statistics(org_id=test_organization.id, days=7)
        
        assert "total_records" in stats
        assert "sentiment_distribution" in stats
        assert "risk_distribution" in stats
        assert "daily_trend" in stats
    
    @pytest.mark.asyncio
    async def test_get_statistics_empty(self, db_session: AsyncSession):
        """测试空数据统计"""
        service = SentimentService(db_session)
        
        stats = await service.get_statistics(days=7)
        
        assert stats["total_records"] == 0
    
    @pytest.mark.asyncio
    @patch('src.services.sentiment_service.SentimentAnalysisAgent')
    async def test_generate_report(self, mock_agent_class, db_session: AsyncSession, test_sentiment_records, test_organization: Organization):
        """测试生成报告"""
        mock_agent = MagicMock()
        mock_agent.generate_report = AsyncMock(return_value={
            "report_type": "daily",
            "report_content": "模拟报告内容",
            "statistics": {}
        })
        mock_agent_class.return_value = mock_agent
        
        service = SentimentService(db_session)
        service._agent = mock_agent
        
        report = await service.generate_report(
            org_id=test_organization.id,
            period="daily"
        )
        
        assert report is not None
        assert "report_type" in report
