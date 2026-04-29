# -*- coding: utf-8 -*-
"""fetch 路由 Pydantic schemas（请求 / 响应 DTO）。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, Field


class ExtractConfigIn(BaseModel):
    css_selectors: dict[str, str] = Field(default_factory=dict)
    xpath: dict[str, str] = Field(default_factory=dict)
    schema_: dict[str, Any] = Field(default_factory=dict, alias="schema")
    format: Literal["text", "markdown", "json", "html"] = "markdown"

    model_config = {"populate_by_name": True}


class FetchRequestIn(BaseModel):
    # AnyHttpUrl: pydantic 强类型，自动校验 scheme ∈ {http, https}
    # 进入 service 前再走 ssrf_guard.validate_url 做 IP/元数据/redirect 校验
    url: AnyHttpUrl
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    timeout: int = 30
    tier_hint: Literal[
        "L0_CACHE",
        "L1_HTTP",
        "L2_CRAWL4AI",
        "L3_HEADLESSX",
        "L4_OFFICIAL_API",
    ] | None = None
    extract: ExtractConfigIn | None = None
    bypass_cache: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)


class FetchBatchIn(BaseModel):
    requests: list[FetchRequestIn]
    concurrency: int = 5


class FetchResponseOut(BaseModel):
    url: str
    status_code: int
    tier_used: str
    duration_ms: int
    text: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    extracted: dict[str, Any] | None = None
    cached: bool = False
    error: str | None = None
    blocked_reason: str | None = None
    ok: bool


class AuditRecordOut(BaseModel):
    request_ts: str
    user_id: str | None
    url: str
    tier_used: str
    status_code: int
    duration_ms: int
    blocked_reason: str | None = None
    error: str | None = None


class AuditQueryOut(BaseModel):
    items: list[AuditRecordOut]
    total: int
    stats: dict[str, int]


class ComplianceCheckOut(BaseModel):
    url: str
    allowed: bool
    blocked: bool
    block_reason: dict[str, Any] | None
    tier_hint: str
