# -*- coding: utf-8 -*-
"""extract.py 测试。"""

from __future__ import annotations

from skills.office.pdf.helpers.extract import (
    extract_metadata,
    extract_tables,
    extract_text,
)


def test_extract_text_full(sample_pdf):
    text = extract_text(sample_pdf)
    assert "Hello Anxin V3 - Page 1" in text
    assert "Hello Anxin V3 - Page 2" in text


def test_extract_text_range(sample_pdf):
    text = extract_text(sample_pdf, pages=(1, 1))
    assert "Page 1" in text
    assert "Page 2" not in text


def test_extract_metadata(sample_pdf):
    meta = extract_metadata(sample_pdf)
    assert meta["page_count"] == 2


def test_extract_tables_empty_ok(sample_pdf):
    # 我们的 sample 没有表格，应返回空列表，不报错
    tables = extract_tables(sample_pdf)
    assert isinstance(tables, list)
