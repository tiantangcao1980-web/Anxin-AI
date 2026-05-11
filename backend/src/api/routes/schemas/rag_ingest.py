# -*- coding: utf-8 -*-
"""rag_ingest 路由 Pydantic schemas（P13-A）。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IngestTaskStatus(str, Enum):
    """异步任务状态。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ParsedSegmentOut(BaseModel):
    """单个 segment 的响应表示。"""

    segment_id: str
    modality: str = Field(..., description="text | image | table | formula | seal")
    content: str = Field(..., description="文本类直出；二进制以 <bytes:N> 占位")
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResultOut(BaseModel):
    """单文档解析结果。"""

    document_id: str
    segments: list[ParsedSegmentOut]
    structure: dict[str, Any]
    statistics: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


class IngestTaskCreateOut(BaseModel):
    """创建任务返回体。"""

    task_id: str
    status: IngestTaskStatus
    created_at: datetime


class IngestTaskOut(BaseModel):
    """任务查询返回体。"""

    task_id: str
    status: IngestTaskStatus
    file_name: str
    doc_type: str
    created_at: datetime
    finished_at: datetime | None = None
    result: IngestResultOut | None = None
    error: str | None = None
