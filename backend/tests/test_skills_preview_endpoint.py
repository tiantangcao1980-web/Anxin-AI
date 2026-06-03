# -*- coding: utf-8 -*-
"""
POST /api/v1/skills/preview 单测

覆盖：
    - 非 .md 文件 → 400
    - 空文件 → 400
    - 非 UTF-8 → 400
    - 合法 SKILL.md（无 sandbox 块）→ 返回 manifest=T0 + fingerprint
    - 合法 SKILL.md（有 sandbox=T2）→ 返回 tier=T2 + entrypoint
    - 非法 sandbox manifest（如 T1 无签名）→ 400
    - 不注册到 registry（同名 skill 不会出现在后续 list 里）
"""

from __future__ import annotations

from io import BytesIO

import pytest

pytestmark = pytest.mark.asyncio


VALID_T0 = """---
name: preview-test-t0
description: 测试用 prompt-only skill
version: 1.0.0
---

# Body

只是 prompt 而已。
"""

VALID_T2 = """---
name: preview-test-t2
description: 测试用 code skill
version: 1.0.0
type: code
category: office
sandbox:
  tier: T2
  entrypoint: my_module:run
  runtime: python3.11
  resource_limits:
    timeout_sec: 30
---

正文略。
"""

INVALID_T1_NO_SIG = """---
name: preview-test-t1
description: T1 无签名应被拒绝
version: 1.0.0
sandbox:
  tier: T1
  entrypoint: m:f
---
正文略。
"""


def _upload(filename: str, content: bytes) -> dict:
    return {
        "file": (filename, BytesIO(content), "text/markdown"),
    }


async def test_rejects_non_md(auth_client) -> None:
    resp = await auth_client.post(
        "/api/v1/skills/preview",
        files=_upload("not_a_skill.txt", b"hi"),
    )
    assert resp.status_code == 400
    assert ".md" in resp.text


async def test_rejects_empty(auth_client) -> None:
    resp = await auth_client.post(
        "/api/v1/skills/preview",
        files=_upload("empty.md", b""),
    )
    assert resp.status_code == 400


async def test_rejects_non_utf8(auth_client) -> None:
    resp = await auth_client.post(
        "/api/v1/skills/preview",
        files=_upload("bad.md", b"\xff\xfe\xfd"),
    )
    assert resp.status_code == 400


async def test_preview_t0_returns_manifest_with_fingerprint(auth_client) -> None:
    resp = await auth_client.post(
        "/api/v1/skills/preview",
        files=_upload("preview-test-t0.md", VALID_T0.encode("utf-8")),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "preview-test-t0"
    assert body["version"] == "1.0.0"
    assert body["manifest"]["tier"] == "T0"
    assert body["manifest"]["entrypoint"] is None
    assert body["manifest"]["fingerprint"].startswith("sha256:")


async def test_preview_t2_returns_entrypoint(auth_client) -> None:
    resp = await auth_client.post(
        "/api/v1/skills/preview",
        files=_upload("preview-test-t2.md", VALID_T2.encode("utf-8")),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["manifest"]["tier"] == "T2"
    assert body["manifest"]["entrypoint"] == "my_module:run"
    assert body["manifest"]["resource_limits"]["timeout_sec"] == 30


async def test_preview_invalid_manifest_rejected(auth_client) -> None:
    """T1 没签名 → SkillLoader 不报错（loader 不做 manifest 校验），但
    /preview 内部调 SandboxManifest.from_frontmatter 会抛 ManifestValidationError。"""
    resp = await auth_client.post(
        "/api/v1/skills/preview",
        files=_upload("preview-test-t1.md", INVALID_T1_NO_SIG.encode("utf-8")),
    )
    assert resp.status_code == 400
    # 关键字命中即可
    body = resp.json()
    raw = str(body).lower()
    assert "manifest" in raw or "签名" in raw or "t1" in raw


async def test_preview_does_not_register(auth_client) -> None:
    """preview 不应把 skill 加进 registry。"""
    # 先 preview
    resp = await auth_client.post(
        "/api/v1/skills/preview",
        files=_upload("preview-test-t0.md", VALID_T0.encode("utf-8")),
    )
    assert resp.status_code == 200

    # 然后 list；preview-test-t0 不应该出现（除非别的测试 upload 过）
    list_resp = await auth_client.get("/api/v1/skills")
    assert list_resp.status_code == 200
    names = [s["name"] for s in list_resp.json()["items"]]
    assert "preview-test-t0" not in names
