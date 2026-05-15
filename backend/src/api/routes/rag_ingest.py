"""rag_ingest 路由（P13-A 多模态文档解析）。

挂载点（``api/routes/__init__.py`` 用 ``prefix="/rag/ingest"`` 注册）::

    POST  /api/v1/rag/ingest/multimodal       上传文件 → 异步入队 → 返回 task_id
    GET   /api/v1/rag/ingest/{task_id}        查询解析状态 + 结果

实现说明
========

异步层当前使用 ``BackgroundTasks`` + 进程内 ``_TASK_STORE``，方便单机
开发联调。真上 Celery 见 ``TODO(p13a-celery)``。

跨用户隔离暂不强约束（仅以 ``user_id`` 写入 metadata），等 P13-B 知识图谱
持久化时一并落到数据库。
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status

from src.api.routes.schemas.rag_ingest import (
    IngestResultOut,
    IngestTaskCreateOut,
    IngestTaskOut,
    IngestTaskStatus,
    ParsedSegmentOut,
)
from src.services.rag.ingest.multimodal import (
    IngestResult,
    MinerUIngestor,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# 进程内任务存储（mock）
# ---------------------------------------------------------------------------


class _TaskRecord:
    """单条任务记录（线程不安全，仅供单进程开发使用）。"""

    __slots__ = (
        "task_id",
        "status",
        "file_name",
        "doc_type",
        "created_at",
        "finished_at",
        "result",
        "error",
        "_user_id",
    )

    def __init__(
        self,
        *,
        task_id: str,
        file_name: str,
        doc_type: str,
        user_id: str | None,
    ) -> None:
        self.task_id = task_id
        self.status: IngestTaskStatus = IngestTaskStatus.PENDING
        self.file_name = file_name
        self.doc_type = doc_type
        self.created_at = datetime.now(UTC)
        self.finished_at: datetime | None = None
        self.result: IngestResult | None = None
        self.error: str | None = None
        self._user_id = user_id


_TASK_STORE: dict[str, _TaskRecord] = {}


def _new_task_id() -> str:
    return f"ingest-{uuid.uuid4().hex[:16]}"


# ---------------------------------------------------------------------------
# 序列化辅助
# ---------------------------------------------------------------------------


def _result_to_out(result: IngestResult) -> IngestResultOut:
    return IngestResultOut(
        document_id=result.document_id,
        segments=[
            ParsedSegmentOut(
                segment_id=seg.segment_id,
                modality=seg.modality,
                content=(
                    seg.content
                    if isinstance(seg.content, str)
                    else f"<bytes:{len(seg.content)}>"
                ),
                metadata=seg.metadata,
            )
            for seg in result.segments
        ],
        structure=result.structure,
        statistics=result.statistics,
        warnings=result.warnings,
    )


def _record_to_out(record: _TaskRecord) -> IngestTaskOut:
    return IngestTaskOut(
        task_id=record.task_id,
        status=record.status,
        file_name=record.file_name,
        doc_type=record.doc_type,
        created_at=record.created_at,
        finished_at=record.finished_at,
        result=_result_to_out(record.result) if record.result else None,
        error=record.error,
    )


# ---------------------------------------------------------------------------
# 后台任务执行
# ---------------------------------------------------------------------------


async def _run_ingest(task_id: str, file_path: Path, doc_type: str) -> None:
    """实际跑 MinerU。捕获所有异常落到 record.error。"""
    record = _TASK_STORE.get(task_id)
    if record is None:
        return
    record.status = IngestTaskStatus.RUNNING
    try:
        ingestor = MinerUIngestor()
        # TODO(p13a-celery): 改成 Celery 任务投递；当前直接 await。
        result = await ingestor.ingest(file_path, doc_type=doc_type)
        record.result = result
        record.status = IngestTaskStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001
        record.error = f"{type(exc).__name__}: {exc}"
        record.status = IngestTaskStatus.FAILED
    finally:
        record.finished_at = datetime.now(UTC)
        # 清理临时文件
        try:
            if file_path.exists():
                file_path.unlink(missing_ok=True)
        except OSError:
            pass


def _kickoff_background(
    background_tasks: BackgroundTasks | None,
    task_id: str,
    file_path: Path,
    doc_type: str,
) -> None:
    """统一调度入口（测试可手动 ``await _run_ingest`` 而不必 patch BackgroundTasks）。"""
    if background_tasks is not None:
        background_tasks.add_task(_run_ingest, task_id, file_path, doc_type)
    else:
        # 兜底：脱离 fastapi 调度（极少场景，比如脚本直跑）
        asyncio.get_event_loop().create_task(_run_ingest(task_id, file_path, doc_type))


# ---------------------------------------------------------------------------
# Endpoint：POST /multimodal
# ---------------------------------------------------------------------------


@router.post(
    "/multimodal",
    response_model=IngestTaskCreateOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_multimodal(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="待解析文件（PDF / 扫描图 / Office）"),
    doc_type: str = Form(default="auto", description="contract | scan | report | auto"),
    user_id: str | None = Form(default=None),
) -> IngestTaskCreateOut:
    """上传文件 → 写临时盘 → 入异步队列 → 返回 task_id。"""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="filename_required",
        )

    suffix = Path(file.filename).suffix or ""
    # 临时文件 NamedTemporaryFile（不删，由后台任务跑完清理）
    tmp = tempfile.NamedTemporaryFile(prefix="rag-ingest-", suffix=suffix, delete=False)
    try:
        chunk = await file.read()
        tmp.write(chunk)
    finally:
        tmp.close()
    tmp_path = Path(tmp.name)

    task_id = _new_task_id()
    record = _TaskRecord(
        task_id=task_id,
        file_name=file.filename,
        doc_type=doc_type,
        user_id=user_id,
    )
    _TASK_STORE[task_id] = record

    _kickoff_background(background_tasks, task_id, tmp_path, doc_type)

    return IngestTaskCreateOut(
        task_id=task_id,
        status=record.status,
        created_at=record.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoint：GET /{task_id}
# ---------------------------------------------------------------------------


@router.get("/{task_id}", response_model=IngestTaskOut)
async def get_task(task_id: str) -> IngestTaskOut:
    """查询解析任务状态 / 结果。"""
    record = _TASK_STORE.get(task_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="task_not_found",
        )
    return _record_to_out(record)


# ---------------------------------------------------------------------------
# 测试 / 内部使用钩子
# ---------------------------------------------------------------------------


def _reset_store_for_tests() -> None:
    """单测之间重置进程内 store。生产 / API 不暴露。"""
    _TASK_STORE.clear()


def _peek_record(task_id: str) -> _TaskRecord | None:
    """单测查看内部 record（不暴露给路由）。"""
    return _TASK_STORE.get(task_id)


def _build_test_app() -> Any:  # pragma: no cover
    """单测便捷：返回挂了 ``rag_ingest`` 的 FastAPI 实例。

    避开 v3/main 主 app 的预先存在 import 链断裂（fetch / app_authorization）。
    """
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/rag/ingest")
    return app
