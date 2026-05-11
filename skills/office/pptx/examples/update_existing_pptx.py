# -*- coding: utf-8 -*-
"""示例 3：在已有 PPT 上做编辑（替换文本 + 重排序 + 套主题）。"""

from __future__ import annotations

from pathlib import Path

from skills.office.pptx.helpers.create import create_pptx
from skills.office.pptx.helpers.edit import (
    add_slide,
    remove_slide,
    reorder_slides,
    replace_text,
)
from skills.office.pptx.helpers.theme import apply_theme


def main() -> str:
    out = Path(__file__).parent / "output_updated.pptx"

    # 1) 先创建一份初始 PPT
    create_pptx(
        str(out),
        slides=[
            {"layout": "title_only", "title": "2025 年规划"},
            {"layout": "title_content", "title": "Q1", "content": ["目标 A", "目标 B"]},
            {"layout": "title_content", "title": "Q2", "content": ["目标 C"]},
            {"layout": "title_only", "title": "TODO 待删除页"},
        ],
    )

    # 2) 替换年份
    replace_text(str(out), {"2025": "2026"})

    # 3) 删除最后一页
    remove_slide(str(out), index=-1)

    # 4) 在末尾追加致谢页
    add_slide(
        str(out),
        layout="title_only",
        content={"title": "Thank You"},
        position=-1,
    )

    # 5) 把 Q1 / Q2 顺序对调
    reorder_slides(str(out), [0, 2, 1, 3])

    # 6) 应用「商务」主题
    apply_theme(str(out), "商务")

    return str(out)


if __name__ == "__main__":
    print(main())
