# -*- coding: utf-8 -*-
"""personas 路由 Pydantic schemas（V3 user-facing persona API DTO）。"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============ 通用 ============

class PersonaListItem(BaseModel):
    """persona 列表项（只暴露元信息）。"""

    persona_id: str
    display_name: str
    emoji: str = "🤖"
    description: str = ""
    capabilities: List[str] = Field(default_factory=list)
    backed_by_skills: List[str] = Field(default_factory=list)
    supported_apps: List[str] = Field(default_factory=list)
    enabled: bool = True


class PersonaDetail(PersonaListItem):
    """persona 详情（含后端 agent 列表 + 系统 prompt 摘要）。"""

    backed_by_agents: List[str] = Field(default_factory=list)
    system_prompt_excerpt: str = ""


class PersonaListOut(BaseModel):
    items: List[PersonaListItem]
    total: int


# ============ chat ============

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    persona_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============ operations_manager 专用 ============

class OKRDashboardRequest(BaseModel):
    period: str = Field(..., description="例如 Q2-2026 / 2026-04 / 本季度")
    team: Optional[str] = None


class OKRItemOut(BaseModel):
    objective: str
    owner: str = ""
    progress: float = 0.0
    status: str = "on_track"
    key_results: List[Dict[str, Any]] = Field(default_factory=list)


class OKRDashboardResponse(BaseModel):
    period: str
    team: Optional[str] = None
    markdown: str
    items: List[OKRItemOut]
    summary: Dict[str, int] = Field(default_factory=dict)


class WeeklyReportRequest(BaseModel):
    week_start: date = Field(..., description="周一日期")
    sources: List[str] = Field(default_factory=lambda: ["飞书", "钉钉", "日历"])
    team: Optional[str] = None


class WeeklyReportResponse(BaseModel):
    week_start: str
    week_end: str
    team: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    markdown: str
    sections: Dict[str, List[str]] = Field(default_factory=dict)


class MeetingMinutesRequest(BaseModel):
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    meeting_topic: Optional[str] = None


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
    decisions: List[str] = Field(default_factory=list)
    todos: List[TodoItemOut] = Field(default_factory=list)
    audio_url: Optional[str] = None


class ExtractTodosRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    source: str = "free_text"


class ExtractTodosResponse(BaseModel):
    todos: List[TodoItemOut]
    total: int
