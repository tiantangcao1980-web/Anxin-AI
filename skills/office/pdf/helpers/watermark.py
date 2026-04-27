# -*- coding: utf-8 -*-
"""水印 + 加密（基于 pypdf + reportlab）。

- add_text_watermark: 文字水印（透明度 + 旋转）
- add_image_watermark: 图片水印
- encrypt / decrypt: AES-256（pypdf 4.x 默认）
"""

from __future__ import annotations

import io
from pathlib import Path


def _ensure(path) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {p}")
    return p


def _make_text_watermark_pdf(
    text: str,
    page_size,
    opacity: float = 0.3,
    angle: int = 45,
    font_name: str = "STSong-Light",
    font_size: int = 48,
) -> io.BytesIO:
    """生成单页水印 PDF（内存）。"""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas

    try:
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
        actual_font = font_name
    except Exception:
        actual_font = "Helvetica"

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=page_size)
    width, height = page_size
    c.saveState()
    c.setFillAlpha(opacity)
    c.setFont(actual_font, font_size)
    c.translate(width / 2, height / 2)
    c.rotate(angle)
    c.drawCentredString(0, 0, text)
    c.restoreState()
    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def add_text_watermark(
    path,
    text: str,
    out_path,
    opacity: float = 0.3,
    angle: int = 45,
    font_size: int = 48,
) -> Path:
    """给 PDF 每一页加文字水印。"""
    from pypdf import PdfReader, PdfWriter

    src = _ensure(path)
    reader = PdfReader(str(src))
    writer = PdfWriter()

    for page in reader.pages:
        # 取页面大小（pt）
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        wm_buf = _make_text_watermark_pdf(
            text, (width, height), opacity=opacity, angle=angle, font_size=font_size
        )
        wm_reader = PdfReader(wm_buf)
        page.merge_page(wm_reader.pages[0])
        writer.add_page(page)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        writer.write(f)
    writer.close()
    return out


def add_image_watermark(path, image_path, out_path, opacity: float = 0.3) -> Path:
    """给 PDF 每页加图片水印（居中、按页面 50% 宽度缩放）。"""
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas

    src = _ensure(path)
    img = _ensure(image_path)
    reader = PdfReader(str(src))
    writer = PdfWriter()

    for page in reader.pages:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(width, height))
        c.saveState()
        c.setFillAlpha(opacity)
        # 50% 宽度居中
        iw = width * 0.5
        ih = iw  # 假设方形；reportlab 会按图片真实比例
        c.drawImage(
            str(img),
            (width - iw) / 2,
            (height - ih) / 2,
            width=iw,
            preserveAspectRatio=True,
            mask="auto",
        )
        c.restoreState()
        c.showPage()
        c.save()
        buf.seek(0)
        wm_reader = PdfReader(buf)
        page.merge_page(wm_reader.pages[0])
        writer.add_page(page)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        writer.write(f)
    writer.close()
    return out


def encrypt(path, password: str, out_path) -> Path:
    """AES-256 加密（pypdf 4.x 默认算法）。"""
    from pypdf import PdfReader, PdfWriter

    src = _ensure(path)
    reader = PdfReader(str(src))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    # pypdf 4.x: algorithm="AES-256"
    try:
        writer.encrypt(user_password=password, owner_password=password, algorithm="AES-256")
    except TypeError:
        # 兼容旧版本
        writer.encrypt(user_password=password, owner_password=password)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        writer.write(f)
    writer.close()
    return out


def decrypt(path, password: str, out_path) -> Path:
    """解密 PDF。"""
    from pypdf import PdfReader, PdfWriter

    src = _ensure(path)
    reader = PdfReader(str(src))
    if reader.is_encrypted:
        ok = reader.decrypt(password)
        if not ok:
            raise ValueError("密码错误，无法解密")
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        writer.write(f)
    writer.close()
    return out
