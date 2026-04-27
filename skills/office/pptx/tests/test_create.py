# -*- coding: utf-8 -*-
"""create.py 测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from skills.office.pptx.helpers import create, read


def test_create_simple_deck(tmp_path: Path) -> None:
    out = tmp_path / "simple.pptx"
    p = create.create_pptx(
        out,
        slides=[
            {"layout": "title_only", "title": "封面"},
            {
                "layout": "title_content",
                "title": "目录",
                "content": ["第一节", "第二节", "第三节"],
                "notes": "讲 3 分钟",
            },
            {"layout": "title_only", "title": "致谢"},
        ],
    )
    assert Path(p).exists()
    slides = read.read_slides(p)
    assert len(slides) == 3
    assert slides[0]["title"] == "封面"
    assert "第一节" in "\n".join(slides[1]["texts"])
    assert "讲 3 分钟" in slides[1]["notes"]


def test_create_with_pie_chart(tmp_path: Path) -> None:
    out = tmp_path / "chart.pptx"
    p = create.create_pptx(
        out,
        slides=[
            {
                "layout": "title_content",
                "title": "客户构成",
                "chart": {
                    "type": "pie",
                    "categories": ["A", "B", "C"],
                    "series": [("数量", [60, 30, 10])],
                },
            }
        ],
    )
    assert Path(p).exists()
    # 至少能读出 1 张幻灯片
    slides = read.read_slides(p)
    assert len(slides) == 1
    # 应至少包含一个非文本形状（图表）
    has_chart_like = any(
        not s["has_text"] for s in slides[0]["shapes"]
    )
    assert has_chart_like, slides[0]["shapes"]
