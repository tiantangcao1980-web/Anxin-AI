# -*- coding: utf-8 -*-
"""示例：把 Markdown 调研稿渲染为 PDF（中文友好）。

用法:
    python generate_report_from_md.py research.md research.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from skills.office.pdf.helpers.generate import markdown_to_pdf  # noqa: E402


def main(md_path: str, out_path: str) -> None:
    md_text = Path(md_path).read_text(encoding="utf-8")
    out = markdown_to_pdf(md_text, out_path)
    print(f"已生成 PDF → {out}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python generate_report_from_md.py <input.md> <output.pdf>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
