# -*- coding: utf-8 -*-
"""扫描件 OCR（基于 pytesseract）。

系统依赖：
- macOS:  brew install tesseract tesseract-lang
- Ubuntu: apt-get install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng

验证：`tesseract --list-langs` 应包含 chi_sim。
"""

from __future__ import annotations

import shutil
from pathlib import Path


def _check_tesseract() -> bool:
    """tesseract 可执行文件是否在 PATH。"""
    return shutil.which("tesseract") is not None


def _ensure_tesseract():
    if not _check_tesseract():
        raise RuntimeError(
            "未检测到 tesseract，请先安装：\n"
            "  macOS:  brew install tesseract tesseract-lang\n"
            "  Ubuntu: apt-get install tesseract-ocr tesseract-ocr-chi-sim"
        )


def _ensure_path(path) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {p}")
    return p


def ocr_image(image_path, lang: str = "chi_sim+eng") -> str:
    """对单张图片做 OCR。"""
    _ensure_tesseract()
    import pytesseract
    from PIL import Image

    p = _ensure_path(image_path)
    return pytesseract.image_to_string(Image.open(str(p)), lang=lang)


def ocr_pdf(path, lang: str = "chi_sim+eng", dpi: int = 200) -> str:
    """对整个 PDF 做 OCR：先把每页渲染为图片，再调 tesseract。

    优先使用 pdf2image（系统需有 poppler）；若不可用，则回退到 pdfplumber 的 to_image。
    """
    _ensure_tesseract()
    import pytesseract

    p = _ensure_path(path)
    texts: list[str] = []

    # 路径 1: pdf2image
    try:
        from pdf2image import convert_from_path

        images = convert_from_path(str(p), dpi=dpi)
        for img in images:
            texts.append(pytesseract.image_to_string(img, lang=lang))
        return "\n\n".join(texts)
    except Exception:
        pass

    # 路径 2: pdfplumber to_image
    import pdfplumber

    with pdfplumber.open(str(p)) as pdf:
        for page in pdf.pages:
            pil_img = page.to_image(resolution=dpi).original
            texts.append(pytesseract.image_to_string(pil_img, lang=lang))
    return "\n\n".join(texts)
