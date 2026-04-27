# -*- coding: utf-8 -*-
"""theme.py 测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from pptx import Presentation

from skills.office.pptx.helpers import create, theme


def _build_deck(out: Path) -> None:
    create.create_pptx(
        out,
        slides=[
            {
                "layout": "title_content",
                "title": "标题",
                "content": ["正文 1", "正文 2"],
            }
        ],
    )


def test_list_themes() -> None:
    names = theme.list_themes()
    assert "专业" in names
    assert "商务" in names
    assert "极简" in names


def test_apply_theme_unknown(tmp_path: Path) -> None:
    out = tmp_path / "x.pptx"
    _build_deck(out)
    with pytest.raises(ValueError):
        theme.apply_theme(out, "NotExist")


def test_theme_changes_master_font(tmp_path: Path) -> None:
    out = tmp_path / "themed.pptx"
    _build_deck(out)

    theme.apply_theme(out, "商务")
    prs = Presentation(str(out))
    slide = prs.slides[0]

    # 收集所有 run 字体
    fonts: list[str] = []
    for shape in slide.shapes:
        if not getattr(shape, "has_text_frame", False):
            continue
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                if run.font.name:
                    fonts.append(run.font.name)

    # 「商务」主题应使用 Microsoft YaHei
    assert any("YaHei" in f for f in fonts), fonts


def test_set_master_font_overrides(tmp_path: Path) -> None:
    out = tmp_path / "fonts.pptx"
    _build_deck(out)
    theme.set_master_font(out, title_font="KaiTi", body_font="FangSong")

    prs = Presentation(str(out))
    slide = prs.slides[0]
    found_title, found_body = False, False
    for shape in slide.shapes:
        if not getattr(shape, "has_text_frame", False):
            continue
        is_title = shape == slide.shapes.title
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                if is_title and run.font.name == "KaiTi":
                    found_title = True
                if not is_title and run.font.name == "FangSong":
                    found_body = True
    assert found_title or found_body  # 至少其中一处应被改写
