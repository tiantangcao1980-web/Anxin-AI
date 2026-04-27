# -*- coding: utf-8 -*-
"""manipulate.py 测试：merge / split / rotate / reorder。"""

from __future__ import annotations

from pypdf import PdfReader

from skills.office.pdf.helpers.manipulate import merge, reorder, rotate, split


def test_merge(sample_pdf, sample_pdf_3p, tmp_path):
    out = tmp_path / "merged.pdf"
    merge([sample_pdf, sample_pdf_3p], out)
    assert out.exists()
    reader = PdfReader(str(out))
    assert len(reader.pages) == 2 + 3


def test_split(sample_pdf_3p, tmp_path):
    out_dir = tmp_path / "split"
    parts = split(sample_pdf_3p, [(1, 1), (2, 3)], out_dir)
    assert len(parts) == 2
    assert len(PdfReader(str(parts[0])).pages) == 1
    assert len(PdfReader(str(parts[1])).pages) == 2


def test_rotate(sample_pdf, tmp_path):
    out = tmp_path / "rotated.pdf"
    rotate(sample_pdf, page=1, degrees=90, out_path=out)
    reader = PdfReader(str(out))
    assert reader.pages[0].rotation in (90, -270)  # 兼容不同 pypdf 版本


def test_reorder(sample_pdf_3p, tmp_path):
    out = tmp_path / "reordered.pdf"
    reorder(sample_pdf_3p, [3, 1, 2], out)
    assert len(PdfReader(str(out)).pages) == 3
