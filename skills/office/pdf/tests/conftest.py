# -*- coding: utf-8 -*-
"""共享 fixture：生成临时 PDF 用于测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让 from skills.office.pdf.helpers.* 可导入
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """生成一个 2 页的最简 PDF。"""
    from reportlab.pdfgen import canvas

    out = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(out))
    c.drawString(72, 720, "Hello Anxin V3 - Page 1")
    c.drawString(72, 700, "This is a test PDF.")
    c.showPage()
    c.drawString(72, 720, "Hello Anxin V3 - Page 2")
    c.drawString(72, 700, "Second page content.")
    c.showPage()
    c.save()
    return out


@pytest.fixture
def sample_pdf_3p(tmp_path: Path) -> Path:
    """3 页 PDF。"""
    from reportlab.pdfgen import canvas

    out = tmp_path / "sample3.pdf"
    c = canvas.Canvas(str(out))
    for i in range(1, 4):
        c.drawString(72, 720, f"Page {i}")
        c.showPage()
    c.save()
    return out
