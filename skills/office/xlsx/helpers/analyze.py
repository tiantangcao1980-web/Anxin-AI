# -*- coding: utf-8 -*-
"""xlsx 数据分析 - pandas 封装。

提供描述性统计、分组聚合、数据透视。
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def summarize(df: pd.DataFrame) -> dict[str, Any]:
    """对 DataFrame 做描述性统计。

    返回包含：
    - shape: (rows, cols)
    - columns: 列名列表
    - dtypes: {col: dtype_str}
    - describe: numeric 列的 describe()
    - null_count: {col: 缺失数}
    - unique_count: {col: 唯一值数}
    """
    numeric_describe = (
        df.describe(include="number").to_dict() if df.select_dtypes("number").shape[1] else {}
    )
    return {
        "shape": df.shape,
        "columns": df.columns.tolist(),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "describe": numeric_describe,
        "null_count": df.isnull().sum().to_dict(),
        "unique_count": df.nunique().to_dict(),
    }


_AGG_FUNCS = {
    "sum": "sum",
    "avg": "mean",
    "mean": "mean",
    "max": "max",
    "min": "min",
    "count": "count",
    "median": "median",
    "std": "std",
}


def groupby_agg(
    df: pd.DataFrame,
    group_col: str | list[str],
    agg_col: str,
    func: str = "sum",
) -> pd.DataFrame:
    """按 group_col 分组，对 agg_col 跑 func 聚合。

    Args:
        df: 输入 DataFrame
        group_col: 分组列（单列或多列）
        agg_col: 聚合列
        func: sum/avg/mean/max/min/count/median/std 之一
    """
    if func not in _AGG_FUNCS:
        raise ValueError(f"unsupported agg func: {func}; allowed: {list(_AGG_FUNCS)}")
    pandas_func = _AGG_FUNCS[func]
    grouped = df.groupby(group_col)[agg_col].agg(pandas_func)
    return grouped.reset_index()


def pivot_table(
    df: pd.DataFrame,
    index: str | list[str],
    columns: str | list[str] | None,
    values: str | list[str],
    aggfunc: str = "sum",
    fill_value: Any = 0,
) -> pd.DataFrame:
    """数据透视。

    Args:
        df: 输入
        index: 行索引列
        columns: 列方向展开的列；None 表示不展开
        values: 取值列
        aggfunc: 聚合方式
        fill_value: 缺失填充
    """
    if aggfunc in _AGG_FUNCS:
        aggfunc = _AGG_FUNCS[aggfunc]
    return pd.pivot_table(
        df,
        index=index,
        columns=columns,
        values=values,
        aggfunc=aggfunc,
        fill_value=fill_value,
    )
