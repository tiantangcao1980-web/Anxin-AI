# -*- coding: utf-8 -*-
"""
P5-A: skills 路由 API 测试

覆盖 6 个 endpoint：
    GET    /api/v1/skills
    GET    /api/v1/skills/triggers/match
    GET    /api/v1/skills/{name}
    POST   /api/v1/skills/upload
    PUT    /api/v1/skills/{name}/toggle
    POST   /api/v1/skills/{name}/execute

不依赖真 LLM —— execute 用 monkeypatch 把默认 ``_default_llm_call`` 换成 stub。
"""

from __future__ import annotations

# SQLite ↔ JSONB 兼容补丁（与其它 API 测试保持一致）
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler as _SQLiteTC

if not hasattr(_SQLiteTC, "visit_JSONB"):
    def _visit_JSONB(self, type_, **kw):  # noqa: N802
        return self.visit_JSON(type_, **kw)

    _SQLiteTC.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]


import textwrap

import pytest
import pytest_asyncio
from httpx import AsyncClient

from src.services.skill_registry import Skill, SkillRegistry


SKILL_CONTRACT = textwrap.dedent(
    """\
    ---
    name: contract-review
    description: 合同审查
    category: legal
    triggers:
      - 合同审查
      - 风险审核
    personas:
      - lawyer
    ---
    body
    """
)

SKILL_DOCS = textwrap.dedent(
    """\
    ---
    name: doc-summary
    description: 文档摘要
    category: office
    triggers:
      - 摘要
    ---
    body
    """
)


@pytest_asyncio.fixture(autouse=True)
async def _seed_registry(monkeypatch):
    """每个测试用全新的注册表，避免污染。"""
    SkillRegistry.reset_instance()
    reg = SkillRegistry.instance()
    reg.register(Skill(
        name="contract-review",
        description="合同审查",
        category="legal",
        triggers=["合同审查", "风险审核"],
        personas=["lawyer"],
        body="body A",
    ))
    reg.register(Skill(
        name="doc-summary",
        description="文档摘要",
        category="office",
        triggers=["摘要"],
        body="body B",
    ))
    yield
    SkillRegistry.reset_instance()


# ---------------------------------------------------------------------------
# GET /skills
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_skills_returns_all(auth_client: AsyncClient) -> None:
    r = await auth_client.get("/api/v1/skills")
    assert r.status_code == 200
    data = r.json()
    names = sorted(s["name"] for s in data["items"])
    assert names == ["contract-review", "doc-summary"]
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_list_skills_filter_category(auth_client: AsyncClient) -> None:
    r = await auth_client.get("/api/v1/skills", params={"category": "legal"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert [s["name"] for s in items] == ["contract-review"]


@pytest.mark.asyncio
async def test_list_skills_filter_persona(auth_client: AsyncClient) -> None:
    r = await auth_client.get("/api/v1/skills", params={"persona": "lawyer"})
    assert r.status_code == 200
    names = sorted(s["name"] for s in r.json()["items"])
    # doc-summary 没有 personas → 全员可用；lawyer 都看得到
    assert names == ["contract-review", "doc-summary"]


# ---------------------------------------------------------------------------
# GET /skills/triggers/match
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_match_triggers(auth_client: AsyncClient) -> None:
    r = await auth_client.get(
        "/api/v1/skills/triggers/match",
        params={"q": "请帮我做合同审查 + 摘要", "top_k": 5},
    )
    assert r.status_code == 200
    items = r.json()["items"]
    names = [s["name"] for s in items]
    assert "contract-review" in names
    assert "doc-summary" in names


# ---------------------------------------------------------------------------
# GET /skills/{name}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_skill_detail(auth_client: AsyncClient) -> None:
    r = await auth_client.get("/api/v1/skills/contract-review")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "contract-review"
    assert data["body_length"] > 0
    assert "body" in data["body_excerpt"] or data["body_excerpt"] == "body A"


@pytest.mark.asyncio
async def test_get_skill_detail_404(auth_client: AsyncClient) -> None:
    r = await auth_client.get("/api/v1/skills/nope")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /skills/upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_skill_md(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        "/api/v1/skills/upload",
        files={"file": ("uploaded.md", SKILL_CONTRACT, "text/markdown")},
    )
    # contract-review 已经存在，会被覆盖；状态 201
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["name"] == "contract-review"
    assert SkillRegistry.instance().get("contract-review") is not None


@pytest.mark.asyncio
async def test_upload_skill_md_rejects_non_md(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        "/api/v1/skills/upload",
        files={"file": ("bad.txt", b"hi", "text/plain")},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_upload_skill_md_rejects_invalid_yaml(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        "/api/v1/skills/upload",
        files={"file": ("bad.md", b"no frontmatter at all", "text/markdown")},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# PUT /skills/{name}/toggle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_toggle_skill(auth_client: AsyncClient) -> None:
    r = await auth_client.put(
        "/api/v1/skills/contract-review/toggle",
        json={"enabled": False},
    )
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    assert SkillRegistry.instance().get("contract-review").enabled is False


@pytest.mark.asyncio
async def test_toggle_skill_404(auth_client: AsyncClient) -> None:
    r = await auth_client.put(
        "/api/v1/skills/nope/toggle",
        json={"enabled": True},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /skills/{name}/execute
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_skill_with_stub_llm(
    auth_client: AsyncClient, monkeypatch
) -> None:
    """patch 默认 LLM callable，确保 execute 不依赖外部服务。"""
    from src.services import skill_executor as se_module
    from src.services.skill_executor import executor as exec_module

    def stub(system: str, user: str) -> str:
        return f"echo: {len(system)}+{len(user)}"

    monkeypatch.setattr(exec_module, "_default_llm_call", stub)

    r = await auth_client.post(
        "/api/v1/skills/contract-review/execute",
        json={"payload": {"q": "你好"}, "persona": "lawyer"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "success"
    assert data["output"].startswith("echo:")
    assert data["skill_name"] == "contract-review"


@pytest.mark.asyncio
async def test_execute_skill_404(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        "/api/v1/skills/nope/execute",
        json={"payload": {}},
    )
    assert r.status_code == 404
