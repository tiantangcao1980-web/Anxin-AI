# -*- coding: utf-8 -*-
"""
P7-A: personas API 路由测试

mock OperationsManagerAgent 的方法，验证：
    - GET    /api/v1/personas                 列表
    - GET    /api/v1/personas/{id}            详情
    - POST   /api/v1/personas/{id}/chat       通用 chat
    - POST   /api/v1/personas/operations/okr/dashboard
    - POST   /api/v1/personas/operations/weekly-report
    - POST   /api/v1/personas/operations/meeting-minutes
    - POST   /api/v1/personas/operations/extract-todos
"""

from __future__ import annotations

# SQLite ↔ JSONB 兼容补丁（必须在 import models 前生效）
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler as _SQLiteTC

if not hasattr(_SQLiteTC, "visit_JSONB"):
    def _visit_JSONB(self, type_, **kw):  # noqa: N802
        return self.visit_JSON(type_, **kw)

    _SQLiteTC.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]


from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.agents.personas import PersonaRegistry


@pytest.fixture(autouse=True)
def _reset_persona_registry():
    PersonaRegistry.reset_instance()
    yield
    PersonaRegistry.reset_instance()


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def _patch_chat(content: str = "ok"):
    """patch OperationsManagerAgent.chat 避免真正请求 LLM。"""
    return patch(
        "src.agents.personas.operations_manager.OperationsManagerAgent.chat",
        new=AsyncMock(return_value=content),
    )


def _patch_llm_init():
    """避免实例化时跑真实 LLM 配置查询。"""
    return patch("src.agents.base.get_llm_config_sync", return_value=None)


# ------------------------------------------------------------------
class TestPersonaListAndDetail:
    @pytest.mark.asyncio
    async def test_list_personas_returns_operations_manager(
        self, auth_client: AsyncClient
    ):
        with _patch_llm_init():
            r = await auth_client.get("/api/v1/personas")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total"] >= 1
        ids = [item["persona_id"] for item in data["items"]]
        assert "operations_manager" in ids

        ops = next(i for i in data["items"] if i["persona_id"] == "operations_manager")
        assert ops["display_name"] == "流程管家"
        assert ops["emoji"] == "📋"
        assert "okr_tracking" in ops["capabilities"]
        assert "docx" in ops["backed_by_skills"]

    @pytest.mark.asyncio
    async def test_get_persona_detail(self, auth_client: AsyncClient):
        with _patch_llm_init():
            r = await auth_client.get("/api/v1/personas/operations_manager")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["persona_id"] == "operations_manager"
        assert data["display_name"] == "流程管家"
        assert data["system_prompt_excerpt"]
        assert "operations_manager" in data["system_prompt_excerpt"] or "流程管家" in data["system_prompt_excerpt"]

    @pytest.mark.asyncio
    async def test_get_persona_404(self, auth_client: AsyncClient):
        with _patch_llm_init():
            r = await auth_client.get("/api/v1/personas/nonexistent")
        assert r.status_code == 404


