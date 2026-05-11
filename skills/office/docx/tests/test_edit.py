# -*- coding: utf-8 -*-
"""测试 :mod:`skills.office.docx.helpers.edit`。"""

from __future__ import annotations

import pytest

pytest.importorskip("docx")

from skills.office.docx.helpers.create import create_docx
from skills.office.docx.helpers.edit import (
    find_replace,
    insert_paragraph,
    update_table_cell,
)
from skills.office.docx.helpers.read import read_text, read_tables


def _build_doc(tmp_path):
    return create_docx(
        tmp_path / "edit.docx",
        sections=[
            {"type": "heading", "level": 1, "text": "{{标题}}"},
            {"type": "paragraph", "text": "甲方：{{甲方}}"},
            {"type": "paragraph", "text": "签约日期：{{日期}}"},
            {
                "type": "table",
                "header": ["项目", "金额"],
                "rows": [["首付款", "0"], ["尾款", "0"]],
            },
        ],
    )


def test_edit_find_replace_preserves_format(tmp_path):
    out = _build_doc(tmp_path)
    n = find_replace(
        out,
        {
            "{{标题}}": "服务合同",
            "{{甲方}}": "北京安心科技有限公司",
            "{{日期}}": "2026-04-26",
        },
    )
    assert n >= 3
    text = read_text(out)
    assert "{{标题}}" not in text
    assert "{{甲方}}" not in text
    assert "服务合同" in text
    assert "北京安心科技有限公司" in text
    assert "2026-04-26" in text


def test_update_table_cell(tmp_path):
    out = _build_doc(tmp_path)
    assert update_table_cell(out, table_idx=0, row=1, col=1, value="60,000")
    assert update_table_cell(out, table_idx=0, row=2, col=1, value="60,000")
    assert not update_table_cell(out, table_idx=99, row=0, col=0, value="x")
    tables = read_tables(out)
    # row 1 是首付款行，col 1 是金额列
    assert tables[0][1][1] == "60,000"
    assert tables[0][2][1] == "60,000"


def test_insert_paragraph(tmp_path):
    out = _build_doc(tmp_path)
    ok = insert_paragraph(out, after_text="甲方：{{甲方}}", content="新增条款：保密期限三年。")
    assert ok
    text = read_text(out)
    assert "新增条款：保密期限三年。" in text
