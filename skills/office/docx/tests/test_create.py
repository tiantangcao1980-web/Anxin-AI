# -*- coding: utf-8 -*-
"""测试 :mod:`skills.office.docx.helpers.create`。"""

from __future__ import annotations

import pytest

pytest.importorskip("docx")

from skills.office.docx.helpers.create import create_docx
from skills.office.docx.helpers.read import read_text, read_tables


def test_create_simple_passes(tmp_path):
    out = create_docx(
        tmp_path / "simple.docx",
        sections=[
            {"type": "heading", "level": 1, "text": "Hello"},
            {"type": "paragraph", "text": "world"},
        ],
        title="t",
        author="a",
    )
    assert out.exists()
    text = read_text(out)
    assert "Hello" in text
    assert "world" in text


def test_create_with_table_chinese(tmp_path):
    out = create_docx(
        tmp_path / "table.docx",
        sections=[
            {"type": "heading", "level": 2, "text": "中文表格测试"},
            {
                "type": "table",
                "header": ["姓名", "部门", "职务"],
                "rows": [
                    ["张三", "法务部", "高级法律顾问"],
                    ["李四", "合规部", "合规经理"],
                ],
            },
        ],
    )
    assert out.exists()
    tables = read_tables(out)
    assert len(tables) == 1
    rows = tables[0]
    assert rows[0] == ["姓名", "部门", "职务"]
    assert rows[1] == ["张三", "法务部", "高级法律顾问"]
    assert rows[2] == ["李四", "合规部", "合规经理"]
