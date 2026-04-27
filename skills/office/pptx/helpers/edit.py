# -*- coding: utf-8 -*-
"""编辑 .pptx 文件 — replace / reorder / add / remove。"""

from __future__ import annotations

import os
from typing import Any

from pptx import Presentation

from .create import _add_slide  # 复用单页构造逻辑


def replace_text(path: str | os.PathLike[str], mapping: dict[str, str]) -> int:
    """全文替换；返回替换次数（按 run 计）。

    精度保留在 run 层面，避免破坏字体格式。
    """
    if not mapping:
        return 0

    prs = Presentation(str(path))
    n = 0
    for slide in prs.slides:
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    text = run.text
                    new_text = text
                    for old, new in mapping.items():
                        if old in new_text:
                            new_text = new_text.replace(old, new)
                    if new_text != text:
                        run.text = new_text
                        n += 1
        # notes
        if slide.has_notes_slide:
            tf = slide.notes_slide.notes_text_frame
            for para in tf.paragraphs:
                for run in para.runs:
                    text = run.text
                    new_text = text
                    for old, new in mapping.items():
                        if old in new_text:
                            new_text = new_text.replace(old, new)
                    if new_text != text:
                        run.text = new_text
                        n += 1

    prs.save(str(path))
    return n


def reorder_slides(path: str | os.PathLike[str], new_order: list[int]) -> None:
    """按 new_order 重新排序。

    new_order 必须是 [0..N-1] 的一个排列。
    """
    prs = Presentation(str(path))
    n = len(prs.slides)
    if sorted(new_order) != list(range(n)):
        raise ValueError(
            f"new_order must be a permutation of 0..{n - 1}, got {new_order}"
        )

    # 通过操作 sldIdLst 子元素顺序实现 reorder
    # 注意 lxml 不允许同一节点同时存在两次，先 detach 再 append
    sldIdLst = prs.slides._sldIdLst  # type: ignore[attr-defined]
    children = list(sldIdLst)
    for c in children:
        sldIdLst.remove(c)
    for i in new_order:
        sldIdLst.append(children[i])

    prs.save(str(path))


def add_slide(
    path: str | os.PathLike[str],
    layout: str,
    content: dict[str, Any],
    position: int = -1,
) -> None:
    """在 position 插入一张幻灯片；position=-1 表示追加到最后。"""
    prs = Presentation(str(path))

    slide_def = {"layout": layout, **content}
    _add_slide(prs, slide_def)

    # 如果 position 不是末尾，需要在 sldIdLst 上挪到目标位置
    if position != -1:
        sldIdLst = prs.slides._sldIdLst  # type: ignore[attr-defined]
        children = list(sldIdLst)
        new_slide_elem = children[-1]
        sldIdLst.remove(new_slide_elem)
        # 重新计算插入索引
        target = position if position >= 0 else len(children) + position
        target = max(0, min(target, len(children) - 1))
        # 注：children 已不含 new_slide_elem
        remaining = list(sldIdLst)
        # 清空再按新顺序追加
        for c in remaining:
            sldIdLst.remove(c)
        for i, c in enumerate(remaining):
            if i == target:
                sldIdLst.append(new_slide_elem)
            sldIdLst.append(c)
        if target >= len(remaining):
            sldIdLst.append(new_slide_elem)

    prs.save(str(path))


def remove_slide(path: str | os.PathLike[str], index: int) -> None:
    """删除指定索引的幻灯片。"""
    prs = Presentation(str(path))
    n = len(prs.slides)
    if index < 0:
        index = n + index
    if not (0 <= index < n):
        raise IndexError(f"slide index {index} out of range (0..{n - 1})")

    sldIdLst = prs.slides._sldIdLst  # type: ignore[attr-defined]
    children = list(sldIdLst)
    sldIdLst.remove(children[index])

    prs.save(str(path))
