# -*- coding: utf-8 -*-
"""
Incident Pydantic schemas — CREAO 自愈闭环 Slice 1

供前端上报、API 列表 / 详情查询、跨 Agent 内部 collect 调用使用。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============ 枚举 ============

class IncidentSource(str, Enum):
    OUTPUT_VALIDATOR = "output_validator"
    AGENT_FORUM = "agent_forum"
    LOW_RATING = "low_rating"
    API_5XX = "api_5xx"
    FRONTEND_ERROR = "frontend_error"


class IncidentSeverity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class IncidentStatus(str, Enum):
    OPEN = "open"
    TRIAGED = "triaged"
    LINKED = "linked"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# ============ 响应 ============

class IncidentRead(BaseModel):
    """对外读模型，含全部字段。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source: IncidentSource
    severity: IncidentSeverity
    fingerprint: str
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_classification: str = "CONFIDENTIAL"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    agent_name: Optional[str] = None
    route: Optional[str] = None
    status: IncidentStatus
    occurrence_count: int = 1
    first_seen_at: datetime
    last_seen_at: datetime
    triage_summary: Optional[str] = None
    github_issue_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============ 前端上报 ============

class IncidentReportIn(BaseModel):
    """
    浏览器侧主动上报（window.onerror / unhandledrejection / React ErrorBoundary）。
    source 固定为 frontend_error；后端在 collector 里强制覆盖以防伪造。
    """

    model_config = ConfigDict(extra="ignore")

    source: IncidentSource = IncidentSource.FRONTEND_ERROR
    title: str = Field(..., min_length=1, max_length=256)
    message: Optional[str] = Field(None, max_length=4096)
    stack: Optional[str] = Field(None, max_length=16384)
    url: Optional[str] = Field(None, max_length=1024)
    user_agent: Optional[str] = Field(None, max_length=512)
    session_id: Optional[str] = Field(None, max_length=64)


# ============ 列表查询 ============

class IncidentListQuery(BaseModel):
    """GET /incidents 的 query 参数。"""

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=200)
    source: Optional[IncidentSource] = None
    severity: Optional[IncidentSeverity] = None
    status: Optional[IncidentStatus] = None
