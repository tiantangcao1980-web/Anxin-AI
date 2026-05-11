# -*- coding: utf-8 -*-
"""测试 :mod:`skills.office.docx.helpers.read`。"""

from __future__ import annotations

import pytest

pytest.importorskip("docx")

from skills.office.docx.helpers.create import create_docx
from skills.office.docx.helpers.read import read_text, read_tables, read_metadata


def test_read_extracts_all_paragraphs(tmp_path):
    out = create_docx(
        tmp_path / "many.docx",
        sections=[
            {"type": "heading", "level": 1, "text": "段落一"},
            {"type": "paragraph", "text": "第一段正文。"},
            {"type": "paragraph", "text": "第二段正文。"},
            {"type": "page_break"},
            {"type": "paragraph", "text": "第三段在新页。"},
        ],
        title="读取测试",
        author="anxin_assistant",
    )
    text = read_text(out)
    assert "段落一" in text
    assert "第一段正文。" in text
    assert "第二段正文。" in text
    assert "第三段在新页。" in text

    meta = read_metadata(out)
    assert meta["title"] == "读取测试"
    assert meta["author"] == "anxin_assistant"
    # tables 为空
    assert read_tables(out) == []
