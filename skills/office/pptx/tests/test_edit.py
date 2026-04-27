# -*- coding: utf-8 -*-
"""edit.py 测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from skills.office.pptx.helpers import create, edit, read


def _build_deck(out: Path) -> None:
    create.create_pptx(
        out,
        slides=[
            {"layout": "title_only", "title": "页 0"},
            {"layout": "title_only", "title": "页 1"},
            {"layout": "title_only", "title": "页 2"},
            {"layout": "title_only", "title": "页 3"},
        ],
    )


def test_edit_reorder(tmp_path: Path) -> None:
    out = tmp_path / "reorder.pptx"
    _build_deck(out)

    edit.reorder_slides(out, [3, 0, 2, 1])
    slides = read.read_slides(out)
    titles = [s["title"] for s in slides]
    assert titles == ["页 3", "页 0", "页 2", "页 1"]


def test_edit_replace_text(tmp_path: Path) -> None:
    out = tmp_path / "replace.pptx"
    create.create_pptx(
        out,
        slides=[{"layout": "title_only", "title": "Q1 2025"}],
    )

    n = edit.replace_text(out, {"2025": "2026"})
    assert n >= 1
    slides = read.read_slides(out)
    assert "2026" in slides[0]["title"]
    assert "2025" not in slides[0]["title"]


def test_edit_reorder_invalid(tmp_path: Path) -> None:
    out = tmp_path / "invalid.pptx"
    _build_deck(out)
    with pytest.raises(ValueError):
        edit.reorder_slides(out, [0, 1])  # 长度不对
