# -*- coding: utf-8 -*-
"""tests/test_analyze.py - pandas 分析。"""

from __future__ import annotations

import pandas as pd
import pytest

from skills.office.xlsx.helpers import analyze


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "region": ["北", "北", "南", "南", "南"],
            "category": ["a", "b", "a", "b", "a"],
            "amount": [10, 20, 30, 40, 50],
        }
    )


def test_summarize_returns_full_dict(df):
    out = analyze.summarize(df)
    assert out["shape"] == (5, 3)
    assert set(out["columns"]) == {"region", "category", "amount"}
    assert out["null_count"]["amount"] == 0
    assert "amount" in out["describe"]
    assert "region" not in out["describe"]  # describe 仅 numeric


def test_groupby_agg_sum(df):
    res = analyze.groupby_agg(df, group_col="region", agg_col="amount", func="sum")
    res = res.set_index("region")["amount"].to_dict()
    assert res["北"] == 30
    assert res["南"] == 120


def test_groupby_agg_avg(df):
    res = analyze.groupby_agg(df, group_col="region", agg_col="amount", func="avg")
    res = res.set_index("region")["amount"].to_dict()
    assert res["北"] == 15
    assert res["南"] == 40


def test_analyze_pivot(df):
    p = analyze.pivot_table(
        df, index="region", columns="category", values="amount", aggfunc="sum"
    )
    # 北/a = 10, 北/b = 20, 南/a = 30+50=80, 南/b = 40
    assert p.loc["北", "a"] == 10
    assert p.loc["北", "b"] == 20
    assert p.loc["南", "a"] == 80
    assert p.loc["南", "b"] == 40


def test_groupby_unsupported_func_raises(df):
    with pytest.raises(ValueError, match="unsupported agg func"):
        analyze.groupby_agg(df, "region", "amount", func="bogus")
