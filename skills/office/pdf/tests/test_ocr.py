# -*- coding: utf-8 -*-
"""ocr.py 测试：仅在系统装有 tesseract 时执行。"""

from __future__ import annotations

import shutil

import pytest

from skills.office.pdf.helpers import ocr

no_tesseract = shutil.which("tesseract") is None


@pytest.mark.skipif(no_tesseract, reason="未安装 tesseract，跳过 OCR 测试")
def test_ocr_pdf_runs(sample_pdf):
    """仅验证 OCR 能跑通，不强求识别精度（合成 PDF 是矢量文本，OCR 结果可能为空）。"""
    text = ocr.ocr_pdf(sample_pdf, lang="eng")
    assert isinstance(text, str)


@pytest.mark.skipif(no_tesseract, reason="未安装 tesseract，跳过 OCR 测试")
def test_ocr_image_runs(tmp_path):
    """渲染一张含英文的图，OCR 能识别。"""
    from PIL import Image, ImageDraw, ImageFont

    img_path = tmp_path / "hello.png"
    img = Image.new("RGB", (300, 80), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("Arial.ttf", 32)
    except Exception:
        font = ImageFont.load_default()
    draw.text((10, 20), "Hello OCR", fill="black", font=font)
    img.save(img_path)

    text = ocr.ocr_image(img_path, lang="eng")
    assert isinstance(text, str)


def test_ocr_raises_when_missing(monkeypatch, sample_pdf):
    """模拟 tesseract 不在 PATH，应抛 RuntimeError。"""
    monkeypatch.setattr(ocr.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="tesseract"):
        ocr.ocr_pdf(sample_pdf)
