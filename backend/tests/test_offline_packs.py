import hashlib
from pathlib import Path

import pytest
from fastapi import HTTPException

from src.api.routes import offline_packs
from src.services.object_storage_service import (
    LocalObjectStorageService,
    ObjectStorageError,
    ObjectStorageService,
)


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


# ============================================================================
# manifest 生成：从对象存储列文件 + 逐个算 sha256
# ============================================================================


async def _seed_pack_objects(
    storage: LocalObjectStorageService, pack_id: str, files: dict[str, bytes]
) -> None:
    prefix = offline_packs._pack_object_prefix(pack_id)
    for rel_path, content in files.items():
        await storage.put(f"{prefix}/{rel_path}", content)


@pytest.mark.asyncio
async def test_local_object_storage_list_recurses_and_sorts(tmp_path: Path):
    storage = LocalObjectStorageService(tmp_path)
    await storage.put("offline-packs/p1/b.txt", b"bb")
    await storage.put("offline-packs/p1/sub/a.txt", b"aaa")
    await storage.put("offline-packs/p2/other.txt", b"x")

    listed = await storage.list("offline-packs/p1")

    assert [obj.object_key for obj in listed] == [
        "offline-packs/p1/b.txt",
        "offline-packs/p1/sub/a.txt",
    ]
    assert {obj.size for obj in listed} == {2, 3}


@pytest.mark.asyncio
async def test_local_object_storage_list_missing_prefix_returns_empty(tmp_path: Path):
    storage = LocalObjectStorageService(tmp_path)
    assert await storage.list("offline-packs/nope") == []


@pytest.mark.asyncio
async def test_build_manifest_lists_files_and_computes_sha256(tmp_path: Path):
    storage = LocalObjectStorageService(tmp_path)
    pack = offline_packs._built_in_packs()[0]  # regulation-core-v1
    files = {
        "index.json": b'{"v":1}',
        "laws/constitution.md": b"# Constitution\n",
        "laws/civil_code.md": b"# Civil Code\n",
    }
    await _seed_pack_objects(storage, pack.id, files)

    manifest = await offline_packs._build_manifest(pack, storage)

    assert manifest.id == pack.id
    assert manifest.version == pack.version
    # path 为相对包目录的路径，按 object_key 升序
    assert [f.path for f in manifest.files] == [
        "index.json",
        "laws/civil_code.md",
        "laws/constitution.md",
    ]
    expected = {
        rel: hashlib.sha256(content).hexdigest() for rel, content in files.items()
    }
    for f in manifest.files:
        assert f.sha256 == expected[f.path]
        assert f.size_bytes == len(files[f.path])
    assert manifest.total_size == sum(len(c) for c in files.values())


@pytest.mark.asyncio
async def test_build_manifest_empty_pack_falls_back_to_declared_size(tmp_path: Path):
    storage = LocalObjectStorageService(tmp_path)
    pack = offline_packs._built_in_packs()[0]

    manifest = await offline_packs._build_manifest(pack, storage)

    assert manifest.files == []
    assert manifest.total_size == pack.size_bytes


@pytest.mark.asyncio
async def test_get_manifest_route_uses_storage_abstraction(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        offline_packs,
        "_DEFAULT_PACKS_FILE",
        str(Path("/tmp/anxin-offline-packs-does-not-exist.json")),
    )
    storage = LocalObjectStorageService(tmp_path)
    await _seed_pack_objects(
        storage, "regulation-core-v1", {"index.json": b'{"v":1}'}
    )
    monkeypatch.setattr(offline_packs, "get_object_storage", lambda: storage)

    manifest = await offline_packs.get_manifest("regulation-core-v1")

    assert [f.path for f in manifest.files] == ["index.json"]
    assert manifest.files[0].sha256 == hashlib.sha256(b'{"v":1}').hexdigest()
    assert manifest.total_size == len(b'{"v":1}')


@pytest.mark.asyncio
async def test_get_manifest_route_unknown_pack_404(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        offline_packs,
        "_DEFAULT_PACKS_FILE",
        str(Path("/tmp/anxin-offline-packs-does-not-exist.json")),
    )
    monkeypatch.setattr(
        offline_packs, "get_object_storage", lambda: LocalObjectStorageService(tmp_path)
    )

    with pytest.raises(HTTPException) as exc:
        await offline_packs.get_manifest("does-not-exist")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_manifest_route_storage_unavailable_returns_503(monkeypatch):
    monkeypatch.setattr(
        offline_packs,
        "_DEFAULT_PACKS_FILE",
        str(Path("/tmp/anxin-offline-packs-does-not-exist.json")),
    )

    class _BrokenStorage(ObjectStorageService):
        backend = "broken"

        async def list(self, prefix: str):  # type: ignore[override]
            raise ObjectStorageError("minio unreachable")

    monkeypatch.setattr(offline_packs, "get_object_storage", lambda: _BrokenStorage())

    with pytest.raises(HTTPException) as exc:
        await offline_packs.get_manifest("regulation-core-v1")

    assert exc.value.status_code == 503
