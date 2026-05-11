# -*- coding: utf-8 -*-
"""PDF skill helpers — extract / manipulate / generate / ocr / watermark / form.

公开导出常用函数，方便 `from skills.office.pdf.helpers import extract_text`。
"""

from .extract import (
    extract_images,
    extract_metadata,
    extract_tables,
    extract_text,
)
from .form import fill_form, read_form
from .generate import html_to_pdf, markdown_to_pdf
from .manipulate import merge, reorder, rotate, split
from .ocr import ocr_image, ocr_pdf
from .watermark import (
    add_image_watermark,
    add_text_watermark,
    decrypt,
    encrypt,
)

__all__ = [
    "extract_text",
    "extract_tables",
    "extract_images",
    "extract_metadata",
    "merge",
    "split",
    "rotate",
    "reorder",
    "markdown_to_pdf",
    "html_to_pdf",
    "ocr_pdf",
    "ocr_image",
    "add_text_watermark",
    "add_image_watermark",
    "encrypt",
    "decrypt",
    "read_form",
    "fill_form",
]
