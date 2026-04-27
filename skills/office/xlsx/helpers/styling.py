# -*- coding: utf-8 -*-
"""xlsx 单元格样式 - 表头、条件格式、列宽。"""

from __future__ import annotations

from typing import Any

from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet


_HEADER_FILL = PatternFill("solid", fgColor="D9D9D9")  # 灰底
_HEADER_FONT = Font(bold=True, color="000000")
_HEADER_ALIGN = Alignment(horizontal="center", vertical="center")
_THIN_SIDE = Side(style="thin", color="999999")
_DEFAULT_BORDER = Border(left=_THIN_SIDE, right=_THIN_SIDE, top=_THIN_SIDE, bottom=_THIN_SIDE)


def apply_header_style(ws: Worksheet, row: int = 1) -> None:
    """对指定行应用表头样式（加粗 + 灰底 + 居中 + 细边框）。"""
    for cell in ws[row]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = _HEADER_ALIGN
        cell.border = _DEFAULT_BORDER


def apply_conditional_format(
    ws: Worksheet,
    range_str: str,
    rule: str,
    *,
    threshold: Any = None,
    color_high: str = "FFC7CE",  # 红
    color_low: str = "C6EFCE",   # 绿
) -> None:
    """应用条件格式。

    Args:
        ws: 工作表
        range_str: 范围，如 "B2:B100"
        rule: "high"（高于阈值红）| "low"（低于阈值绿）| "color_scale"（红→绿渐变）| "data_bar"（数据条）
        threshold: rule=high/low 时必传
        color_high: 高值色（去掉 #）
        color_low: 低值色
    """
    if rule == "high":
        if threshold is None:
            raise ValueError("rule='high' requires threshold")
        ws.conditional_formatting.add(
            range_str,
            CellIsRule(
                operator="greaterThan",
                formula=[str(threshold)],
                fill=PatternFill("solid", fgColor=color_high),
            ),
        )
    elif rule == "low":
        if threshold is None:
            raise ValueError("rule='low' requires threshold")
        ws.conditional_formatting.add(
            range_str,
            CellIsRule(
                operator="lessThan",
                formula=[str(threshold)],
                fill=PatternFill("solid", fgColor=color_low),
            ),
        )
    elif rule == "color_scale":
        ws.conditional_formatting.add(
            range_str,
            ColorScaleRule(
                start_type="min", start_color=color_low,
                end_type="max", end_color=color_high,
            ),
        )
    elif rule == "data_bar":
        ws.conditional_formatting.add(
            range_str,
            DataBarRule(start_type="min", end_type="max", color="638EC6"),
        )
    else:
        raise ValueError(f"unknown rule: {rule}")


def auto_fit_columns(ws: Worksheet) -> None:
    """简易列宽自适应：取列内最长字符串长度 + 2，封顶 60。"""
    for column_cells in ws.columns:
        try:
            col_letter = get_column_letter(column_cells[0].column)
        except (AttributeError, IndexError):
            continue
        max_len = 0
        for cell in column_cells:
            try:
                v = cell.value
            except AttributeError:
                continue
            if v is None:
                continue
            length = len(str(v))
            if length > max_len:
                max_len = length
        ws.column_dimensions[col_letter].width = min(max_len + 2, 60)
