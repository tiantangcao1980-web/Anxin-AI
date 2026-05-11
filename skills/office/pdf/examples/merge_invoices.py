# -*- coding: utf-8 -*-
"""示例：批量合并发票 PDF。

用法:
    python merge_invoices.py /path/to/invoices_dir merged.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from skills.office.pdf.helpers.manipulate import merge  # noqa: E402


def main(input_dir: str, out_path: str) -> None:
    src = Path(input_dir)
    pdfs = sorted(src.glob("*.pdf"))
    if not pdfs:
        print(f"目录 {src} 下没有 PDF")
        return
    print(f"准备合并 {len(pdfs)} 个 PDF...")
    out = merge(pdfs, out_path)
    print(f"合并完成 → {out}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python merge_invoices.py <invoices_dir> <out.pdf>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
