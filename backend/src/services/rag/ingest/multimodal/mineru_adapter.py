# -*- coding: utf-8 -*-
"""MinerU 适配器（P13-A）。

MinerU 是 OpenDataLab 出的 PDF 多模态解析工具：

- Python SDK：``pip install magic-pdf``  （依赖大：含 paddle / detectron2 配置）
- CLI：``magic-pdf -p input.pdf -o output_dir``

本阶段策略
==========

为了避免 magic-pdf 的重型依赖（≈ 2 GB 模型权重 + paddleocr），当前实现：

1. **mock 模式（默认）**：根据 ``file_path`` 的扩展名 + 文件名启发式
   返回结构化假数据，但严格遵守 :class:`IngestResult` 契约。
2. **真接入位点**：``_invoke_mineru_sdk`` / ``_invoke_mineru_cli`` 已留好
   `TODO: integrate magic-pdf` 注释，下一阶段（P13-A.2）补齐。

之所以保留 mock 还可用：单元测试 / CI / 早期联调（P13-B 知识图谱、
P13-C VLM Query 都依赖 segment 契约即可工作，与真实 MinerU 输出无关）。
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from src.services.rag.ingest.multimodal.base import (
    IngestResult,
    Modality,
    MultimodalIngestor,
    ParsedSegment,
)
from src.services.rag.ingest.multimodal.layout_preserver import LayoutPreserver


# 支持的扩展名（小写）
_SUPPORTED_EXTENSIONS: set[str] = {
    ".pdf",
    ".doc",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".tif",
    ".xls",
    ".xlsx",
}


class MinerUIngestor(MultimodalIngestor):
    """MinerU 适配器（mock + 真接入 TODO）。

    Args:
        use_sdk: ``True`` 走 Python SDK，``False`` 走 CLI subprocess。
            当前两条路径均为 TODO，实际返回 mock 数据。
        max_pages: 单文档最大解析页数，超过截断（防御性）。
    """

    def __init__(self, *, use_sdk: bool = True, max_pages: int = 200) -> None:
        self.use_sdk = use_sdk
        self.max_pages = max_pages
        self._layout = LayoutPreserver()

    async def supports(self, file_path: Path) -> bool:
        """支持 PDF / Office / 常见图像扩展。"""
        return file_path.suffix.lower() in _SUPPORTED_EXTENSIONS

    async def ingest(self, file_path: Path, doc_type: str = "auto") -> IngestResult:
        """解析文档为多模态 segment 列表（当前 mock）。"""
        started = time.perf_counter()
        document_id = file_path.stem
        warnings: list[str] = []

        if not file_path.exists():
            warnings.append(f"file_not_found:{file_path}")
            return IngestResult(
                document_id=document_id,
                segments=[],
                structure={},
                statistics={"elapsed_ms": 0, "engine": "mineru-mock", "doc_type": doc_type},
                warnings=warnings,
            )

        if not await self.supports(file_path):
            warnings.append(f"unsupported_extension:{file_path.suffix}")

        # TODO(p13a-real): 接 magic-pdf SDK
        # ----------------------------------------------------------
        # if self.use_sdk:
        #     raw = await self._invoke_mineru_sdk(file_path)
        # else:
        #     raw = await self._invoke_mineru_cli(file_path)
        # segments = self._convert_mineru_output(raw, document_id)
        # ----------------------------------------------------------
        segments = await self._build_mock_segments(file_path, document_id, doc_type)

        # 法律层级抽取（仅对有文本的 segment 生效）
        text_blob = "\n".join(
            seg.content if isinstance(seg.content, str) else ""
            for seg in segments
            if seg.modality == Modality.TEXT.value
        )
        structure = self._layout.extract(text_blob) if text_blob else {}

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        result = IngestResult(
            document_id=document_id,
            segments=segments,
            structure=structure,
            statistics={
                "engine": "mineru-mock" if not self._real_engine_available() else "mineru-sdk",
                "doc_type": doc_type,
                "elapsed_ms": elapsed_ms,
                "page_count": self._estimate_pages(segments),
            },
            warnings=warnings,
        )
        result.statistics["modality_counts"] = result.count_by_modality()
        return result

    # ------------------------------------------------------------------
    # mock 数据生成
    # ------------------------------------------------------------------

    async def _build_mock_segments(
        self, file_path: Path, document_id: str, doc_type: str
    ) -> list[ParsedSegment]:
        """根据扩展名 + 文件名 hint 编排 mock segment。"""
        ext = file_path.suffix.lower()
        await asyncio.sleep(0)  # 占位异步切换点

        # 扫描件 / 图像优先：返回 image + seal candidate
        if ext in {".png", ".jpg", ".jpeg", ".tiff", ".tif"}:
            return self._mock_scan_segments(document_id)

        # Excel / Excel 截图 → 表格优先
        if ext in {".xls", ".xlsx"}:
            return self._mock_table_segments(document_id)

        # 默认：PDF / Office → 法律合同样板
        return self._mock_contract_segments(document_id, doc_type)

    @staticmethod
    def _mock_contract_segments(document_id: str, doc_type: str) -> list[ParsedSegment]:
        """合同 PDF 的 mock：含章 / 条层级 + 公章图。"""
        return [
            ParsedSegment(
                segment_id=f"{document_id}:0",
                modality=Modality.TEXT.value,
                content=(
                    "第一章 总则\n"
                    "第一条 为规范双方权利义务，依据《民法典》订立本合同。\n"
                    "第二条 本合同适用范围为甲乙双方之间的服务采购事项。\n"
                    "第二章 合作内容\n"
                    "第三条 甲方委托乙方提供 SaaS 软件开发服务。\n"
                    "  （一）产品形态：Web + 移动端。\n"
                    "  （二）交付节点：详见附件一。\n"
                ),
                metadata={
                    "page": 1,
                    "bbox": [40, 60, 560, 740],
                    "parent_section": "第一章 总则",
                    "confidence": 0.99,
                    "language": "zh-CN",
                    "doc_type": doc_type,
                },
            ),
            ParsedSegment(
                segment_id=f"{document_id}:1",
                modality=Modality.TABLE.value,
                content=(
                    "| 项目 | 金额 | 备注 |\n"
                    "|---|---|---|\n"
                    "| 一期 | 100,000 | 启动款 |\n"
                    "| 二期 | 200,000 | 验收款 |\n"
                ),
                metadata={
                    "page": 2,
                    "bbox": [60, 200, 540, 380],
                    "parent_section": "第三条",
                    "confidence": 0.95,
                    "rows": 2,
                    "cols": 3,
                },
            ),
            ParsedSegment(
                segment_id=f"{document_id}:2",
                modality=Modality.SEAL.value,
                content=b"\x89PNG\r\n\x1a\n<mock-seal-bytes>",
                metadata={
                    "page": 3,
                    "bbox": [400, 600, 540, 720],
                    "parent_section": "签章页",
                    "confidence": 0.83,
                    "color": "red",
                    "shape": "circle",
                },
            ),
        ]

    @staticmethod
    def _mock_scan_segments(document_id: str) -> list[ParsedSegment]:
        """扫描件：image + 公章候选 + OCR 文本。"""
        return [
            ParsedSegment(
                segment_id=f"{document_id}:0",
                modality=Modality.IMAGE.value,
                content=b"\x89PNG\r\n\x1a\n<mock-scan-image>",
                metadata={
                    "page": 1,
                    "bbox": [0, 0, 1240, 1754],
                    "parent_section": None,
                    "confidence": 1.0,
                },
            ),
            ParsedSegment(
                segment_id=f"{document_id}:1",
                modality=Modality.TEXT.value,
                content="兹证明本人于 2026 年 3 月 5 日已向甲方支付保证金人民币壹万元。",
                metadata={
                    "page": 1,
                    "bbox": [120, 400, 1100, 460],
                    "parent_section": "正文",
                    "confidence": 0.78,
                    "language": "zh-CN",
                    "ocr_engine": "mineru-mock",
                },
            ),
            ParsedSegment(
                segment_id=f"{document_id}:2",
                modality=Modality.SEAL.value,
                content=b"\x89PNG\r\n\x1a\n<mock-seal-bytes>",
                metadata={
                    "page": 1,
                    "bbox": [820, 1280, 1080, 1540],
                    "parent_section": "签章区",
                    "confidence": 0.72,
                    "color": "red",
                },
            ),
        ]

    @staticmethod
    def _mock_table_segments(document_id: str) -> list[ParsedSegment]:
        """财务报表 Excel：table 为主。"""
        return [
            ParsedSegment(
                segment_id=f"{document_id}:0",
                modality=Modality.TABLE.value,
                content=(
                    "| 科目 | 期初余额 | 期末余额 |\n"
                    "|---|---|---|\n"
                    "| 货币资金 | 1,200,000 | 1,540,000 |\n"
                    "| 应收账款 | 800,000 | 950,000 |\n"
                ),
                metadata={
                    "page": 1,
                    "bbox": [10, 40, 800, 320],
                    "parent_section": "资产负债表",
                    "confidence": 0.97,
                    "rows": 2,
                    "cols": 3,
                    "sheet": "Sheet1",
                },
            ),
            ParsedSegment(
                segment_id=f"{document_id}:1",
                modality=Modality.FORMULA.value,
                content="净利润 = 营业收入 - 营业成本 - 期间费用 - 所得税",
                metadata={
                    "page": 1,
                    "bbox": [10, 360, 600, 400],
                    "parent_section": "利润表",
                    "confidence": 0.88,
                    "latex": r"NetProfit = Revenue - Cost - Expense - Tax",
                },
            ),
        ]

    # ------------------------------------------------------------------
    # 真接入位点（TODO）
    # ------------------------------------------------------------------

    @staticmethod
    def _real_engine_available() -> bool:
        """是否本机已安装 magic-pdf。"""
        try:
            import importlib.util  # noqa: PLC0415
            return importlib.util.find_spec("magic_pdf") is not None
        except Exception:
            return False

    async def _invoke_mineru_sdk(self, file_path: Path) -> dict[str, Any]:
        """TODO(p13a-real): 调用 magic_pdf SDK。

        参考写法::

            from magic_pdf.tools.cli import do_parse
            doc_info = do_parse(str(file_path), out_path=str(workdir))

        SDK 输出会含 ``content_list``（按 page → block 组织），需要
        映射到 :class:`ParsedSegment`。
        """
        raise NotImplementedError("magic-pdf SDK 接入待 P13-A.2")

    async def _invoke_mineru_cli(self, file_path: Path) -> dict[str, Any]:
        """TODO(p13a-real): subprocess 调用 magic-pdf CLI。

        参考写法::

            cmd = ["magic-pdf", "-p", str(file_path), "-o", str(workdir)]
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return _load_mineru_workdir(workdir)
        """
        raise NotImplementedError("magic-pdf CLI 接入待 P13-A.2")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_pages(segments: list[ParsedSegment]) -> int:
        """从 segment metadata 推断页数。"""
        max_page = 0
        for seg in segments:
            page = seg.metadata.get("page")
            if isinstance(page, int) and page > max_page:
                max_page = page
        return max_page
