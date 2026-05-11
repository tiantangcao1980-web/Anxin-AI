# -*- coding: utf-8 -*-
"""读取 .pptx 文件 — slides / shapes / notes / metadata。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pptx import Presentation


def read_slides(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    """提取每张幻灯片的结构化信息。

    Returns:
        list of dict, each with:
          - index   : int 0-based
          - layout  : str（布局名）
          - title   : str | None
          - texts   : list[str]（所有 text frame 中的文本）
          - shapes  : list[dict] （shape_type / name / has_text）
          - notes   : str
    """
    prs = Presentation(str(path))
    out: list[dict[str, Any]] = []
    for i, slide in enumerate(prs.slides):
        title = None
        if slide.shapes.title is not None and slide.shapes.title.has_text_frame:
            title = slide.shapes.title.text_frame.text or None

        texts: list[str] = []
        shapes_info: list[dict[str, Any]] = []
        for shape in slide.shapes:
            shapes_info.append({
                "shape_type": str(shape.shape_type) if shape.shape_type is not None else "UNKNOWN",
                "name": shape.name,
                "has_text": bool(getattr(shape, "has_text_frame", False)),
            })
            if getattr(shape, "has_text_frame", False):
                txt = shape.text_frame.text
                if txt:
                    texts.append(txt)

        notes = ""
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text or ""

        out.append({
            "index": i,
            "layout": slide.slide_layout.name,
            "title": title,
            "texts": texts,
            "shapes": shapes_info,
            "notes": notes,
        })
    return out


def read_metadata(path: str | os.PathLike[str]) -> dict[str, Any]:
    """读取 .pptx 元数据。"""
    prs = Presentation(str(path))
    cp = prs.core_properties
    return {
        "slide_count": len(prs.slides),
        "title": cp.title or "",
        "author": cp.author or "",
        "subject": cp.subject or "",
        "keywords": cp.keywords or "",
        "created": cp.created.isoformat() if cp.created else None,
        "modified": cp.modified.isoformat() if cp.modified else None,
        "size": Path(path).stat().st_size if Path(path).exists() else 0,
    }
