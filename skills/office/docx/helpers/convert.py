# -*- coding: utf-8 -*-
r"""Markdown <-> docx 互转.

策略：
- 不强依赖 ``markdown`` 第三方库，提供一个内置极简解析器，覆盖：
  ``# 标题`` ``- 列表`` ``1. 有序列表`` ``| 表格 |`` ``\`\`\` 代码块 \`\`\``
  ``**粗体**`` ``*斜体*`` ``> 引用``。
- 若用户安装了 ``markdown``，可在外层先转 HTML 再交由其他工具，但本模块默认不依赖。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .create import create_docx


# ---------------------------------------------------------------------------
# Markdown -> structured sections -> docx
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_OL_RE = re.compile(r"^\s*\d+\.\s+(.+?)\s*$")
_UL_RE = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*[-: ]+\s*(\|\s*[-: ]+\s*)+\|?\s*$")
_CODE_FENCE_RE = re.compile(r"^```")


def _strip_inline(text: str) -> str:
    """去掉 ``**`` ``*`` 并保留文本（python-docx 默认不解析 inline）。"""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def _parse_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def parse_markdown(md: str) -> list[dict]:
    """把 markdown 文本解析为 :func:`create_docx` 接受的 sections。"""
    sections: list[dict] = []
    lines = md.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # 代码块
        if _CODE_FENCE_RE.match(line):
            buf: list[str] = []
            i += 1
            while i < n and not _CODE_FENCE_RE.match(lines[i]):
                buf.append(lines[i])
                i += 1
            sections.append({"type": "paragraph", "text": "\n".join(buf)})
            i += 1  # 跳过结束 ```
            continue

        # 标题
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            sections.append(
                {"type": "heading", "level": level, "text": _strip_inline(m.group(2))}
            )
            i += 1
            continue

        # 表格：当前行有 |，下一行是分隔
        if "|" in line and i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1]):
            header = [_strip_inline(c) for c in _parse_table_row(line)]
            i += 2  # 跳过表头和分隔行
            rows: list[list[str]] = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append([_strip_inline(c) for c in _parse_table_row(lines[i])])
                i += 1
            sections.append({"type": "table", "header": header, "rows": rows})
            continue

        # 列表（连续多行打包）
        if _UL_RE.match(line) or _OL_RE.match(line):
            while i < n and (_UL_RE.match(lines[i]) or _OL_RE.match(lines[i])):
                m_ul = _UL_RE.match(lines[i])
                m_ol = _OL_RE.match(lines[i])
                text = m_ul.group(1) if m_ul else m_ol.group(1)
                bullet = "• " if m_ul else "  "
                sections.append({"type": "paragraph", "text": bullet + _strip_inline(text)})
                i += 1
            continue

        # 引用
        if line.startswith(">"):
            sections.append(
                {"type": "paragraph", "text": _strip_inline(line.lstrip("> ").strip()),
                 "italic": True}
            )
            i += 1
            continue

        # 分隔
        if line.strip() in ("---", "***", "___"):
            sections.append({"type": "page_break"})
            i += 1
            continue

        # 空行 -> 跳过
        if not line.strip():
            i += 1
            continue

        # 普通段落（合并连续非空行）
        buf = [line]
        i += 1
        while i < n and lines[i].strip() and not _is_block_start(lines[i]):
            buf.append(lines[i])
            i += 1
        sections.append({"type": "paragraph", "text": _strip_inline(" ".join(buf))})
    return sections


def _is_block_start(line: str) -> bool:
    if _HEADING_RE.match(line):
        return True
    if _UL_RE.match(line) or _OL_RE.match(line):
        return True
    if _CODE_FENCE_RE.match(line):
        return True
    if line.startswith(">"):
        return True
    if "|" in line:
        return True
    return False


def markdown_to_docx(md_text: str, out_path: str | Path) -> Path:
    """把 markdown 字符串转成 .docx 并返回输出路径。"""
    sections = parse_markdown(md_text)
    return create_docx(out_path, sections)


# ---------------------------------------------------------------------------
# docx -> markdown
# ---------------------------------------------------------------------------

try:
    from docx import Document
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "python-docx 未安装。请在 backend 环境执行: pip install 'python-docx>=1.1'"
    ) from exc


def docx_to_markdown(path: str | Path) -> str:
    """把 .docx 反向转为 markdown 文本。"""
    doc = Document(str(path))
    body = doc.element.body
    out: list[str] = []
    para_idx = 0
    table_idx = 0

    paragraphs = list(doc.paragraphs)
    tables = list(doc.tables)

    # 按顺序遍历 body 子节点（保持段落和表格的相对顺序）
    for child in body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p" and para_idx < len(paragraphs):
            p = paragraphs[para_idx]
            para_idx += 1
            text = p.text
            style_name = (p.style.name or "").lower() if p.style else ""
            if style_name.startswith("heading"):
                # "Heading 1" -> level 1
                m = re.search(r"(\d+)", style_name)
                level = int(m.group(1)) if m else 1
                level = max(1, min(level, 6))
                out.append("#" * level + " " + text)
            elif text:
                out.append(text)
            else:
                out.append("")
        elif tag == "tbl" and table_idx < len(tables):
            t = tables[table_idx]
            table_idx += 1
            out.extend(_table_to_md(t))
            out.append("")

    return "\n".join(out).strip() + "\n"


def _table_to_md(table) -> Iterable[str]:
    rows = [[cell.text.replace("\n", " ").strip() for cell in row.cells]
            for row in table.rows]
    if not rows:
        return []
    n_cols = max(len(r) for r in rows)
    rows = [r + [""] * (n_cols - len(r)) for r in rows]
    header = rows[0]
    sep = ["---"] * n_cols
    body = rows[1:]
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    for r in body:
        out.append("| " + " | ".join(r) + " |")
    return out
