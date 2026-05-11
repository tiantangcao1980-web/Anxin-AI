# -*- coding: utf-8 -*-
"""安心智能助手 — pptx skill helpers.

四件套：
- create  : 创建 .pptx（含图表 / 图片 / 备注）
- read    : 读取 .pptx（slide text / shapes / notes / metadata）
- edit    : 编辑 .pptx（replace / reorder / add / remove）
- theme   : 主题切换（颜色 / 字体 / 母版）
"""

from . import create, read, edit, theme  # noqa: F401

__all__ = ["create", "read", "edit", "theme"]
