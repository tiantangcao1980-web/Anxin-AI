# -*- coding: utf-8 -*-
"""tests/test_read.py - 读取 sheet/公式。"""

from __future__ import annotations

import pandas as pd

from skills.office.xlsx.helpers import create, read


def _make_demo(path):
    create.create_xlsx(
        path,
        {
            "Q1": [
                ["月", "营收"],
                [1, 100],
                [2, 200],
                [3, 300],
                ["合计", "=SUM(B2:B4)"],
            ],
            "Q2": [
                ["月", "营收"],
                [4, 400],
            ],
        },
    )


def test_read_returns_dataframe(tmp_path):
    out = tmp_path / "r.xlsx"
    _make_demo(out)
    df = read.read_sheet(out, "Q1")
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["月", "营收"]
    # 4 行（1..3 + 合计）
    assert df.shape[0] == 4


def test_read_all_sheets_returns_mapping(tmp_path):
    out = tmp_path / "r.xlsx"
    _make_demo(out)
    sheets = read.read_all_sheets(out)
    assert set(sheets.keys()) == {"Q1", "Q2"}
    assert sheets["Q2"].shape[0] == 1


def test_read_formulas_extracts_sum(tmp_path):
    out = tmp_path / "r.xlsx"
    _make_demo(out)
    formulas = read.read_formulas(out, sheet_name="Q1")
    assert "B5" in formulas
    assert formulas["B5"] == "=SUM(B2:B4)"
