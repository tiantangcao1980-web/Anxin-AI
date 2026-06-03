"""Object storage adapters for document and contract files."""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path, PurePosixPath
from typing import cast

import aiofiles  # type: ignore[import-untyped, unused-ignore]

from src.core.config import settings


class ObjectStorageError(RuntimeError):
    """Raised when object storage cannot safely complete an operation."""


@dataclass(frozen=True)
class StoredObject:
    backend: str
    bucket: str
    object_key: str
    size: int
    content_type: str | None = None


@dataclass(frozen=True)
class ListedObject:
    """对象列举结果：用于离线包 manifest 等需要遍历前缀的场景。"""

    object_key: str
    size: int


def _normalize_object_key(object_key: str) -> str:
    key = object_key.replace("\\", "/").lstrip("/")
    path = PurePosixPath(key)
    if not key or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ObjectStorageError(f"Invalid object key: {object_key!r}")
    return str(path)


class ObjectStorageService:
    backend = "base"

    async def put(
        self,
        object_key: str,
        content: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        raise NotImplementedError

    async def get(self, object_key: str) -> bytes:
        raise NotImplementedError

    async def delete(self, object_key: str) -> None:
        raise NotImplementedError

    async def exists(self, object_key: str) -> bool:
        raise NotImplementedError

    async def list(self, prefix: str) -> list[ListedObject]:
        """递归列出某前缀下的全部对象（不含目录条目），按 object_key 升序。"""
        raise NotImplementedError

    async def presigned_get_url(self, object_key: str, expires_seconds: int = 3600) -> str:
        raise NotImplementedError


class LocalObjectStorageService(ObjectStorageService):
    backend = "local"
    bucket = "local"

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or settings.STORAGE_LOCAL_PATH)

    def _resolve_path(self, object_key: str) -> Path:
        normalized = _normalize_object_key(object_key)
        root = self.root.resolve()
        target = (root / normalized).resolve()
        if target != root and root not in target.parents:
            raise ObjectStorageError(f"Object key escapes storage root: {object_key!r}")
        return target

    async def put(
        self,
        object_key: str,
        content: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        normalized = _normalize_object_key(object_key)
        path = self._resolve_path(normalized)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(content)
        return StoredObject(
            backend=self.backend,
            bucket=self.bucket,
            object_key=normalized,
            size=len(content),
            content_type=content_type,
        )

    async def get(self, object_key: str) -> bytes:
        path = self._resolve_path(object_key)
        try:
            async with aiofiles.open(path, "rb") as f:
                return cast(bytes, await f.read())
        except FileNotFoundError as exc:
            raise ObjectStorageError(f"Object not found: {object_key}") from exc

    async def delete(self, object_key: str) -> None:
        path = self._resolve_path(object_key)
        try:
            path.unlink()
        except FileNotFoundError:
            return

    async def exists(self, object_key: str) -> bool:
        return self._resolve_path(object_key).is_file()

    async def list(self, prefix: str) -> list[ListedObject]:
        base = self._resolve_path(prefix)

        def walk() -> list[ListedObject]:
            if not base.is_dir():
                # 兼容把 prefix 直接当作单个对象的情况
                if base.is_file():
                    return [ListedObject(object_key=_normalize_object_key(prefix), size=base.stat().st_size)]
                return []
            root = self.root.resolve()
            objects: list[ListedObject] = []
            for path in base.rglob("*"):
                if not path.is_file():
                    continue
                rel = path.resolve().relative_to(root)
                objects.append(
                    ListedObject(object_key=rel.as_posix(), size=path.stat().st_size)
                )
            objects.sort(key=lambda obj: obj.object_key)
            return objects

        return await asyncio.to_thread(walk)

    async def presigned_get_url(self, object_key: str, expires_seconds: int = 3600) -> str:
        normalized = _normalize_object_key(object_key)
        return f"local://{normalized}"


class MinioObjectStorageService(ObjectStorageService):
    backend = "minio"

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool | None = None,
    ):
        from minio import Minio

        self.bucket = bucket or settings.MINIO_BUCKET
        self.client = Minio(
            endpoint or settings.MINIO_ENDPOINT,
            access_key=access_key or settings.MINIO_ACCESS_KEY,
            secret_key=secret_key or settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL if secure is None else secure,
        )
        self._bucket_ready = False

    async def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return

        def ensure() -> None:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)

        await asyncio.to_thread(ensure)
        self._bucket_ready = True

    async def put(
        self,
        object_key: str,
        content: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        normalized = _normalize_object_key(object_key)
        await self._ensure_bucket()
        await asyncio.to_thread(
            self.client.put_object,
            self.bucket,
            normalized,
            io.BytesIO(content),
            len(content),
            content_type=content_type or "application/octet-stream",
        )
        return StoredObject(
            backend=self.backend,
            bucket=self.bucket,
            object_key=normalized,
            size=len(content),
            content_type=content_type,
        )

    async def get(self, object_key: str) -> bytes:
        normalized = _normalize_object_key(object_key)

        def read() -> bytes:
            response = self.client.get_object(self.bucket, normalized)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        try:
            return await asyncio.to_thread(read)
        except Exception as exc:
            raise ObjectStorageError(f"Object not found or unavailable: {object_key}") from exc

    async def delete(self, object_key: str) -> None:
        normalized = _normalize_object_key(object_key)
        await asyncio.to_thread(self.client.remove_object, self.bucket, normalized)

    async def exists(self, object_key: str) -> bool:
        normalized = _normalize_object_key(object_key)

        def stat() -> bool:
            try:
                self.client.stat_object(self.bucket, normalized)
                return True
            except Exception:
                return False

        return await asyncio.to_thread(stat)

    async def list(self, prefix: str) -> list[ListedObject]:
        normalized = _normalize_object_key(prefix)
        await self._ensure_bucket()

        def enumerate_objects() -> list[ListedObject]:
            objects: list[ListedObject] = []
            for obj in self.client.list_objects(
                self.bucket, prefix=normalized, recursive=True
            ):
                # 跳过以 "/" 结尾的目录占位对象
                name = obj.object_name
                if name is None or name.endswith("/"):
                    continue
                objects.append(ListedObject(object_key=name, size=obj.size or 0))
            objects.sort(key=lambda item: item.object_key)
            return objects

        return await asyncio.to_thread(enumerate_objects)

    async def presigned_get_url(self, object_key: str, expires_seconds: int = 3600) -> str:
        normalized = _normalize_object_key(object_key)
        return await asyncio.to_thread(
            self.client.presigned_get_object,
            self.bucket,
            normalized,
            expires=timedelta(seconds=expires_seconds),
        )


def get_object_storage(backend: str | None = None) -> ObjectStorageService:
    selected = (backend or settings.STORAGE_BACKEND).lower()
    if selected == "local":
        return LocalObjectStorageService()
    if selected in {"minio", "s3"}:
        return MinioObjectStorageService()
    raise ObjectStorageError(f"Unsupported storage backend: {selected}")
