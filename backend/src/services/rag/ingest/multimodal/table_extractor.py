# -*- coding: utf-8 -*-
"""表格抽取（P13-A）。

真实接入路径
============

- **PDF / Image 表格**：MinerU 输出 ``content_list`` 已含 table 块（HTML / Markdown）。
- **复杂表格**（合并单元格、跨页）：可叠加 ``camelot`` / ``pdfplumber`` /
  ``unstructured`` 二次校正。
- **Excel**：``pandas.read_excel`` → ``DataFrame.to_markdown`` 即可。

本阶段
======

提供"统一 markdown 输出"接口。``extract_from_markdown`` 直接接受
MinerU 已输出的 markdown 表格字符串并校验列数一致性 / 行数；
``to_markdown`` 把 row-major 二维列表转 markdown。

下游 RAG 召回基于 markdown chunk 即可，不必反序列化为 DataFrame。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TableData:
    """结构化表格。"""

    headers: list[str]
    rows: list[list[str]]
    markdown: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def col_count(self) -> int:
        return len(self.headers)


class TableExtractor:
    """表格抽取器。"""

    @staticmethod
    def to_markdown(headers: list[str], rows: list[list[str]]) -> str:
        """二维表 → markdown 表格字符串。"""
        if not headers:
            return ""
        head_line = "| " + " | ".join(headers) + " |"
        sep_line = "|" + "|".join(["---"] * len(headers)) + "|"
        body_lines = [
            "| " + " | ".join(str(cell) for cell in row) + " |"
            for row in rows
        ]
        return "\n".join([head_line, sep_line, *body_lines])

    @staticmethod
    def extract_from_markdown(md_table: str) -> TableData | None:
        """解析 markdown 表格字符串。无法解析返回 ``None``。"""
        lines = [ln for ln in md_table.strip().splitlines() if ln.strip()]
        if len(lines) < 2:
            return None

        # 第一行 header
        header_cells = [c.strip() for c in lines[0].strip("|").split("|")]
        # 第二行分隔（``---``），跳过
        if "---" not in lines[1]:
            return None

        body_rows: list[list[str]] = []
        for line in lines[2:]:
            cells = [c.strip() for c in line.strip("|").split("|")]
            # 列数对齐（不足补空，超出截断）—— 保留原始单元格数也行，
            # 这里选择稳健的截 / 补，便于下游统计。
            if len(cells) < len(header_cells):
                cells.extend([""] * (len(header_cells) - len(cells)))
            elif len(cells) > len(header_cells):
                cells = cells[: len(header_cells)]
            body_rows.append(cells)

        return TableData(
            headers=header_cells,
            rows=body_rows,
            markdown=md_table.strip(),
            metadata={"source": "markdown"},
        )

    @staticmethod
    def extract_from_2d(headers: list[str], rows: list[list[str]]) -> TableData:
        """直接从二维列表构造（Excel / pandas 路径）。"""
        md = TableExtractor.to_markdown(headers, rows)
        return TableData(
            headers=headers,
            rows=rows,
            markdown=md,
            metadata={"source": "2d-list"},
        )

    # 真接入位点 ------------------------------------------------------
    @staticmethod
    async def extract_from_pdf_block(_block: dict[str, Any]) -> TableData | None:
        """TODO(p13a-real): 接 MinerU table block。

        典型输入字段：``html`` / ``markdown`` / ``cell_grid``。
        """
        raise NotImplementedError("PDF table block 解析待 P13-A.2")
