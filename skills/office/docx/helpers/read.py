# -*- coding: utf-8 -*-
"""读取 .docx 文档.

提供三个互不依赖的入口：

- :func:`read_text`     ：按段落顺序拼接成纯文本（段落间 ``\n``）
- :func:`read_tables`   ：返回所有表格的二维数组列表
- :func:`read_metadata` ：返回 core_properties 关键字段字典
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from docx import Document
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "python-docx 未安装。请在 backend 环境执行: pip install 'python-docx>=1.1'"
    ) from exc


def read_text(path: str | Path) -> str:
    """提取所有段落文本（不含表格内文本）."""
    doc = Document(str(path))
    parts: list[str] = []
    for p in doc.paragraphs:
        text = p.text
        if text:
            parts.append(text)
    return "\n".join(parts)


def read_tables(path: str | Path) -> list[list[list[str]]]:
    """提取所有表格 -> [table][row][col] 三维列表."""
    doc = Document(str(path))
    out: list[list[list[str]]] = []
    for table in doc.tables:
        rows: list[list[str]] = []
        for row in table.rows:
            rows.append([cell.text for cell in row.cells])
        out.append(rows)
    return out


def read_metadata(path: str | Path) -> dict[str, Any]:
    """读取 core_properties 关键字段."""
    doc = Document(str(path))
    cp = doc.core_properties
    return {
        "author": cp.author,
        "title": cp.title,
        "subject": cp.subject,
        "keywords": cp.keywords,
        "comments": cp.comments,
        "category": cp.category,
        "created": cp.created.isoformat() if cp.created else None,
        "modified": cp.modified.isoformat() if cp.modified else None,
        "last_modified_by": cp.last_modified_by,
        "revision": cp.revision,
    }


def read_full(path: str | Path) -> dict[str, Any]:
    """便捷函数：一次返回 text + tables + metadata."""
    return {
        "text": read_text(path),
        "tables": read_tables(path),
        "metadata": read_metadata(path),
    }
