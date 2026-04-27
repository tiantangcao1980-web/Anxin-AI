# -*- coding: utf-8 -*-
"""xlsx 创建工具 - 基于 openpyxl。

设计原则：
1. 公式安全：所有以 = + - @ 起头的字符串都过 `_check_formula_safe`，
   包含 `cmd|`、`/c `、`DDE(`、`WEBSERVICE(`、`IMPORTDATA(` 等危险 token 直接拒绝；
2. 外部数据（CSV / 用户表单）走 `sanitize_external_value`，前置单引号防 CSV Injection；
3. 多 sheet 一次性写入，列宽自动套到最长内容；
4. 图表统一用 openpyxl.chart 的 Bar/Line/Pie，避免依赖额外画图库。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

# ---------------------------------------------------------------------------
# 公式安全
# ---------------------------------------------------------------------------

# 大小写不敏感的危险 token —— 命中即拒
_DANGEROUS_TOKENS = (
    "cmd|",
    "/c ",
    "/c\t",
    "dde(",
    "webservice(",
    "importdata(",
    "rtd(",
    "call(",
    "exec(",
    "system(",
)

# HYPERLINK 允许，但禁 javascript: / file:// / vbscript: 协议
_HYPERLINK_BAD_PROTO = re.compile(
    r"hyperlink\s*\(\s*[\"'](?:javascript:|file://|vbscript:|data:)",
    re.IGNORECASE,
)

# 公式起头字符
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _check_formula_safe(formula: str) -> None:
    """检查公式是否含危险 token，命中抛 ValueError。"""
    if not isinstance(formula, str):
        return
    lowered = formula.lower()
    for token in _DANGEROUS_TOKENS:
        if token in lowered:
            raise ValueError(
                f"formula injection rejected: dangerous token {token!r} in {formula!r}"
            )
    if _HYPERLINK_BAD_PROTO.search(formula):
        raise ValueError(
            f"formula injection rejected: dangerous hyperlink protocol in {formula!r}"
        )


def sanitize_external_value(value: Any) -> Any:
    """对外部来源（CSV / 用户输入）的值做反 CSV-Injection 处理。

    若是字符串且以 `= + - @` 起头，前置单引号让 Excel 当文本。
    其他类型原样返回。
    """
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def _write_value(ws: Worksheet, row: int, col: int, value: Any) -> None:
    """统一写入：公式走安全检查，普通值原样写。"""
    if isinstance(value, str) and value.startswith("="):
        _check_formula_safe(value)
    ws.cell(row=row, column=col, value=value)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def create_xlsx(
    path: str | Path,
    sheets: dict[str, Iterable[Iterable[Any]]],
    *,
    auto_fit: bool = True,
) -> Workbook:
    """创建 xlsx 文件。

    Args:
        path: 输出文件路径
        sheets: dict[sheet_name, rows]，rows 是二维可迭代
        auto_fit: 是否自动调列宽

    Returns:
        openpyxl Workbook 对象（已 save，但仍可二次编辑后再 save）。
    """
    wb = Workbook()
    # 删默认 sheet
    default = wb.active
    wb.remove(default)

    for sheet_name, rows in sheets.items():
        ws = wb.create_sheet(title=sheet_name[:31])  # Excel sheet name ≤ 31 字符
        for r_idx, row in enumerate(rows, start=1):
            for c_idx, value in enumerate(row, start=1):
                _write_value(ws, r_idx, c_idx, value)
        if auto_fit:
            auto_fit_columns(ws)

    wb.save(str(path))
    return wb


def add_formula(ws: Worksheet, cell: str, formula: str) -> None:
    """安全地写入公式。

    Args:
        ws: 工作表
        cell: 单元格坐标，如 "B5"
        formula: 公式字符串，必须以 = 起头
    """
    if not formula.startswith("="):
        raise ValueError("formula must start with '='")
    _check_formula_safe(formula)
    ws[cell] = formula


def add_chart(
    ws: Worksheet,
    chart_type: str,
    data_range: str,
    *,
    anchor: str = "G2",
    title: str | None = None,
    categories_range: str | None = None,
) -> None:
    """在 sheet 里加图表。

    Args:
        ws: 工作表
        chart_type: "bar" | "line" | "pie"
        data_range: 数据区，如 "A1:D4"（第一行视为表头）
        anchor: 图表左上角锚点单元格
        title: 图表标题
        categories_range: 分类轴范围（可选，默认取数据区第一列）
    """
    chart_type = chart_type.lower()
    if chart_type == "bar":
        chart = BarChart()
    elif chart_type == "line":
        chart = LineChart()
    elif chart_type == "pie":
        chart = PieChart()
    else:
        raise ValueError(f"unsupported chart_type: {chart_type}")

    if title:
        chart.title = title

    # 解析 range
    from openpyxl.utils.cell import range_boundaries

    min_col, min_row, max_col, max_row = range_boundaries(data_range)
    data_ref = Reference(
        ws,
        min_col=min_col + 1,  # 跳过分类列
        min_row=min_row,
        max_col=max_col,
        max_row=max_row,
    )
    cats_ref = Reference(
        ws,
        min_col=min_col,
        min_row=min_row + 1,
        max_col=min_col,
        max_row=max_row,
    )
    if categories_range:
        c_min_col, c_min_row, c_max_col, c_max_row = range_boundaries(categories_range)
        cats_ref = Reference(
            ws,
            min_col=c_min_col,
            min_row=c_min_row,
            max_col=c_max_col,
            max_row=c_max_row,
        )

    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    ws.add_chart(chart, anchor)


def merge_cells(ws: Worksheet, range_str: str) -> None:
    """合并单元格。"""
    ws.merge_cells(range_str)


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
