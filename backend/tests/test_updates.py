import json

import pytest
from fastapi import HTTPException
from starlette.responses import Response

from src.api.routes import updates


@pytest.mark.asyncio
async def test_update_manifest_missing_returns_no_content_and_degraded(monkeypatch, tmp_path):
    monkeypatch.setattr(
        updates,
        "_DEFAULT_MANIFEST_PATH",
        str(tmp_path / "missing-updater-latest.json"),
    )

    response = await updates.check_update("darwin", "arm64", "0.1.0")
    assert isinstance(response, Response)
    assert response.status_code == 204

    latest = await updates.get_latest_release()
    assert latest == {"current_release": None, "platforms": {}}

    health = await updates.healthz()
    assert health["status"] == "degraded"
    assert health["has_manifest"] is False

    with pytest.raises(HTTPException) as exc:
        await updates.read_manifest()
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_manifest_serves_matching_platform_and_changelog(monkeypatch, tmp_path):
    manifest_path = tmp_path / "updater-latest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": "1.2.3",
                "notes": "Release notes",
                "pub_date": "2026-05-07T00:00:00Z",
                "min_version": "1.0.0",
                "platforms": {
                    "darwin-aarch64": {
                        "url": "https://cdn.example.com/app.tar.gz",
                        "signature": "sig",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(updates, "_DEFAULT_MANIFEST_PATH", str(manifest_path))

    update = await updates.check_update("darwin", "arm64", "1.2.2")
    assert isinstance(update, updates.UpdateManifest)
    assert update.version == "1.2.3"
    assert update.url == "https://cdn.example.com/app.tar.gz"

    no_update = await updates.check_update("darwin", "arm64", "1.2.3")
    assert isinstance(no_update, Response)
    assert no_update.status_code == 204

    latest = await updates.get_latest_release()
    assert latest["current_release"]["version"] == "1.2.3"
    assert latest["platforms"] == {"darwin-aarch64": {"url": "https://cdn.example.com/app.tar.gz"}}

    changelog = await updates.get_changelog(limit=10, offset=0)
    assert changelog["total"] == 1
    assert changelog["versions"][0]["version"] == "1.2.3"
