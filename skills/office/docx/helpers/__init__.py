# -*- coding: utf-8 -*-
"""安心智能助手 V3 — Word 文档处理 skill helpers.

子模块：
- create  : 创建 .docx
- read    : 读取 .docx 文本/表格/元数据
- edit    : 查找替换 / 插段 / 改单元格
- convert : Markdown ↔ docx 互转

所有 helper 都接受/返回标准 Python 类型，便于上层 SkillExecutor 直接桥接。
"""

from .create import create_docx
from .read import read_text, read_tables, read_metadata
from .edit import find_replace, insert_paragraph, update_table_cell
from .convert import markdown_to_docx, docx_to_markdown

__all__ = [
    "create_docx",
    "read_text",
    "read_tables",
    "read_metadata",
    "find_replace",
    "insert_paragraph",
    "update_table_cell",
    "markdown_to_docx",
    "docx_to_markdown",
]
