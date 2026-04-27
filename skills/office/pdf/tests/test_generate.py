# -*- coding: utf-8 -*-
"""generate.py 测试：markdown / html → PDF。"""

from __future__ import annotations

from pypdf import PdfReader

from skills.office.pdf.helpers.generate import html_to_pdf, markdown_to_pdf


def test_markdown_to_pdf_basic(tmp_path):
    md = """# 标题一

正文段落，包含**加粗**和*斜体*。

- 列表项 1
- 列表项 2

```
code block
```
"""
    out = tmp_path / "out.md.pdf"
    markdown_to_pdf(md, out)
    assert out.exists() and out.stat().st_size > 0
    reader = PdfReader(str(out))
    assert len(reader.pages) >= 1


def test_html_to_pdf_basic(tmp_path):
    html = """
    <h1>标题</h1>
    <p>段落内容，包含 <b>加粗</b> 与 <i>斜体</i>。</p>
    <ul><li>项一</li><li>项二</li></ul>
    """
    out = tmp_path / "out.html.pdf"
    html_to_pdf(html, out)
    assert out.exists() and out.stat().st_size > 0
