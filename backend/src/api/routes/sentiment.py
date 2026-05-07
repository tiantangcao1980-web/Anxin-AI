"""舆情监控API路由"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.sentiment_service import SentimentService

router = APIRouter()


# ============ 请求/响应模型 ============

class MonitorCreate(BaseModel):
    """创建监控配置"""
    name: str
    keywords: list[str]
    sources: list[str] | None = None
    exclude_keywords: list[str] | None = None
    alert_threshold: float = Field(default=0.7, ge=0, le=1)
    negative_threshold: float = Field(default=0.6, ge=0, le=1)
    risk_threshold: float = Field(default=0.8, ge=0, le=1)
    scan_interval: int = Field(default=3600, ge=60)
    description: str | None = None


class MonitorUpdate(BaseModel):
    """更新监控配置"""
    name: str | None = None
    keywords: list[str] | None = None
    sources: list[str] | None = None
    exclude_keywords: list[str] | None = None
    alert_threshold: float | None = None
    negative_threshold: float | None = None
    risk_threshold: float | None = None
    scan_interval: int | None = None
    description: str | None = None
    is_active: bool | None = None


class MonitorResponse(BaseModel):
    """监控配置响应"""
    id: str
    name: str
    keywords: list[str]
    sources: list[str] | None = None
    alert_threshold: float
    is_active: bool
    total_records: int
    negative_count: int
    alert_count: int
    last_scan_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MonitorListResponse(BaseModel):
    """监控配置列表响应"""
    items: list[MonitorResponse]
    total: int
    page: int
    page_size: int


class SentimentAnalyzeRequest(BaseModel):
    """舆情分析请求"""
    content: str
    keyword: str
    source: str | None = None
    source_type: str = "other"
    title: str | None = None
    save_record: bool = True


class SentimentAnalyzeResponse(BaseModel):
    """舆情分析响应"""
    sentiment_type: str
    sentiment_score: float
    risk_level: str
    risk_score: float
    analysis: str | None = None
    record_id: str | None = None


class RecordResponse(BaseModel):
    """舆情记录响应"""
    id: str
    keyword: str
    title: str | None = None
    content: str
    source: str | None = None
    source_type: str
    sentiment_type: str
    sentiment_score: float
    risk_level: str
    risk_score: float
    summary: str | None = None
    created_at: datetime


class RecordListResponse(BaseModel):
    """舆情记录列表响应"""
    items: list[RecordResponse]
    total: int
    page: int
    page_size: int


class AlertResponse(BaseModel):
    """预警响应"""
    id: str
    alert_type: str
    alert_level: str
    title: str
    message: str
    is_read: bool
    is_handled: bool
    handled_at: datetime | None = None
    handle_note: str | None = None
    created_at: datetime


class AlertListResponse(BaseModel):
    """预警列表响应"""
    items: list[AlertResponse]
    total: int
    page: int
    page_size: int


class AlertHandleRequest(BaseModel):
    """处理预警请求"""
    handle_note: str | None = None


class StatisticsResponse(BaseModel):
    """统计响应"""
    period: str
    total_records: int
    sentiment_distribution: dict[str, Any]
    risk_distribution: dict[str, Any]
    alerts: dict[str, Any]
    daily_trend: list[dict[str, Any]]


class ReportRequest(BaseModel):
    """报告请求"""
    period: str = "daily"  # daily, weekly, monthly
    focus_keywords: list[str] | None = None


# ============ 监控配置路由 ============

@router.get("/monitors", response_model=UnifiedResponse)
async def list_monitors(
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取监控配置列表"""
    service = SentimentService(db)

    monitors, total = await service.list_monitors(
        org_id=user.org_id,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )

    data = MonitorListResponse(
        items=[
            MonitorResponse(
                id=m.id,
                name=m.name,
                keywords=m.keywords,
                sources=m.sources,
                alert_threshold=m.alert_threshold,
                is_active=m.is_active,
                total_records=m.total_records,
                negative_count=m.negative_count,
                alert_count=m.alert_count,
                last_scan_at=m.last_scan_at,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in monitors
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
    return UnifiedResponse.success(data=data)


@router.post("/monitors", response_model=UnifiedResponse)
async def create_monitor(
    request: MonitorCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """创建监控配置"""
    service = SentimentService(db)

    monitor = await service.create_monitor(
        name=request.name,
        keywords=request.keywords,
        sources=request.sources,
        alert_threshold=request.alert_threshold,
        org_id=user.org_id,
        created_by=user.id,
        negative_threshold=request.negative_threshold,
        risk_threshold=request.risk_threshold,
        scan_interval=request.scan_interval,
        description=request.description,
        exclude_keywords=request.exclude_keywords,
    )

    data = MonitorResponse(
        id=monitor.id,
        name=monitor.name,
        keywords=monitor.keywords,
        sources=monitor.sources,
        alert_threshold=monitor.alert_threshold,
        is_active=monitor.is_active,
        total_records=monitor.total_records,
        negative_count=monitor.negative_count,
        alert_count=monitor.alert_count,
        last_scan_at=monitor.last_scan_at,
        created_at=monitor.created_at,
        updated_at=monitor.updated_at,
    )
    return UnifiedResponse.success(data=data)


@router.get("/monitors/{monitor_id}", response_model=UnifiedResponse)
async def get_monitor(
    monitor_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取监控配置详情"""
    service = SentimentService(db)
    monitor = await service.get_monitor(monitor_id)

    if not monitor:
        return UnifiedResponse.error(code=404, message="监控配置不存在")
    if monitor.org_id and str(monitor.org_id) != str(user.org_id):
        return UnifiedResponse.error(code=403, message="无权访问该监控配置")

    data = MonitorResponse(
        id=monitor.id,
        name=monitor.name,
        keywords=monitor.keywords,
        sources=monitor.sources,
        alert_threshold=monitor.alert_threshold,
        is_active=monitor.is_active,
        total_records=monitor.total_records,
        negative_count=monitor.negative_count,
        alert_count=monitor.alert_count,
        last_scan_at=monitor.last_scan_at,
        created_at=monitor.created_at,
        updated_at=monitor.updated_at,
    )
    return UnifiedResponse.success(data=data)


@router.put("/monitors/{monitor_id}", response_model=UnifiedResponse)
async def update_monitor(
    monitor_id: str,
    request: MonitorUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """更新监控配置"""
    service = SentimentService(db)
    existing = await service.get_monitor(monitor_id)
    if not existing:
        return UnifiedResponse.error(code=404, message="监控配置不存在")
    if existing.org_id and str(existing.org_id) != str(user.org_id):
        return UnifiedResponse.error(code=403, message="无权修改该监控配置")

    monitor = await service.update_monitor(
        monitor_id=monitor_id,
        **request.model_dump(exclude_unset=True)
    )
    if not monitor:
        return UnifiedResponse.error(code=404, message="监控配置不存在")

    data = MonitorResponse(
        id=monitor.id,
        name=monitor.name,
        keywords=monitor.keywords,
        sources=monitor.sources,
        alert_threshold=monitor.alert_threshold,
        is_active=monitor.is_active,
        total_records=monitor.total_records,
        negative_count=monitor.negative_count,
        alert_count=monitor.alert_count,
        last_scan_at=monitor.last_scan_at,
        created_at=monitor.created_at,
        updated_at=monitor.updated_at,
    )
    return UnifiedResponse.success(data=data)


@router.delete("/monitors/{monitor_id}", response_model=UnifiedResponse)
async def delete_monitor(
    monitor_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """删除监控配置"""
    service = SentimentService(db)
    monitor = await service.get_monitor(monitor_id)
    if not monitor:
        return UnifiedResponse.error(code=404, message="监控配置不存在")
    if monitor.org_id and str(monitor.org_id) != str(user.org_id):
        return UnifiedResponse.error(code=403, message="无权删除该监控配置")
    if not await service.delete_monitor(monitor_id):
        return UnifiedResponse.error(code=400, message="监控配置删除失败")
    return UnifiedResponse.success(message="监控配置已删除")


@router.post("/monitors/{monitor_id}/toggle", response_model=UnifiedResponse)
async def toggle_monitor(
    monitor_id: str,
    is_active: bool = True,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """启用/禁用监控"""
    service = SentimentService(db)
    existing = await service.get_monitor(monitor_id)
    if not existing:
        return UnifiedResponse.error(code=404, message="监控配置不存在")
    if existing.org_id and str(existing.org_id) != str(user.org_id):
        return UnifiedResponse.error(code=403, message="无权操作该监控配置")
    await service.toggle_monitor(monitor_id, is_active)
    return UnifiedResponse.success(message=f"监控已{'启用' if is_active else '禁用'}")


# ============ 舆情分析路由 ============

@router.post("/analyze", response_model=UnifiedResponse)
async def analyze_sentiment(
    request: SentimentAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """分析舆情内容"""
    service = SentimentService(db)

    result = await service.analyze_content(
        content=request.content,
        keyword=request.keyword,
        source=request.source,
        source_type=request.source_type,
        org_id=user.org_id,
        save_record=request.save_record,
        title=request.title,
    )

    data = SentimentAnalyzeResponse(
        sentiment_type=result["sentiment_type"],
        sentiment_score=result["sentiment_score"],
        risk_level=result["risk_level"],
        risk_score=result["risk_score"],
        analysis=str(result.get("analysis")),
        record_id=result.get("record_id"),
    )
    return UnifiedResponse.success(data=data)


@router.get("/records", response_model=UnifiedResponse)
async def list_records(
    monitor_id: str | None = None,
    keyword: str | None = None,
    sentiment_type: str | None = None,
    risk_level: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取舆情记录列表"""
    service = SentimentService(db)

    records, total = await service.list_records(
        org_id=user.org_id,
        monitor_id=monitor_id,
        keyword=keyword,
        sentiment_type=sentiment_type,
        risk_level=risk_level,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    data = RecordListResponse(
        items=[
            RecordResponse(
                id=r.id,
                keyword=r.keyword,
                title=r.title,
                content=r.content[:500] + "..." if len(r.content) > 500 else r.content,
                source=r.source,
                source_type=r.source_type.value,
                sentiment_type=r.sentiment_type.value,
                sentiment_score=r.sentiment_score,
                risk_level=r.risk_level.value,
                risk_score=r.risk_score,
                summary=r.summary,
                created_at=r.created_at,
            )
            for r in records
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
    return UnifiedResponse.success(data=data)


@router.get("/records/{record_id}", response_model=UnifiedResponse)
async def get_record(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取舆情记录详情"""
    service = SentimentService(db)
    record = await service.get_record(record_id)

    if not record:
        return UnifiedResponse.error(code=404, message="舆情记录不存在")
    if record.org_id and str(record.org_id) != str(user.org_id):
        return UnifiedResponse.error(code=403, message="无权访问该舆情记录")

    data = RecordResponse(
        id=record.id,
        keyword=record.keyword,
        title=record.title,
        content=record.content,
        source=record.source,
        source_type=record.source_type.value,
        sentiment_type=record.sentiment_type.value,
        sentiment_score=record.sentiment_score,
        risk_level=record.risk_level.value,
        risk_score=record.risk_score,
        summary=record.summary,
        created_at=record.created_at,
    )
    return UnifiedResponse.success(data=data)


# ============ 预警管理路由 ============

@router.get("/alerts")
async def list_alerts(
    is_read: bool | None = None,
    is_handled: bool | None = None,
    alert_level: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取预警列表"""
    service = SentimentService(db)

    alerts, total = await service.list_alerts(
        org_id=user.org_id,
        is_read=is_read,
        is_handled=is_handled,
        alert_level=alert_level,
        page=page,
        page_size=page_size,
    )

    data = AlertListResponse(
        items=[
            AlertResponse(
                id=a.id,
                alert_type=a.alert_type.value,
                alert_level=a.alert_level.value,
                title=a.title,
                message=a.message,
                is_read=a.is_read,
                is_handled=a.is_handled,
                handled_at=a.handled_at,
                handle_note=a.handle_note,
                created_at=a.created_at,
            )
            for a in alerts
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
    return UnifiedResponse.success(data=data)


@router.get("/alerts/{alert_id}")
async def get_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取预警详情"""
    service = SentimentService(db)
    alert = await service.get_alert(alert_id)

    if not alert:
        return UnifiedResponse.error(code=404, message="预警不存在")
    if alert.org_id and str(alert.org_id) != str(user.org_id):
        return UnifiedResponse.error(code=403, message="无权访问该预警")

    data = AlertResponse(
        id=alert.id,
        alert_type=alert.alert_type.value,
        alert_level=alert.alert_level.value,
        title=alert.title,
        message=alert.message,
        is_read=alert.is_read,
        is_handled=alert.is_handled,
        handled_at=alert.handled_at,
        handle_note=alert.handle_note,
        created_at=alert.created_at,
    )
    return UnifiedResponse.success(data=data)


@router.post("/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """标记预警已读"""
    service = SentimentService(db)
    existing = await service.get_alert(alert_id)
    if not existing:
        return UnifiedResponse.error(code=404, message="预警不存在")
    if existing.org_id and str(existing.org_id) != str(user.org_id):
        return UnifiedResponse.error(code=403, message="无权操作该预警")
    await service.mark_alert_read(alert_id)
    return UnifiedResponse.success(message="已标记为已读")


@router.post("/alerts/{alert_id}/handle")
async def handle_alert(
    alert_id: str,
    request: AlertHandleRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """处理预警"""
    service = SentimentService(db)
    existing = await service.get_alert(alert_id)
    if not existing:
        return UnifiedResponse.error(code=404, message="预警不存在")
    if existing.org_id and str(existing.org_id) != str(user.org_id):
        return UnifiedResponse.error(code=403, message="无权操作该预警")

    await service.handle_alert(
        alert_id=alert_id,
        handled_by=user.id,
        handle_note=request.handle_note,
    )
    return UnifiedResponse.success(message="预警已处理")


# ============ 统计报告路由 ============

@router.get("/statistics")
async def get_statistics(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取舆情统计"""
    service = SentimentService(db)

    stats = await service.get_statistics(
        org_id=user.org_id,
        days=days,
    )

    return UnifiedResponse.success(data=StatisticsResponse(**stats))


@router.post("/reports")
async def generate_report(
    request: ReportRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """生成舆情分析报告"""
    service = SentimentService(db)

    report = await service.generate_report(
        org_id=user.org_id,
        period=request.period,
        focus_keywords=request.focus_keywords,
    )

    return UnifiedResponse.success(data=report)
