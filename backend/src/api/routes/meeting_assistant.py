"""AI 旁听助手 API 路由"""


from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.meeting_assistant_service import meeting_assistant

router = APIRouter()


class StartListeningRequest(BaseModel):
    conversation_id: str
    conversation_type: str = "im"  # im | anonymous_chat


class StopListeningRequest(BaseModel):
    conversation_id: str


class LinkCaseRequest(BaseModel):
    case_id: str | None = None
    contract_id: str | None = None


@router.post("/start", response_model=UnifiedResponse)
async def start_listening(
    req: StartListeningRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """开启 AI 旁听"""
    if req.conversation_type not in ("im", "anonymous_chat"):
        raise HTTPException(status_code=400, detail="不支持的对话类型")

    existing = await meeting_assistant.get_record(db, req.conversation_id)
    if existing and str(existing.started_by) != str(user.id):
        raise HTTPException(status_code=403, detail="该对话已有其他用户开启旁听")

    record = await meeting_assistant.start_listening(
        db=db,
        conversation_id=req.conversation_id,
        conversation_type=req.conversation_type,
        user_id=str(user.id),
    )
    await db.commit()

    return UnifiedResponse.success(
        data={
            "record_id": record.id,
            "conversation_id": record.conversation_id,
            "status": record.status,
            "started_at": record.started_at.isoformat() if record.started_at else None,
        },
        message="AI 旁听已开启",
    )


@router.post("/stop", response_model=UnifiedResponse)
async def stop_listening(
    req: StopListeningRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """停止旁听并生成纪要"""
    existing = await meeting_assistant.get_record(db, req.conversation_id)
    if existing and str(existing.started_by) != str(user.id):
        raise HTTPException(status_code=403, detail="无权停止该旁听记录")

    record = await meeting_assistant.stop_listening(
        db=db,
        conversation_id=req.conversation_id,
    )
    if not record:
        raise HTTPException(status_code=404, detail="未找到进行中的旁听记录")

    await db.commit()

    return UnifiedResponse.success(
        data={
            "record_id": record.id,
            "status": record.status,
            "summary": record.summary,
            "action_items": record.action_items,
            "ended_at": record.ended_at.isoformat() if record.ended_at else None,
        },
        message="AI 旁听已结束，纪要已生成",
    )


@router.get("/status/{conversation_id}", response_model=UnifiedResponse)
async def get_status(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """查询旁听状态"""
    record = await meeting_assistant.get_record(db, conversation_id)
    is_active = bool(record and str(record.started_by) == str(user.id) and meeting_assistant.is_listening(conversation_id))
    return UnifiedResponse.success(data={"listening": is_active})


@router.get("/insights/{conversation_id}", response_model=UnifiedResponse)
async def get_insights(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取实时分析结果"""
    record = await meeting_assistant.get_record(db, conversation_id)
    if not record or str(record.started_by) != str(user.id):
        return UnifiedResponse.success(data={"insights": []})

    return UnifiedResponse.success(data={"insights": record.insights or []})


@router.get("/summary/{conversation_id}", response_model=UnifiedResponse)
async def get_summary(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取结构化纪要"""
    record = await meeting_assistant.get_record(db, conversation_id)
    if not record or str(record.started_by) != str(user.id):
        raise HTTPException(status_code=404, detail="未找到旁听记录")

    return UnifiedResponse.success(
        data={
            "record_id": record.id,
            "status": record.status,
            "summary": record.summary,
            "action_items": record.action_items,
            "transcript_text": record.transcript_text,
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "ended_at": record.ended_at.isoformat() if record.ended_at else None,
        }
    )


@router.get("/records", response_model=UnifiedResponse)
async def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取用户的旁听记录列表"""
    records, total = await meeting_assistant.get_records_by_user(
        db, str(user.id), page, page_size
    )
    return UnifiedResponse.success(
        data={
            "items": [
                {
                    "id": r.id,
                    "conversation_id": r.conversation_id,
                    "conversation_type": r.conversation_type,
                    "status": r.status,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "ended_at": r.ended_at.isoformat() if r.ended_at else None,
                    "summary_title": (r.summary or {}).get("title", ""),
                }
                for r in records
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/{record_id}/link-case", response_model=UnifiedResponse)
async def link_case(
    record_id: str,
    req: LinkCaseRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """将旁听记录关联到案件或合同"""
    from sqlalchemy import select

    from src.models.meeting_record import MeetingRecord

    result = await db.execute(
        select(MeetingRecord).where(MeetingRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if str(record.started_by) != str(user.id):
        raise HTTPException(status_code=403, detail="无权操作该旁听记录")

    if req.case_id:
        record.related_case_id = req.case_id
    if req.contract_id:
        record.related_contract_id = req.contract_id

    await db.commit()
    return UnifiedResponse.success(message="关联成功")
