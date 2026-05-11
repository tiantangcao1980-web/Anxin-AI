# -*- coding: utf-8 -*-
"""编辑现有 .docx 文档.

三个常用操作：

- :func:`find_replace`         ：按 dict 做多字段查找替换，保留 run 格式
- :func:`insert_paragraph`     ：在某段文本后插入新段落
- :func:`update_table_cell`    ：精确更新某个表格单元格
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

try:
    from docx import Document
    from docx.text.paragraph import Paragraph
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "python-docx 未安装。请在 backend 环境执行: pip install 'python-docx>=1.1'"
    ) from exc


# ---------------------------------------------------------------------------
# 查找替换
# ---------------------------------------------------------------------------

def _replace_in_paragraph(p: Paragraph, mapping: Mapping[str, str]) -> int:
    """在段落内做查找替换。

    策略：
    1. 先在每个 run 内独立替换（保留格式）
    2. 若整段文本含 key 但 run 之间被切断，则把整段拼起来替换后写回到第一个 run，
       清空其余 run 的文本（格式上以第一个 run 为准）

    返回替换发生次数。
    """
    count = 0
    # 先尝试 run 级别替换
    for run in p.runs:
        new = run.text
        for key, value in mapping.items():
            if key and key in new:
                new = new.replace(key, value)
                count += mapping_hit(key, run.text)
        if new != run.text:
            run.text = new

    # 再处理跨 run 的情况
    full = p.text
    needs_cross = any(k in full and not _present_in_any_run(p, k) for k in mapping if k)
    if needs_cross:
        new_full = full
        for key, value in mapping.items():
            if key and key in new_full:
                new_full = new_full.replace(key, value)
                count += full.count(key)
        if p.runs:
            p.runs[0].text = new_full
            for run in p.runs[1:]:
                run.text = ""
        else:
            p.add_run(new_full)
    return count


def mapping_hit(key: str, text: str) -> int:
    """工具函数：统计 key 在 text 中出现次数。"""
    if not key:
        return 0
    return text.count(key)


def _present_in_any_run(p: Paragraph, key: str) -> bool:
    return any(key in run.text for run in p.runs)


def find_replace(path: str | Path, mapping: Mapping[str, str]) -> int:
    """对整个 .docx 做查找替换（含正文段落 + 表格单元格 + 页眉页脚）.

    :param path: 待修改文件路径（原地写回）
    :param mapping: ``{要找的: 替换为的}``，key 为空字符串会被忽略
    :returns: 替换总次数
    """
    if not mapping:
        return 0
    doc = Document(str(path))
    total = 0
    # 正文
    for p in doc.paragraphs:
        total += _replace_in_paragraph(p, mapping)
    # 表格
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    total += _replace_in_paragraph(p, mapping)
    # 页眉页脚
    for section in doc.sections:
        for container in (section.header, section.footer):
            for p in container.paragraphs:
                total += _replace_in_paragraph(p, mapping)
    doc.save(str(path))
    return total


# ---------------------------------------------------------------------------
# 在指定段落后插入新段落
# ---------------------------------------------------------------------------

def insert_paragraph(
    path: str | Path,
    after_text: str,
    content: str,
    *,
    style: str | None = None,
) -> bool:
    """在第一个匹配 ``after_text`` 的段落后插入新段落.

    :param path: docx 路径
    :param after_text: 锚点段落（精确匹配 .text，全等或包含均触发）
    :param content: 新段落文本
    :param style: 可选段落样式（如 "Heading 2"）
    :returns: 是否成功插入
    """
    doc = Document(str(path))
    target: Paragraph | None = None
    for p in doc.paragraphs:
        if p.text == after_text or after_text in p.text:
            target = p
            break
    if target is None:
        return False

    new_p = target._element.addnext(
        _make_paragraph_element(doc, content, style=style)
    )  # noqa: F841
    doc.save(str(path))
    return True


def _make_paragraph_element(doc, text: str, *, style: str | None):
    """构造一个 <w:p> XML 元素并返回。"""
    p = doc.add_paragraph(text)
    if style:
        try:
            p.style = doc.styles[style]
        except KeyError:
            pass
    # 把刚加的段落从尾部摘出来，调用方负责把它 addnext 到指定位置
    elem = p._element
    elem.getparent().remove(elem)
    return elem


# ---------------------------------------------------------------------------
# 修改表格单元格
# ---------------------------------------------------------------------------

def update_table_cell(
    path: str | Path,
    table_idx: int,
    row: int,
    col: int,
    value: str,
) -> bool:
    """精确更新某个表格单元格.

    :returns: 是否成功更新（坐标越界返回 False）
    """
    doc = Document(str(path))
    if table_idx < 0 or table_idx >= len(doc.tables):
        return False
    table = doc.tables[table_idx]
    if row < 0 or row >= len(table.rows):
        return False
    cells = table.rows[row].cells
    if col < 0 or col >= len(cells):
        return False
    cell = cells[col]
    # 清空原内容（保留第一个 paragraph 节点）
    for p in cell.paragraphs:
        for run in list(p.runs):
            run.text = ""
    if cell.paragraphs:
        if cell.paragraphs[0].runs:
            cell.paragraphs[0].runs[0].text = str(value)
        else:
            cell.paragraphs[0].add_run(str(value))
    else:
        cell.text = str(value)
    doc.save(str(path))
    return True
