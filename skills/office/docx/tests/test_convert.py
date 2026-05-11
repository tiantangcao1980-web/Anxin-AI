# -*- coding: utf-8 -*-
"""测试 :mod:`skills.office.docx.helpers.convert` 的 markdown 双向转换。"""

from __future__ import annotations

import pytest

pytest.importorskip("docx")

from skills.office.docx.helpers.convert import (
    docx_to_markdown,
    markdown_to_docx,
    parse_markdown,
)
from skills.office.docx.helpers.read import read_tables, read_text


SAMPLE_MD = """# 合同摘要

本合同自 **2026-04-26** 起生效，乙方为 *上海智策*。

## 关键条款

- 服务期限：12 个月
- 总金额：120,000 元
- 付款方式：分期

| 阶段 | 金额 |
| --- | --- |
| 首付款 | 60,000 |
| 尾款 | 60,000 |
"""


def test_markdown_roundtrip(tmp_path):
    out = markdown_to_docx(SAMPLE_MD, tmp_path / "round.docx")
    assert out.exists()

    text = read_text(out)
    assert "合同摘要" in text
    assert "关键条款" in text
    assert "服务期限：12 个月" in text or "服务期限" in text

    tables = read_tables(out)
    assert tables, "应当解析出至少一个表格"
    header = tables[0][0]
    assert header == ["阶段", "金额"]
    assert tables[0][1] == ["首付款", "60,000"]

    md = docx_to_markdown(out)
    assert "# 合同摘要" in md
    assert "## 关键条款" in md
    # 表格已在 markdown 中重新出现
    assert "| 阶段 | 金额 |" in md


def test_parse_markdown_smoke():
    sections = parse_markdown(SAMPLE_MD)
    types = [s["type"] for s in sections]
    assert "heading" in types
    assert "table" in types
