"""skills 路由 Pydantic schemas（请求 / 响应 DTO）。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SkillSummaryOut(BaseModel):
    """技能摘要（列表用，不含 body）。"""

    name: str
    description: str
    version: str = "0.0.0"
    category: str = "general"
    type: str = "general"
    triggers: list[str] = Field(default_factory=list)
    personas: list[str] = Field(default_factory=list)
    requires_apps: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    enabled: bool = True
    author: str | None = None
    file_path: str | None = None


class SkillListOut(BaseModel):
    items: list[SkillSummaryOut]
    total: int


class SkillDetailOut(SkillSummaryOut):
    """技能详情（含 body 摘要 + 长度）。"""

    body_excerpt: str = ""
    body_length: int = 0


class ToggleSkillBody(BaseModel):
    enabled: bool


class ExecuteSkillBody(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    persona: str | None = None
    app_authorizations: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class ExecuteSkillOut(BaseModel):
    skill_name: str
    status: str
    output: str = ""
    error: str | None = None
    duration_ms: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class TriggerMatchOut(BaseModel):
    items: list[SkillSummaryOut]
    total: int


class UploadSkillOut(BaseModel):
    name: str
    saved_path: str
    errors: list[str] = Field(default_factory=list)
    skill: SkillSummaryOut
