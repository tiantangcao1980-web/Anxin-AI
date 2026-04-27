# -*- coding: utf-8 -*-
"""示例 1：用 sections 列表快速创建一个含标题、段落、页码的 .docx。

运行：
    python skills/office/docx/examples/create_simple.py /tmp/simple.docx
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from skills.office.docx.helpers.create import create_docx


def main(out_path: str = "/tmp/simple.docx") -> Path:
    sections = [
        {"type": "header", "text": "安心智能助手 — 示例文档"},
        {"type": "footer", "page_number": True},
        {"type": "heading", "level": 1, "text": "Hello, 安心"},
        {"type": "paragraph", "text": "这是一个最小可运行的 .docx 创建示例。"},
        {"type": "paragraph", "text": "支持中英文混排：Hello World 你好世界。", "bold": True},
        {"type": "paragraph", "text": "右对齐段落示例。", "align": "right"},
    ]
    return create_docx(out_path, sections, title="示例文档", author="anxin_assistant")


if __name__ == "__main__":
    out = main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/simple.docx")
    print(f"已生成: {out}")
