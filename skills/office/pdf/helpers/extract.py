# -*- coding: utf-8 -*-
"""PDF 内容提取（基于 pdfplumber + pypdf）。

- extract_text: 文本（可指定页范围）
- extract_tables: 表格三维数组
- extract_images: 抽图到目录
- extract_metadata: 文档元数据
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def _ensure_path(path) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {p}")
    return p


def extract_text(path, pages: Optional[tuple[int, int]] = None) -> str:
    """提取 PDF 文本。

    Args:
        path: PDF 文件路径
        pages: (start, end) 闭区间页码（1-based），不传则提取全文

    Returns:
        合并后的文本，页之间用 \n\n 分隔
    """
    import pdfplumber

    p = _ensure_path(path)
    chunks: list[str] = []
    with pdfplumber.open(str(p)) as pdf:
        total = len(pdf.pages)
        if pages is None:
            start, end = 1, total
        else:
            start, end = pages
            start = max(1, start)
            end = min(total, end)
        for i in range(start - 1, end):
            text = pdf.pages[i].extract_text() or ""
            chunks.append(text)
    return "\n\n".join(chunks)


def extract_tables(path) -> list[list[list[str]]]:
    """提取所有表格。

    Returns:
        三维数组：[table][row][cell]
    """
    import pdfplumber

    p = _ensure_path(path)
    all_tables: list[list[list[str]]] = []
    with pdfplumber.open(str(p)) as pdf:
        for page in pdf.pages:
            for tbl in page.extract_tables() or []:
                # 标准化为字符串
                norm = [[("" if c is None else str(c)) for c in row] for row in tbl]
                all_tables.append(norm)
    return all_tables


def extract_images(path, out_dir) -> list[Path]:
    """抽出 PDF 内嵌图片到 out_dir，返回写入的文件路径列表。

    使用 pypdf 的 images API（4.x+）。
    """
    from pypdf import PdfReader

    p = _ensure_path(path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(p))
    written: list[Path] = []
    for i, page in enumerate(reader.pages):
        for j, image in enumerate(page.images):
            # image.name 可能含扩展名；统一拼装
            name = image.name or f"page-{i+1}-img-{j+1}.bin"
            target = out / f"page{i+1}-{j+1}-{name}"
            target.write_bytes(image.data)
            written.append(target)
    return written


def extract_metadata(path) -> dict:
    """提取文档元数据：标题/作者/创建时间/页数等。"""
    from pypdf import PdfReader

    p = _ensure_path(path)
    reader = PdfReader(str(p))
    meta = reader.metadata or {}
    # 转 dict 并去掉前导 /
    data = {
        (k[1:] if isinstance(k, str) and k.startswith("/") else k): (str(v) if v is not None else None)
        for k, v in (meta.items() if hasattr(meta, "items") else [])
    }
    data["page_count"] = len(reader.pages)
    return data
