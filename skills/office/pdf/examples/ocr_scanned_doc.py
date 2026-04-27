# -*- coding: utf-8 -*-
"""示例：对扫描件 PDF 做中英混合 OCR。

前置：tesseract 已安装并包含 chi_sim。
    macOS: brew install tesseract tesseract-lang
    Ubuntu: apt-get install tesseract-ocr tesseract-ocr-chi-sim

用法:
    python ocr_scanned_doc.py path/to/scan.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from skills.office.pdf.helpers.ocr import ocr_pdf  # noqa: E402


def main(pdf_path: str) -> None:
    text = ocr_pdf(pdf_path, lang="chi_sim+eng")
    print(text)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python ocr_scanned_doc.py <scan.pdf>")
        sys.exit(1)
    main(sys.argv[1])
