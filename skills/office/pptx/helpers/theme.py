# -*- coding: utf-8 -*-
"""主题切换 — 颜色 / 字体 / 母版。

内置 3 个主题：
- 「专业」  : 深蓝色调，标题 SimHei，正文 SimSun
- 「商务」  : 深灰 + 金，标题 Microsoft YaHei，正文 Microsoft YaHei
- 「极简」  : 黑白，标题 Source Han Sans / 等距，正文 SimSun
"""

from __future__ import annotations

import os
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Pt


_THEMES: dict[str, dict[str, Any]] = {
    "专业": {
        "title_font": "SimHei",
        "body_font": "SimSun",
        "title_color": RGBColor(0x0F, 0x3D, 0x7A),  # 深蓝
        "body_color": RGBColor(0x33, 0x33, 0x33),
        "title_size": Pt(36),
        "body_size": Pt(18),
    },
    "商务": {
        "title_font": "Microsoft YaHei",
        "body_font": "Microsoft YaHei",
        "title_color": RGBColor(0x2C, 0x2C, 0x2C),  # 深灰
        "body_color": RGBColor(0x55, 0x55, 0x55),
        "title_size": Pt(34),
        "body_size": Pt(18),
    },
    "极简": {
        "title_font": "Source Han Sans",
        "body_font": "SimSun",
        "title_color": RGBColor(0x00, 0x00, 0x00),
        "body_color": RGBColor(0x44, 0x44, 0x44),
        "title_size": Pt(32),
        "body_size": Pt(16),
    },
}


def list_themes() -> list[str]:
    """返回内置主题名列表。"""
    return list(_THEMES.keys())


def apply_theme(path: str | os.PathLike[str], theme_name: str) -> None:
    """对整个 .pptx 应用主题（颜色 + 字体 + 字号）。"""
    if theme_name not in _THEMES:
        raise ValueError(
            f"unknown theme {theme_name!r}; available: {list(_THEMES)}"
        )
    theme = _THEMES[theme_name]
    prs = Presentation(str(path))

    for slide in prs.slides:
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            is_title = shape == slide.shapes.title
            font_name = theme["title_font"] if is_title else theme["body_font"]
            color = theme["title_color"] if is_title else theme["body_color"]
            size = theme["title_size"] if is_title else theme["body_size"]
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    run.font.name = font_name
                    run.font.color.rgb = color
                    run.font.size = size
                    if is_title:
                        run.font.bold = True

    prs.save(str(path))


def set_master_font(
    path: str | os.PathLike[str],
    title_font: str | None = None,
    body_font: str | None = None,
) -> None:
    """对所有页面 / 母版统一字体（不动颜色和字号）。"""
    if not title_font and not body_font:
        return
    prs = Presentation(str(path))

    # slide masters
    for master in prs.slide_masters:
        for shape in master.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if body_font:
                        run.font.name = body_font

    # 现有幻灯片
    for slide in prs.slides:
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            is_title = shape == slide.shapes.title
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if is_title and title_font:
                        run.font.name = title_font
                    elif not is_title and body_font:
                        run.font.name = body_font

    prs.save(str(path))
