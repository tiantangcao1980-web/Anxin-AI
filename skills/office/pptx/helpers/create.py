# -*- coding: utf-8 -*-
"""创建 .pptx 文件。

支持 6 种布局 + 4 种内嵌图表 + 图片 + 演讲者备注。
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches, Pt

# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

# python-pptx 默认主题里 SlideLayouts 的索引（标准 office 模板）
_LAYOUT_INDEX: dict[str, int] = {
    "title_only": 5,            # Title Only
    "title_content": 1,         # Title and Content
    "two_content": 3,           # Two Content
    "comparison": 4,            # Comparison
    "picture_with_caption": 8,  # Picture with Caption
    "blank": 6,                 # Blank
}

_CHART_TYPE: dict[str, XL_CHART_TYPE] = {
    "bar": XL_CHART_TYPE.BAR_CLUSTERED,
    "line": XL_CHART_TYPE.LINE,
    "pie": XL_CHART_TYPE.PIE,
    "scatter": XL_CHART_TYPE.XY_SCATTER,
}

# 默认中文字体
_DEFAULT_TITLE_FONT = "SimHei"
_DEFAULT_BODY_FONT = "SimSun"


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def create_pptx(path: str | os.PathLike[str], slides: list[dict[str, Any]]) -> str:
    """创建一份 .pptx 并返回绝对路径。

    Args:
        path: 输出文件路径
        slides: list of dict，每个 dict 支持以下键：
            - layout (str)          : 见 _LAYOUT_INDEX
            - title (str)           : 标题
            - content (list[str]|str): 正文
            - chart (dict)          : {"type", "categories", "series"}
            - image (str)           : 图片路径
            - notes (str)           : 演讲者备注
    """
    prs = Presentation()
    for slide_def in slides:
        _add_slide(prs, slide_def)

    out_path = Path(path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return str(out_path)


def create_pptx_from_template(
    template_path: str | os.PathLike[str],
    out_path: str | os.PathLike[str],
    variables: dict[str, str] | None = None,
) -> str:
    """从 Markdown 模板生成 .pptx。

    模板格式（每个 ## 标题为一页）：

        # 路演 PPT 模板

        ## 封面
        layout: title_only
        title: {{company}} 路演

        ## 问题
        layout: title_content
        title: 我们要解决的问题
        - 问题 1
        - 问题 2
        notes: 强调痛点
    """
    md = Path(template_path).read_text(encoding="utf-8")
    if variables:
        for k, v in variables.items():
            md = md.replace("{{" + k + "}}", v)

    slides = _parse_markdown_template(md)
    return create_pptx(out_path, slides)


# ---------------------------------------------------------------------------
# 内部：构造单页
# ---------------------------------------------------------------------------

def _add_slide(prs: Presentation, slide_def: dict[str, Any]) -> None:
    layout_name = slide_def.get("layout", "title_content")
    layout_idx = _LAYOUT_INDEX.get(layout_name, 1)
    # python-pptx 默认主题至少有 9 个布局，但容错一下
    layout_idx = min(layout_idx, len(prs.slide_layouts) - 1)
    slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])

    # 标题
    title_text = slide_def.get("title")
    if title_text and slide.shapes.title is not None:
        slide.shapes.title.text = str(title_text)
        _apply_font(slide.shapes.title, _DEFAULT_TITLE_FONT, bold=True)

    # 正文 / bullet
    content = slide_def.get("content")
    if content:
        _add_bullets(slide, content)

    # 图表
    chart_def = slide_def.get("chart")
    if chart_def:
        _add_chart(slide, chart_def)

    # 图片
    image_path = slide_def.get("image")
    if image_path and Path(image_path).exists():
        slide.shapes.add_picture(
            str(image_path),
            Inches(1), Inches(2),
            width=Inches(6),
        )

    # 演讲者备注
    notes = slide_def.get("notes")
    if notes:
        slide.notes_slide.notes_text_frame.text = str(notes)


def _add_bullets(slide, content: Any) -> None:
    if isinstance(content, str):
        items = [content]
    else:
        items = [str(x) for x in content]

    # 优先使用布局自带的 placeholder.body
    body_ph = None
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == 1:  # body
            body_ph = ph
            break

    if body_ph is None:
        # 兜底：插入 textbox
        tb = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5))
        tf = tb.text_frame
    else:
        tf = body_ph.text_frame

    tf.clear()
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item
        p.level = 0
        for run in p.runs:
            run.font.name = _DEFAULT_BODY_FONT
            run.font.size = Pt(18)


def _add_chart(slide, chart_def: dict[str, Any]) -> None:
    chart_type = _CHART_TYPE.get(chart_def.get("type", "bar"), XL_CHART_TYPE.BAR_CLUSTERED)

    x, y, cx, cy = Inches(1), Inches(2), Inches(7), Inches(4.5)

    if chart_type == XL_CHART_TYPE.XY_SCATTER:
        # series: list[(name, list[(x,y), ...])]
        chart_data = XyChartData()
        for name, points in chart_def.get("series", []):
            s = chart_data.add_series(str(name))
            for px, py in points:
                s.add_data_point(px, py)
        slide.shapes.add_chart(chart_type, x, y, cx, cy, chart_data)
    else:
        chart_data = CategoryChartData()
        chart_data.categories = chart_def.get("categories", [])
        for name, values in chart_def.get("series", []):
            chart_data.add_series(str(name), list(values))
        slide.shapes.add_chart(chart_type, x, y, cx, cy, chart_data)


def _apply_font(shape, font_name: str, *, bold: bool = False) -> None:
    if not shape.has_text_frame:
        return
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            run.font.name = font_name
            run.font.bold = bold


# ---------------------------------------------------------------------------
# 内部：模板解析（Markdown -> slides[]）
# ---------------------------------------------------------------------------

_HEADER_RE = re.compile(r"^##\s+(.+)$")
_KV_RE = re.compile(r"^([a-zA-Z_]+)\s*:\s*(.+)$")
_BULLET_RE = re.compile(r"^[-*]\s+(.+)$")


def _parse_markdown_template(md: str) -> list[dict[str, Any]]:
    slides: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    bullets: list[str] = []

    for raw in md.splitlines():
        line = raw.rstrip()

        if not line:
            continue
        if line.startswith("# "):
            # 文档大标题，忽略
            continue

        m = _HEADER_RE.match(line)
        if m:
            if current is not None:
                if bullets:
                    current.setdefault("content", bullets)
                slides.append(current)
            current = {"layout": "title_content", "title": m.group(1).strip()}
            bullets = []
            continue

        if current is None:
            continue

        m = _BULLET_RE.match(line)
        if m:
            bullets.append(m.group(1).strip())
            continue

        m = _KV_RE.match(line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if key == "title":
                current["title"] = value
            elif key == "layout":
                current["layout"] = value
            elif key == "notes":
                current["notes"] = value
            elif key == "image":
                current["image"] = value

    if current is not None:
        if bullets:
            current.setdefault("content", bullets)
        slides.append(current)

    return slides
