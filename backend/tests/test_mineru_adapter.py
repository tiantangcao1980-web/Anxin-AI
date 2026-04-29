# -*- coding: utf-8 -*-
"""MinerU 适配器单测（P13-A）。

覆盖：

- ``supports`` 扩展名判断
- 不存在文件 → warnings
- PDF 默认 → 合同 mock（含 chapter / clause / table / seal）
- 扫描图（.png / .jpg） → image + OCR text + seal
- Excel → table + formula
- statistics 含 modality_counts、elapsed_ms、page_count
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.rag.ingest.multimodal import MinerUIngestor
from src.services.rag.ingest.multimodal.base import IngestResult, Modality


@pytest.fixture
def adapter() -> MinerUIngestor:
    return MinerUIngestor()


@pytest.fixture
def tmp_pdf(tmp_path: Path) -> Path:
    p = tmp_path / "contract-2026.pdf"
    p.write_bytes(b"%PDF-1.4\n<<>>")
    return p


@pytest.fixture
def tmp_scan(tmp_path: Path) -> Path:
    p = tmp_path / "evidence-001.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n<fake>")
    return p


@pytest.fixture
def tmp_xlsx(tmp_path: Path) -> Path:
    p = tmp_path / "balance-2026.xlsx"
    p.write_bytes(b"PK\x03\x04<fake-xlsx>")
    return p


@pytest.mark.asyncio
async def test_supports_known_extensions(adapter: MinerUIngestor, tmp_path: Path) -> None:
    for ext in [".pdf", ".docx", ".png", ".jpg", ".xlsx", ".tiff"]:
        f = tmp_path / f"x{ext}"
        f.write_bytes(b"")
        assert await adapter.supports(f), f"应支持扩展名 {ext}"


@pytest.mark.asyncio
async def test_supports_rejects_unknown(adapter: MinerUIngestor, tmp_path: Path) -> None:
    f = tmp_path / "test.zzz"
    f.write_bytes(b"")
    assert await adapter.supports(f) is False


@pytest.mark.asyncio
async def test_ingest_missing_file_returns_warning(
    adapter: MinerUIngestor, tmp_path: Path
) -> None:
    result = await adapter.ingest(tmp_path / "no-such.pdf")
    assert isinstance(result, IngestResult)
    assert result.segments == []
    assert any(w.startswith("file_not_found") for w in result.warnings)


@pytest.mark.asyncio
async def test_ingest_pdf_returns_contract_mock(
    adapter: MinerUIngestor, tmp_pdf: Path
) -> None:
    result = await adapter.ingest(tmp_pdf, doc_type="contract")
    assert result.document_id == tmp_pdf.stem
    modalities = {seg.modality for seg in result.segments}
    assert Modality.TEXT.value in modalities
    assert Modality.TABLE.value in modalities
    assert Modality.SEAL.value in modalities
    # 法律层级提取应识别"第一章 / 第一条"
    structure = result.structure
    assert structure["type"] == "root"
    chapters = [c for c in structure["children"] if c["type"] == "chapter"]
    assert chapters, "合同 mock 必须识别出章节"
    assert chapters[0]["label"] == "第一章"


@pytest.mark.asyncio
async def test_ingest_scan_returns_image_and_seal(
    adapter: MinerUIngestor, tmp_scan: Path
) -> None:
    result = await adapter.ingest(tmp_scan, doc_type="scan")
    modalities = [seg.modality for seg in result.segments]
    assert Modality.IMAGE.value in modalities
    assert Modality.SEAL.value in modalities
    # 公章 segment 必须带 confidence + bbox
    seal = next(s for s in result.segments if s.modality == Modality.SEAL.value)
    assert "confidence" in seal.metadata
    assert "bbox" in seal.metadata
    assert isinstance(seal.content, bytes)


@pytest.mark.asyncio
async def test_ingest_xlsx_returns_table_and_formula(
    adapter: MinerUIngestor, tmp_xlsx: Path
) -> None:
    result = await adapter.ingest(tmp_xlsx, doc_type="report")
    modalities = [seg.modality for seg in result.segments]
    assert Modality.TABLE.value in modalities
    assert Modality.FORMULA.value in modalities
    table = next(s for s in result.segments if s.modality == Modality.TABLE.value)
    assert "| 科目 |" in str(table.content)


@pytest.mark.asyncio
async def test_ingest_statistics_populated(
    adapter: MinerUIngestor, tmp_pdf: Path
) -> None:
    result = await adapter.ingest(tmp_pdf)
    stats = result.statistics
    assert stats["doc_type"] == "auto"
    assert stats["engine"].startswith("mineru")
    assert "elapsed_ms" in stats
    assert "modality_counts" in stats
    assert sum(stats["modality_counts"].values()) == len(result.segments)


@pytest.mark.asyncio
async def test_real_engine_check_does_not_crash(adapter: MinerUIngestor) -> None:
    # 不依赖 magic_pdf 是否可用，仅断言不抛异常
    assert isinstance(MinerUIngestor._real_engine_available(), bool)


@pytest.mark.asyncio
async def test_invoke_sdk_and_cli_are_todo(adapter: MinerUIngestor, tmp_pdf: Path) -> None:
    with pytest.raises(NotImplementedError):
        await adapter._invoke_mineru_sdk(tmp_pdf)
    with pytest.raises(NotImplementedError):
        await adapter._invoke_mineru_cli(tmp_pdf)
