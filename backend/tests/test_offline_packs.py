from pathlib import Path

import pytest
from fastapi import HTTPException

from src.api.routes import offline_packs


@pytest.mark.asyncio
async def test_builtin_offline_pack_catalog_manifest_and_health(monkeypatch):
    monkeypatch.setattr(
        offline_packs,
        "_DEFAULT_PACKS_FILE",
        str(Path("/tmp/anxin-offline-packs-does-not-exist.json")),
    )

    listing = await offline_packs.list_packs(kind=None)
    assert listing["total"] == 3
    assert [pack.id for pack in listing["items"]] == [
        "regulation-core-v1",
        "regulation-full-v1",
        "template-pack-v1",
    ]

    pack = await offline_packs.get_pack("regulation-core-v1")
    assert pack.kind == "regulation_core"

    manifest = await offline_packs.get_manifest("regulation-core-v1")
    assert manifest.id == pack.id
    assert manifest.version == pack.version
    assert manifest.files == []

    health = await offline_packs.healthz()
    assert health["status"] == "degraded"
    assert health["configured_packs"] == 0


@pytest.mark.asyncio
async def test_builtin_offline_pack_download_requires_ops_url(monkeypatch):
    monkeypatch.setattr(
        offline_packs,
        "_DEFAULT_PACKS_FILE",
        str(Path("/tmp/anxin-offline-packs-does-not-exist.json")),
    )

    with pytest.raises(HTTPException) as exc:
        await offline_packs.download_pack("regulation-core-v1")

    assert exc.value.status_code == 503
