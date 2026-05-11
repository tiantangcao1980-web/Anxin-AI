# -*- coding: utf-8 -*-
"""示例 4：CSV → 描述性统计 + groupby 聚合 → 多 sheet xlsx。

模拟一份订单 CSV，做销售分析后落地为 xlsx。
"""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pandas as pd

from skills.office.xlsx.helpers import analyze, create, styling


def _make_demo_csv(path: Path) -> None:
    rows = [
        ["order_id", "region", "category", "amount"],
        ["O001", "华北", "合同审查", 1200],
        ["O002", "华东", "财税咨询", 800],
        ["O003", "华南", "合同审查", 1500],
        ["O004", "华北", "财税咨询", 950],
        ["O005", "华东", "合同审查", 1100],
        ["O006", "华南", "财税咨询", 780],
        ["O007", "华北", "合同审查", 1300],
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


def main(out: str = "/tmp/anxin_csv_analysis.xlsx") -> Path:
    csv_path = Path(tempfile.mkstemp(suffix=".csv")[1])
    _make_demo_csv(csv_path)

    df = pd.read_csv(csv_path)

    # 1. 全表描述
    summary = analyze.summarize(df)

    # 2. 按 region 求和
    region_sum = analyze.groupby_agg(df, group_col="region", agg_col="amount", func="sum")

    # 3. 按 category 平均
    category_avg = analyze.groupby_agg(df, group_col="category", agg_col="amount", func="avg")

    sheets = {
        "原始数据": [df.columns.tolist()] + df.values.tolist(),
        "描述统计": [
            ["指标", "值"],
            ["总行数", summary["shape"][0]],
            ["总列数", summary["shape"][1]],
            ["amount 缺失数", summary["null_count"]["amount"]],
        ],
        "按区域汇总": [region_sum.columns.tolist()] + region_sum.values.tolist(),
        "按品类均值": [category_avg.columns.tolist()] + category_avg.values.tolist(),
    }

    wb = create.create_xlsx(out, sheets)
    for name in wb.sheetnames:
        ws = wb[name]
        styling.apply_header_style(ws)
        styling.auto_fit_columns(ws)
    wb.save(out)
    print(f"saved: {out}")
    return Path(out)


if __name__ == "__main__":
    main()
