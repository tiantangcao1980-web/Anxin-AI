# -*- coding: utf-8 -*-
"""示例：从合同 PDF 提取正文 + 表格 + 元数据。

用法:
    python extract_contract_text.py path/to/contract.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

# 让示例脚本可独立运行
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from skills.office.pdf.helpers.extract import (  # noqa: E402
    extract_metadata,
    extract_tables,
    extract_text,
)


def main(pdf_path: str) -> None:
    print("== 元数据 ==")
    for k, v in extract_metadata(pdf_path).items():
        print(f"  {k}: {v}")

    print("\n== 正文（前 500 字）==")
    text = extract_text(pdf_path)
    print(text[:500])

    tables = extract_tables(pdf_path)
    print(f"\n== 提取到 {len(tables)} 张表格 ==")
    for i, tbl in enumerate(tables, 1):
        print(f"  表 {i}: {len(tbl)} 行 x {len(tbl[0]) if tbl else 0} 列")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python extract_contract_text.py path/to/contract.pdf")
        sys.exit(1)
    main(sys.argv[1])
