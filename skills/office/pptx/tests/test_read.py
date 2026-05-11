# -*- coding: utf-8 -*-
"""read.py 测试。"""

from __future__ import annotations

from pathlib import Path

from skills.office.pptx.helpers import create, read


def test_read_slides_returns_text_and_notes(tmp_path: Path) -> None:
    out = tmp_path / "deck.pptx"
    create.create_pptx(
        out,
        slides=[
            {
                "layout": "title_content",
                "title": "标题页",
                "content": ["要点 A", "要点 B"],
                "notes": "演讲提示",
            },
        ],
    )
    slides = read.read_slides(out)
    assert len(slides) == 1
    s = slides[0]
    assert s["title"] == "标题页"
    joined = "\n".join(s["texts"])
    assert "要点 A" in joined
    assert "要点 B" in joined
    assert s["notes"] == "演讲提示"

    meta = read.read_metadata(out)
    assert meta["slide_count"] == 1
    assert meta["size"] > 0