# ------------------------------------------------------------------
class TestPersonaChat:
    @pytest.mark.asyncio
    async def test_chat_with_persona(self, auth_client: AsyncClient):
        with _patch_llm_init(), _patch_chat("hello from operations_manager"):
            r = await auth_client.post(
                "/api/v1/personas/operations_manager/chat",
                json={"message": "你好", "history": [], "extra": {}},
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["persona_id"] == "operations_manager"
        assert data["content"] == "hello from operations_manager"
        assert "okr_tracking" in data["metadata"]["capabilities"]

    @pytest.mark.asyncio
    async def test_chat_unknown_persona_404(self, auth_client: AsyncClient):
        with _patch_llm_init():
            r = await auth_client.post(
                "/api/v1/personas/unknown_persona/chat",
                json={"message": "hi"},
            )
        assert r.status_code == 404


# ------------------------------------------------------------------
class TestOperationsEndpoints:
    @pytest.mark.asyncio
    async def test_okr_dashboard(self, auth_client: AsyncClient):
        fake_resp = (
            "## OKR 看板\n"
            "```json\n"
            '{"items":[{"objective":"提升合格率","owner":"李雷","progress":0.6,'
            '"status":"on_track","key_results":[]}],'
            '"summary":{"total":1,"on_track":1,"at_risk":0,"off_track":0}}\n'
            "```\n"
        )
        with _patch_llm_init(), _patch_chat(fake_resp):
            r = await auth_client.post(
                "/api/v1/personas/operations/okr/dashboard",
                json={"period": "Q2-2026", "team": "生产部"},
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["period"] == "Q2-2026"
        assert data["team"] == "生产部"
        assert len(data["items"]) == 1
        assert data["items"][0]["objective"] == "提升合格率"
        assert data["summary"]["total"] == 1

    @pytest.mark.asyncio
    async def test_weekly_report(self, auth_client: AsyncClient):
        fake_resp = (
            "## 本周亮点\n- 完成评审\n\n"
            "```json\n"
            '{"highlights":["完成评审"],"risks":[],"next_week":["启动测试"]}\n'
            "```\n"
        )
        with _patch_llm_init(), _patch_chat(fake_resp):
            r = await auth_client.post(
                "/api/v1/personas/operations/weekly-report",
                json={
                    "week_start": "2026-04-20",
                    "sources": ["飞书", "钉钉"],
                    "team": "研发组",
                },
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["week_start"] == "2026-04-20"
        assert data["week_end"] == "2026-04-26"
        assert data["sections"]["highlights"] == ["完成评审"]
        assert data["sections"]["next_week"] == ["启动测试"]

    @pytest.mark.asyncio
    async def test_meeting_minutes_with_transcript(self, auth_client: AsyncClient):
        fake_resp = (
            "## 决议\n通过改版\n\n"
            "```json\n"
            '{"decisions":["通过改版"],'
            '"todos":[{"task":"完成改版","owner":"王伟","due_date":"2026-05-15","priority":"P1"}]}\n'
            "```\n"
        )
        with _patch_llm_init(), _patch_chat(fake_resp):
            r = await auth_client.post(
                "/api/v1/personas/operations/meeting-minutes",
                json={
                    "transcript": "完整会议转写文本...",
                    "meeting_topic": "V3.2 评审",
                },
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "ready"
        assert data["topic"] == "V3.2 评审"
        assert data["decisions"] == ["通过改版"]
        assert len(data["todos"]) == 1
        assert data["todos"][0]["owner"] == "王伟"

    @pytest.mark.asyncio
    async def test_meeting_minutes_pending_when_audio_only(self, auth_client: AsyncClient):
        with _patch_llm_init(), _patch_chat("不应被调用"):
            r = await auth_client.post(
                "/api/v1/personas/operations/meeting-minutes",
                json={
                    "audio_url": "https://example.com/audio.mp3",
                    "meeting_topic": "周一晨会",
                },
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "pending_transcribe"
        assert data["audio_url"] == "https://example.com/audio.mp3"

    @pytest.mark.asyncio
    async def test_meeting_minutes_400_when_neither(self, auth_client: AsyncClient):
        with _patch_llm_init():
            r = await auth_client.post(
                "/api/v1/personas/operations/meeting-minutes",
                json={"meeting_topic": "x"},
            )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_extract_todos(self, auth_client: AsyncClient):
        fake_resp = (
            "```json\n"
            '{"todos":[{"task":"准备拜访","owner":"张三","due_date":"2026-04-30","priority":"P0"}]}\n'
            "```\n"
        )
        with _patch_llm_init(), _patch_chat(fake_resp):
            r = await auth_client.post(
                "/api/v1/personas/operations/extract-todos",
                json={"text": "周一前张三去拜访客户。", "source": "im_chat"},
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total"] == 1
        assert data["todos"][0]["owner"] == "张三"
        assert data["todos"][0]["source"] == "im_chat"


# ------------------------------------------------------------------
class TestAuthRequired:
    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        r = await client.get("/api/v1/personas")
        assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_chat_requires_auth(self, client: AsyncClient):
        r = await client.post(
            "/api/v1/personas/operations_manager/chat",
            json={"message": "hi"},
        )
        assert r.status_code in (401, 403)
