"""personas 路由 Pydantic schemas（V3 user-facing persona API DTO）。"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

# ============ 通用 ============

class PersonaListItem(BaseModel):
    """persona 列表项（只暴露元信息）。"""

    persona_id: str
    display_name: str
    emoji: str = "🤖"
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    backed_by_skills: list[str] = Field(default_factory=list)
    supported_apps: list[str] = Field(default_factory=list)
    enabled: bool = True


class PersonaDetail(PersonaListItem):
    """persona 详情（含后端 agent 列表 + 系统 prompt 摘要）。"""

    backed_by_agents: list[str] = Field(default_factory=list)
    system_prompt_excerpt: str = ""


class PersonaListOut(BaseModel):
    items: list[PersonaListItem]
    total: int


# ============ chat ============

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    history: list[dict[str, Any]] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    persona_id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============ operations_manager 专用 ============

class OKRDashboardRequest(BaseModel):
    period: str = Field(..., description="例如 Q2-2026 / 2026-04 / 本季度")
    team: str | None = None


class OKRItemOut(BaseModel):
    objective: str
    owner: str = ""
    progress: float = 0.0
    status: str = "on_track"
    key_results: list[dict[str, Any]] = Field(default_factory=list)


class OKRDashboardResponse(BaseModel):
    period: str
    team: str | None = None
    markdown: str
    items: list[OKRItemOut]
    summary: dict[str, int] = Field(default_factory=dict)


class WeeklyReportRequest(BaseModel):
    week_start: date = Field(..., description="周一日期")
    sources: list[str] = Field(default_factory=lambda: ["飞书", "钉钉", "日历"])
    team: str | None = None


class WeeklyReportResponse(BaseModel):
    week_start: str
    week_end: str
    team: str | None = None
    sources: list[str] = Field(default_factory=list)
    markdown: str
    sections: dict[str, list[str]] = Field(default_factory=dict)


class MeetingMinutesRequest(BaseModel):
    audio_url: str | None = None
    transcript: str | None = None
    meeting_topic: str | None = None


class TodoItemOut(BaseModel):
    task: str
    owner: str = "?"
    due_date: str = "?"
    priority: str = "P2"
    source: str = ""


class MeetingMinutesResponse(BaseModel):
    status: str
    topic: str
    transcript_excerpt: str = ""
    summary_markdown: str
    decisions: list[str] = Field(default_factory=list)
    todos: list[TodoItemOut] = Field(default_factory=list)
    audio_url: str | None = None


class ExtractTodosRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    source: str = "free_text"


class ExtractTodosResponse(BaseModel):
    todos: list[TodoItemOut]
    total: int
