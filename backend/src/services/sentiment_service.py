"""
舆情监控服务
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from loguru import logger

from src.models.sentiment import (
    SentimentRecord, SentimentAlert, SentimentMonitor,
    SentimentType, RiskLevel, AlertLevel, AlertType, SourceType
)
class SentimentService:
    """舆情监控服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._agent = None
    
    @property
    def agent(self):
        """延迟导入和初始化舆情分析Agent，避免循环依赖"""
        if self._agent is None:
            from src.agents.sentiment_agent import SentimentAnalysisAgent
            self._agent = SentimentAnalysisAgent()
        return self._agent
    
    # ============ 监控配置管理 ============
    
    async def create_monitor(
        self,
        name: str,
        keywords: List[str],
        sources: Optional[List[str]] = None,
        alert_threshold: float = 0.7,
        org_id: Optional[str] = None,
        created_by: Optional[str] = None,
        **kwargs
    ) -> SentimentMonitor:
        """创建监控配置"""
        monitor = SentimentMonitor(
            name=name,
            keywords=keywords,
            sources=sources,
            alert_threshold=alert_threshold,
            negative_threshold=kwargs.get("negative_threshold", 0.6),
            risk_threshold=kwargs.get("risk_threshold", 0.8),
            description=kwargs.get("description"),
            exclude_keywords=kwargs.get("exclude_keywords"),
            scan_interval=kwargs.get("scan_interval", 3600),
            org_id=org_id,
            created_by=created_by,
        )
        
        self.db.add(monitor)
        await self.db.flush()
        
        logger.info(f"创建监控配置: {name}, 关键词: {keywords}")
        return monitor
    
    async def get_monitor(self, monitor_id: str) -> Optional[SentimentMonitor]:
        """获取监控配置详情"""
        result = await self.db.execute(
            select(SentimentMonitor)
            .options(selectinload(SentimentMonitor.records))
            .options(selectinload(SentimentMonitor.alerts))
            .where(SentimentMonitor.id == monitor_id)
        )
        return result.scalar_one_or_none()
    
    async def list_monitors(
        self,
        org_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[SentimentMonitor], int]:
        """获取监控配置列表"""
        query = select(SentimentMonitor)
        count_query = select(func.count(SentimentMonitor.id))
        
        conditions = []
        if org_id:
            conditions.append(SentimentMonitor.org_id == org_id)
        if is_active is not None:
            conditions.append(SentimentMonitor.is_active == is_active)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # 总数
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页
        query = query.order_by(SentimentMonitor.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        monitors = list(result.scalars().all())
        
        return monitors, total
    
    async def update_monitor(
        self,
        monitor_id: str,
        **kwargs
    ) -> Optional[SentimentMonitor]:
        """更新监控配置"""
        monitor = await self.get_monitor(monitor_id)
        if not monitor:
            return None
        
        for key, value in kwargs.items():
            if value is not None and hasattr(monitor, key):
                setattr(monitor, key, value)
        
        monitor.updated_at = datetime.now()
        await self.db.flush()
        
        return monitor
    
    async def delete_monitor(self, monitor_id: str) -> bool:
        """删除监控配置"""
        monitor = await self.get_monitor(monitor_id)
        if not monitor:
            return False
        
        await self.db.delete(monitor)
        return True
    
    async def toggle_monitor(self, monitor_id: str, is_active: bool) -> Optional[SentimentMonitor]:
        """启用/禁用监控"""
        return await self.update_monitor(monitor_id, is_active=is_active)
    
    # ============ 舆情分析 ============
    
    async def analyze_content(
        self,
        content: str,
        keyword: str,
        source: Optional[str] = None,
        source_type: str = "other",
        monitor_id: Optional[str] = None,
        org_id: Optional[str] = None,
        save_record: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """分析舆情内容"""
        # 调用Agent进行情感分析
        sentiment_result = await self.agent.analyze_sentiment(content, [keyword])
        
        # 调用Agent进行风险评估
        risk_result = await self.agent.assess_risk(content, kwargs.get("context"))
        
        # 解析分析结果（简化处理，实际应用需要更健壮的解析）
        sentiment_type = SentimentType.NEUTRAL
        sentiment_score = 0.0
        risk_level = RiskLevel.LOW
        risk_score = 0.0
        
        # 这里应该解析Agent的响应，提取具体的分数
        # 简化处理：根据关键词判断
        negative_keywords = ["诉讼", "纠纷", "违法", "处罚", "风险", "危机", "投诉"]
        positive_keywords = ["合规", "优秀", "表彰", "荣誉", "成功"]
        
        content_lower = content.lower()
        neg_count = sum(1 for k in negative_keywords if k in content_lower)
        pos_count = sum(1 for k in positive_keywords if k in content_lower)
        
        if neg_count > pos_count:
            sentiment_type = SentimentType.NEGATIVE
            sentiment_score = min(-0.3 - neg_count * 0.1, -1.0)
            risk_level = RiskLevel.HIGH if neg_count > 2 else RiskLevel.MEDIUM
            risk_score = min(0.5 + neg_count * 0.1, 1.0)
        elif pos_count > neg_count:
            sentiment_type = SentimentType.POSITIVE
            sentiment_score = min(0.3 + pos_count * 0.1, 1.0)
        
        result = {
            "sentiment_type": sentiment_type.value,
            "sentiment_score": sentiment_score,
            "risk_level": risk_level.value,
            "risk_score": risk_score,
            "analysis": sentiment_result.get("analysis"),
            "risk_assessment": risk_result.get("risk_assessment"),
        }
        
        # 保存记录
        if save_record:
            record = await self.create_record(
                keyword=keyword,
                content=content,
                source=source,
                source_type=source_type,
                sentiment_type=sentiment_type.value,
                sentiment_score=sentiment_score,
                risk_level=risk_level.value,
                risk_score=risk_score,
                monitor_id=monitor_id,
                org_id=org_id,
                ai_analysis={
                    "sentiment": sentiment_result,
                    "risk": risk_result
                },
                **kwargs
            )
            result["record_id"] = record.id
            
            # 检查是否需要触发预警
            if risk_score >= 0.7 or sentiment_score <= -0.7:
                await self._trigger_alert(record, monitor_id, org_id)
        
        return result
    
    async def create_record(
        self,
        keyword: str,
        content: str,
        sentiment_type: str,
        sentiment_score: float,
        risk_level: str,
        risk_score: float,
        source: Optional[str] = None,
        source_type: str = "other",
        monitor_id: Optional[str] = None,
        org_id: Optional[str] = None,
        **kwargs
    ) -> SentimentRecord:
        """创建舆情记录"""
        record = SentimentRecord(
            keyword=keyword,
            content=content,
            title=kwargs.get("title"),
            source=source,
            source_type=SourceType(source_type) if source_type in [e.value for e in SourceType] else SourceType.OTHER,
            sentiment_type=SentimentType(sentiment_type) if sentiment_type in [e.value for e in SentimentType] else SentimentType.NEUTRAL,
            sentiment_score=sentiment_score,
            risk_level=RiskLevel(risk_level) if risk_level in [e.value for e in RiskLevel] else RiskLevel.LOW,
            risk_score=risk_score,
            risk_factors=kwargs.get("risk_factors"),
            ai_analysis=kwargs.get("ai_analysis"),
            summary=kwargs.get("summary"),
            publish_time=kwargs.get("publish_time"),
            author=kwargs.get("author"),
            engagement=kwargs.get("engagement"),
            monitor_id=monitor_id,
            org_id=org_id,
        )
        
        self.db.add(record)
        await self.db.flush()
        
        # 更新监控统计
        if monitor_id:
            await self._update_monitor_stats(monitor_id, record)
        
        return record
    
    async def _update_monitor_stats(self, monitor_id: str, record: SentimentRecord):
        """更新监控统计信息"""
        result = await self.db.execute(
            select(SentimentMonitor).where(SentimentMonitor.id == monitor_id)
        )
        monitor = result.scalar_one_or_none()
        if monitor:
            monitor.total_records += 1
            if record.sentiment_type == SentimentType.NEGATIVE:
                monitor.negative_count += 1
            monitor.last_scan_at = datetime.now()
            await self.db.flush()
    
    async def _trigger_alert(
        self,
        record: SentimentRecord,
        monitor_id: Optional[str],
        org_id: Optional[str]
    ):
        """触发舆情预警"""
        # 确定预警类型和等级
        if record.risk_score >= 0.9:
            alert_type = AlertType.HIGH_RISK
            alert_level = AlertLevel.CRITICAL
        elif record.risk_score >= 0.7:
            alert_type = AlertType.HIGH_RISK
            alert_level = AlertLevel.DANGER
        elif record.sentiment_score <= -0.8:
            alert_type = AlertType.NEGATIVE_SURGE
            alert_level = AlertLevel.WARNING
        else:
            alert_type = AlertType.KEYWORD_MATCH
            alert_level = AlertLevel.INFO
        
        alert = SentimentAlert(
            alert_type=alert_type,
            alert_level=alert_level,
            title=f"舆情预警: {record.keyword}",
            message=f"检测到{'高风险' if record.risk_score >= 0.7 else '负面'}舆情，请及时关注。\n\n内容摘要: {record.content[:200]}...",
            related_records=[record.id],
            statistics={
                "sentiment_score": record.sentiment_score,
                "risk_score": record.risk_score,
                "risk_level": record.risk_level.value,
            },
            monitor_id=monitor_id,
            org_id=org_id,
        )
        
        self.db.add(alert)
        await self.db.flush()
        
        # 更新监控预警计数
        if monitor_id:
            result = await self.db.execute(
                select(SentimentMonitor).where(SentimentMonitor.id == monitor_id)
            )
            monitor = result.scalar_one_or_none()
            if monitor:
                monitor.alert_count += 1
                await self.db.flush()
        
        logger.warning(f"触发舆情预警: {alert.title}")
    
    # ============ 舆情记录查询 ============
    
    async def get_record(self, record_id: str) -> Optional[SentimentRecord]:
        """获取舆情记录详情"""
        result = await self.db.execute(
            select(SentimentRecord).where(SentimentRecord.id == record_id)
        )
        return result.scalar_one_or_none()
    
    async def list_records(
        self,
        org_id: Optional[str] = None,
        monitor_id: Optional[str] = None,
        keyword: Optional[str] = None,
        sentiment_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[SentimentRecord], int]:
        """获取舆情记录列表"""
        query = select(SentimentRecord)
        count_query = select(func.count(SentimentRecord.id))
        
        conditions = []
        if org_id:
            conditions.append(SentimentRecord.org_id == org_id)
        if monitor_id:
            conditions.append(SentimentRecord.monitor_id == monitor_id)
        if keyword:
            conditions.append(SentimentRecord.keyword.ilike(f"%{keyword}%"))
        if sentiment_type:
            conditions.append(SentimentRecord.sentiment_type == SentimentType(sentiment_type))
        if risk_level:
            conditions.append(SentimentRecord.risk_level == RiskLevel(risk_level))
        if start_date:
            conditions.append(SentimentRecord.created_at >= start_date)
        if end_date:
            conditions.append(SentimentRecord.created_at <= end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # 总数
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页
        query = query.order_by(SentimentRecord.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        records = list(result.scalars().all())
        
        return records, total
    
    # ============ 预警管理 ============
    
    async def get_alert(self, alert_id: str) -> Optional[SentimentAlert]:
        """获取预警详情"""
        result = await self.db.execute(
            select(SentimentAlert).where(SentimentAlert.id == alert_id)
        )
        return result.scalar_one_or_none()
    
    async def list_alerts(
        self,
        org_id: Optional[str] = None,
        is_read: Optional[bool] = None,
        is_handled: Optional[bool] = None,
        alert_level: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[SentimentAlert], int]:
        """获取预警列表"""
        query = select(SentimentAlert)
        count_query = select(func.count(SentimentAlert.id))
        
        conditions = []
        if org_id:
            conditions.append(SentimentAlert.org_id == org_id)
        if is_read is not None:
            conditions.append(SentimentAlert.is_read == is_read)
        if is_handled is not None:
            conditions.append(SentimentAlert.is_handled == is_handled)
        if alert_level:
            conditions.append(SentimentAlert.alert_level == AlertLevel(alert_level))
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # 总数
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页
        query = query.order_by(SentimentAlert.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        alerts = list(result.scalars().all())
        
        return alerts, total
    
    async def mark_alert_read(self, alert_id: str) -> Optional[SentimentAlert]:
        """标记预警已读"""
        alert = await self.get_alert(alert_id)
        if not alert:
            return None
        
        alert.is_read = True
        await self.db.flush()
        return alert
    
    async def handle_alert(
        self,
        alert_id: str,
        handled_by: str,
        handle_note: Optional[str] = None
    ) -> Optional[SentimentAlert]:
        """处理预警"""
        alert = await self.get_alert(alert_id)
        if not alert:
            return None
        
        alert.is_handled = True
        alert.handled_at = datetime.now()
        alert.handled_by = handled_by
        alert.handle_note = handle_note
        await self.db.flush()
        return alert
    
    # ============ 统计报告 ============
    
    async def get_statistics(
        self,
        org_id: Optional[str] = None,
        days: int = 7,
    ) -> Dict[str, Any]:
        """获取舆情统计信息"""
        start_date = datetime.now() - timedelta(days=days)
        
        conditions = [SentimentRecord.created_at >= start_date]
        if org_id:
            conditions.append(SentimentRecord.org_id == org_id)
        
        # 总数
        total_query = select(func.count(SentimentRecord.id)).where(and_(*conditions))
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0
        
        # 情感分布
        sentiment_stats = {}
        for sentiment in SentimentType:
            query = select(func.count(SentimentRecord.id)).where(
                and_(*conditions, SentimentRecord.sentiment_type == sentiment)
            )
            result = await self.db.execute(query)
            sentiment_stats[sentiment.value] = result.scalar() or 0
        
        # 风险分布
        risk_stats = {}
        for risk in RiskLevel:
            query = select(func.count(SentimentRecord.id)).where(
                and_(*conditions, SentimentRecord.risk_level == risk)
            )
            result = await self.db.execute(query)
            risk_stats[risk.value] = result.scalar() or 0
        
        # 预警统计
        alert_conditions = [SentimentAlert.created_at >= start_date]
        if org_id:
            alert_conditions.append(SentimentAlert.org_id == org_id)
        
        alert_total_query = select(func.count(SentimentAlert.id)).where(and_(*alert_conditions))
        alert_total_result = await self.db.execute(alert_total_query)
        alert_total = alert_total_result.scalar() or 0
        
        unread_query = select(func.count(SentimentAlert.id)).where(
            and_(*alert_conditions, SentimentAlert.is_read == False)
        )
        unread_result = await self.db.execute(unread_query)
        unread_count = unread_result.scalar() or 0
        
        # 每日趋势
        daily_trend = []
        for i in range(days):
            date = datetime.now() - timedelta(days=days - 1 - i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)
            
            day_conditions = conditions.copy()
            day_conditions.append(SentimentRecord.created_at >= date_start)
            day_conditions.append(SentimentRecord.created_at < date_end)
            
            day_query = select(func.count(SentimentRecord.id)).where(and_(*day_conditions))
            day_result = await self.db.execute(day_query)
            day_count = day_result.scalar() or 0
            
            daily_trend.append({
                "date": date_start.strftime("%Y-%m-%d"),
                "count": day_count
            })
        
        return {
            "period": f"{days}天",
            "total_records": total,
            "sentiment_distribution": sentiment_stats,
            "risk_distribution": risk_stats,
            "alerts": {
                "total": alert_total,
                "unread": unread_count,
            },
            "daily_trend": daily_trend,
        }
    
    async def generate_report(
        self,
        org_id: Optional[str] = None,
        period: str = "daily",
        focus_keywords: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """生成舆情分析报告"""
        # 确定时间范围
        period_days = {"daily": 1, "weekly": 7, "monthly": 30}
        days = period_days.get(period, 1)
        start_date = datetime.now() - timedelta(days=days)
        
        # 获取记录
        records, total = await self.list_records(
            org_id=org_id,
            start_date=start_date,
            page_size=100
        )
        
        # 转换为字典列表
        records_data = [
            {
                "keyword": r.keyword,
                "content": r.content,
                "sentiment_type": r.sentiment_type.value,
                "risk_level": r.risk_level.value,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
        
        # 调用Agent生成报告
        report = await self.agent.generate_report(
            records=records_data,
            period=period,
            focus_keywords=focus_keywords
        )
        
        return report
