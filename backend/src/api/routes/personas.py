"""
personas 路由 —— V3 user-facing persona 对外 API（P7 系列）

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/personas"`` 注册）::

    GET    /api/v1/personas                                列出 user-facing persona
    GET    /api/v1/personas/{persona_id}                   单个 persona 详情
    POST   /api/v1/personas/{persona_id}/chat              通用对话（任意 persona）

    # operations_manager 专用 (P7-A)
    POST   /api/v1/personas/operations/okr/dashboard       OKR 看板
    POST   /api/v1/personas/operations/weekly-report       周报生成
    POST   /api/v1/personas/operations/meeting-minutes     会议纪要
    POST   /api/v1/personas/operations/extract-todos       待办提取

权限：所有路由都需要登录用户。后续 P7-B/C/D/E 添加各自 persona 的
specialized endpoints 时，**请放在自己专属的 ``/personas/<short>/``
前缀下**，并复用上方 PersonaRegistry 即可。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from src.agents.personas import PersonaRegistry
from src.api.routes.schemas.persona import (
    ChatRequest,
    ChatResponse,
    ExtractTodosRequest,
    ExtractTodosResponse,
    MeetingMinutesRequest,
    MeetingMinutesResponse,
    OKRDashboardRequest,
    OKRDashboardResponse,
    OKRItemOut,
    PersonaDetail,
    PersonaListItem,
    PersonaListOut,
    TodoItemOut,
    WeeklyReportRequest,
    WeeklyReportResponse,
)
from src.core.deps import get_current_user_required
from src.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# autoload guard：模块第一次被 include 时自动扫描 personas/ 目录
# ---------------------------------------------------------------------------

_AUTOLOADED = False


def _ensure_autoloaded() -> PersonaRegistry:
    global _AUTOLOADED
    registry = PersonaRegistry.instance()
    if not _AUTOLOADED:
        registry.autoload()
        _AUTOLOADED = True
    return registry


# ---------------------------------------------------------------------------
# 通用：列表 / 详情 / chat
# ---------------------------------------------------------------------------


@router.get("", response_model=PersonaListOut)
async def list_personas(
    _user: User = Depends(get_current_user_required),
) -> PersonaListOut:
    """列出所有已注册的 user-facing persona。"""
    registry = _ensure_autoloaded()
    items = [PersonaListItem(**info.to_dict()) for info in registry.list_all()]
    return PersonaListOut(items=items, total=len(items))


@router.get("/{persona_id}", response_model=PersonaDetail)
async def get_persona(
    persona_id: str,
    _user: User = Depends(get_current_user_required),
) -> PersonaDetail:
    registry = _ensure_autoloaded()
    cls = registry.get_class(persona_id)
    if cls is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"persona 不存在: {persona_id}",
        )
    info = cls.get_info()
    excerpt = (cls.SYSTEM_PROMPT or "")[:600]
    return PersonaDetail(
        **info.to_dict(),
        system_prompt_excerpt=excerpt,
    )


@router.post("/{persona_id}/chat", response_model=ChatResponse)
async def chat_with_persona(
    persona_id: str,
    body: ChatRequest,
    user: User = Depends(get_current_user_required),
) -> ChatResponse:
    registry = _ensure_autoloaded()
    agent = registry.get(persona_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"persona 不存在或无法实例化: {persona_id}",
        )
    try:
        content = await agent.handle_message(
            message=body.message,
            user_id=str(user.id),
            history=body.history,
            extra=body.extra,
        )
    except Exception as exc:  # 屏蔽内部异常细节
        logger.exception("persona chat 失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"persona chat 失败: {exc}") from exc

    return ChatResponse(
        persona_id=persona_id,
        content=content,
        metadata={
            "capabilities": list(agent.capabilities),
            "display_name": agent.display_name,
        },
    )


# ---------------------------------------------------------------------------
# operations_manager 专用 endpoints（P7-A）
# ---------------------------------------------------------------------------

_OPS_PERSONA_ID = "operations_manager"


def _get_operations_agent():
    registry = _ensure_autoloaded()
    agent = registry.get(_OPS_PERSONA_ID)
    if agent is None:
        raise HTTPException(
            status_code=503,
            detail=f"流程管家 persona 未加载: {_OPS_PERSONA_ID}",
        )
    return agent


@router.post("/operations/okr/dashboard", response_model=OKRDashboardResponse)
async def operations_okr_dashboard(
    body: OKRDashboardRequest,
    user: User = Depends(get_current_user_required),
) -> OKRDashboardResponse:
    agent = _get_operations_agent()
    try:
        result = await agent.generate_okr_dashboard(
            period=body.period,
            team=body.team,
            user_id=str(user.id),
        )
    except Exception as exc:
        logger.exception("OKR 看板生成失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"OKR 看板生成失败: {exc}") from exc

    items = [OKRItemOut(**item) for item in result.get("items", []) if isinstance(item, dict)]
    return OKRDashboardResponse(
        period=result["period"],
        team=result.get("team"),
        markdown=result["markdown"],
        items=items,
        summary=result.get("summary", {}),
    )


@router.post("/operations/weekly-report", response_model=WeeklyReportResponse)
async def operations_weekly_report(
    body: WeeklyReportRequest,
    user: User = Depends(get_current_user_required),
) -> WeeklyReportResponse:
    agent = _get_operations_agent()
    try:
        result = await agent.generate_weekly_report(
            week_start=body.week_start,
            sources=body.sources,
            team=body.team,
            user_id=str(user.id),
        )
    except Exception as exc:
        logger.exception("周报生成失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"周报生成失败: {exc}") from exc

    return WeeklyReportResponse(**result)


@router.post("/operations/meeting-minutes", response_model=MeetingMinutesResponse)
async def operations_meeting_minutes(
    body: MeetingMinutesRequest,
    user: User = Depends(get_current_user_required),
) -> MeetingMinutesResponse:
    if not body.audio_url and not body.transcript:
        raise HTTPException(
            status_code=400,
            detail="必须提供 audio_url 或 transcript 之一",
        )
    agent = _get_operations_agent()
    try:
        result = await agent.transcribe_and_summarize(
            audio_url=body.audio_url,
            transcript=body.transcript,
            meeting_topic=body.meeting_topic,
            user_id=str(user.id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("会议纪要生成失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"会议纪要生成失败: {exc}") from exc

    todos = [TodoItemOut(**t) for t in result.get("todos", []) if isinstance(t, dict)]
    return MeetingMinutesResponse(
        status=result["status"],
        topic=result["topic"],
        transcript_excerpt=result.get("transcript_excerpt", ""),
        summary_markdown=result["summary_markdown"],
        decisions=result.get("decisions", []),
        todos=todos,
        audio_url=result.get("audio_url"),
    )


@router.post("/operations/extract-todos", response_model=ExtractTodosResponse)
async def operations_extract_todos(
    body: ExtractTodosRequest,
    user: User = Depends(get_current_user_required),
) -> ExtractTodosResponse:
    agent = _get_operations_agent()
    try:
        todos_raw = await agent.extract_todos(
            text=body.text,
            source=body.source,
            user_id=str(user.id),
        )
    except Exception as exc:
        logger.exception("待办提取失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"待办提取失败: {exc}") from exc

    todos = [TodoItemOut(**t) for t in todos_raw if isinstance(t, dict)]
    return ExtractTodosResponse(todos=todos, total=len(todos))
