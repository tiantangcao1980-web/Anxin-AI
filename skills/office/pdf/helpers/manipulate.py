# -*- coding: utf-8 -*-
"""PDF 页面操作（基于 pypdf）。

- merge: 合并多文件
- split: 按页范围拆分
- rotate: 单页旋转
- reorder: 页面重排
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def _ensure(path) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {p}")
    return p


def merge(paths: Iterable, out_path) -> Path:
    """合并多个 PDF。"""
    from pypdf import PdfWriter

    writer = PdfWriter()
    for p in paths:
        writer.append(str(_ensure(p)))
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        writer.write(f)
    writer.close()
    return out


def split(path, ranges: list[tuple[int, int]], out_dir) -> list[Path]:
    """按页范围拆分。

    Args:
        path: 输入 PDF
        ranges: 列表，每项 (start, end) 闭区间 1-based
        out_dir: 输出目录，文件命名 part-1.pdf, part-2.pdf...

    Returns:
        生成的文件列表
    """
    from pypdf import PdfReader, PdfWriter

    src = _ensure(path)
    reader = PdfReader(str(src))
    total = len(reader.pages)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for idx, (start, end) in enumerate(ranges, 1):
        s = max(1, start)
        e = min(total, end)
        if s > e:
            continue
        writer = PdfWriter()
        for i in range(s - 1, e):
            writer.add_page(reader.pages[i])
        target = out / f"part-{idx}.pdf"
        with target.open("wb") as f:
            writer.write(f)
        writer.close()
        written.append(target)
    return written


def rotate(path, page: int, degrees: int, out_path) -> Path:
    """旋转某页（degrees 必须是 90/180/270 的倍数）。"""
    from pypdf import PdfReader, PdfWriter

    if degrees % 90 != 0:
        raise ValueError("degrees 必须是 90 的倍数")
    src = _ensure(path)
    reader = PdfReader(str(src))
    if page < 1 or page > len(reader.pages):
        raise IndexError(f"页码越界: {page} (1..{len(reader.pages)})")
    writer = PdfWriter()
    for i, p in enumerate(reader.pages, 1):
        if i == page:
            p.rotate(degrees)
        writer.add_page(p)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        writer.write(f)
    writer.close()
    return out


def reorder(path, new_order: list[int], out_path) -> Path:
    """按 new_order 重新排列页面（1-based）。

    new_order 长度可与原始相同或为子集；重复 id 会被复制。
    """
    from pypdf import PdfReader, PdfWriter

    src = _ensure(path)
    reader = PdfReader(str(src))
    total = len(reader.pages)
    writer = PdfWriter()
    for i in new_order:
        if i < 1 or i > total:
            raise IndexError(f"页码越界: {i}")
        writer.add_page(reader.pages[i - 1])
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        writer.write(f)
    writer.close()
    return out
