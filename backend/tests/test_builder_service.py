# -*- coding: utf-8 -*-
"""
Builder Service 单元测试 — CREAO Slice 3 (A9, 2026-05-14)

覆盖:
1. test_regression_test_draft_contains_skip   — 草稿默认含 pytest.skip
2. test_regression_function_name_safe         — 函数名安全 (snake_case, 无特殊字符)
3. test_github_issue_draft_includes_metadata  — Issue body 含 severity / fingerprint / payload
4. test_build_drafts_for_unknown_incident     — 找不到 incident 时返回 error
5. test_build_drafts_returns_both             — 同时返回 regression + github_issue
6. test_link_github_issue_updates_status      — link 后 status 推进到 linked
7. test_link_unknown_incident                 — 找不到时返回 ok=False
"""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.harness.builder_service import (
    build_drafts_for_incident,
    build_github_issue_draft,
    build_regression_test_draft,
    link_github_issue,
)
from src.models.incident import Incident


@pytest_asyncio.fixture(autouse=True)
async def _clean(db_session: AsyncSession):
    await db_session.execute(sa_delete(Incident))
    await db_session.commit()
    yield
    await db_session.execute(sa_delete(Incident))
    await db_session.commit()


def _make_incident(**kwargs) -> Incident:
    now = datetime.now(timezone.utc)
    defaults = {
        "source": "output_validator",
        "severity": "P1",
        "fingerprint": "fp_a9",
        "title": "测试失败摘要",
        "payload": {"missing_field": "user_query", "agent": "x"},
        "agent_name": "legal_advisor",
        "route": "/api/v1/chat",
        "status": "triaged",
        "occurrence_count": 3,
        "first_seen_at": now,
        "last_seen_at": now,
        "triage_summary": "[P1] output_validator agent=legal_advisor route=/api/v1/chat",
    }
    defaults.update(kwargs)
    return Incident(**defaults)


def test_regression_test_draft_contains_skip():
    inc = _make_incident()
    draft = build_regression_test_draft(inc)
    assert "pytest.skip" in draft
    assert "CREAO Slice 3" in draft
    assert "TODO" in draft  # 提示人工补全
    assert "@pytest.mark.regression" in draft
    assert "@pytest.mark.creao_slice3" in draft


def test_regression_function_name_safe():
    inc = _make_incident(source="api_5xx", agent_name="法律顾问 + 特殊@字符")
    draft = build_regression_test_draft(inc)
    # 函数名应是 snake_case, 不含空格 / @ / 等
    import re
    m = re.search(r"def (test_\w+)\(\):", draft)
    assert m
    fn_name = m.group(1)
    assert " " not in fn_name
    assert "@" not in fn_name


def test_github_issue_draft_includes_metadata():
    inc = _make_incident(severity="P0", fingerprint="abc123def456")
    draft = build_github_issue_draft(inc)
    assert draft["title"].startswith("[CREAO][P0]")
    body = draft["body"]
    assert "P0" in body
    assert "abc123def456" in body
    assert "missing_field" in body  # payload 内容
    assert "anxin-ai/anxin-assistant" in body


@pytest.mark.asyncio
async def test_build_drafts_for_unknown_incident(db_session: AsyncSession):
    """传入合法格式但不存在的 UUID → 返回 not found error。"""
    import uuid as _u
    fake_id = str(_u.uuid4())
    result = await build_drafts_for_incident(db_session, incident_id=fake_id)
    assert "error" in result
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_build_drafts_for_invalid_id_format(db_session: AsyncSession):
    """传入非法格式 (非 UUID) → 返回 invalid error, 不抛异常。"""
    result = await build_drafts_for_incident(db_session, incident_id="not_a_uuid_at_all")
    assert "error" in result
    assert "invalid" in result["error"].lower() or "not found" in result["error"]


@pytest.mark.asyncio
async def test_build_drafts_returns_both(db_session: AsyncSession):
    inc = _make_incident()
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    result = await build_drafts_for_incident(db_session, incident_id=inc.id)
    assert "regression_test_draft" in result
    assert "github_issue_draft" in result
    assert result["severity"] == "P1"
    assert result["source"] == "output_validator"
    assert "pytest.skip" in result["regression_test_draft"]
    assert "[CREAO][P1]" in result["github_issue_draft"]["title"]


@pytest.mark.asyncio
async def test_link_github_issue_updates_status(db_session: AsyncSession):
    inc = _make_incident(status="triaged")
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    url = "https://github.com/anxin-ai/anxin-assistant/issues/999"
    result = await link_github_issue(db_session, inc.id, url)
    await db_session.commit()
    await db_session.refresh(inc)
    assert result["ok"] is True
    assert result["status"] == "linked"
    assert inc.github_issue_url == url
    assert inc.status == "linked"


@pytest.mark.asyncio
async def test_link_unknown_incident(db_session: AsyncSession):
    """合法 UUID 但找不到 → ok=False + not found。"""
    import uuid as _u
    fake_id = str(_u.uuid4())
    result = await link_github_issue(db_session, fake_id, "https://x/y/z")
    assert result["ok"] is False
    assert "not found" in result.get("error", "")
