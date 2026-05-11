# -*- coding: utf-8 -*-
"""示例 3：基于 DataFrame 做 pivot，再写回 xlsx。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from skills.office.xlsx.helpers import analyze, create, styling


def main(out: str = "/tmp/anxin_pivot.xlsx") -> Path:
    raw = pd.DataFrame(
        {
            "region": ["华北", "华北", "华东", "华东", "华南", "华南"],
            "category": ["合同", "财税", "合同", "财税", "合同", "财税"],
            "amount": [12000, 8000, 15000, 9500, 11000, 7800],
        }
    )

    pivot = analyze.pivot_table(
        raw,
        index="region",
        columns="category",
        values="amount",
        aggfunc="sum",
    )
    pivot["合计"] = pivot.sum(axis=1)

    # pivot 的 index 当成第一列写出来
    rows = [["region"] + pivot.columns.tolist()]
    for idx, row in pivot.iterrows():
        rows.append([idx] + row.tolist())

    wb = create.create_xlsx(out, {"按区按类汇总": rows})
    ws = wb["按区按类汇总"]
    styling.apply_header_style(ws)
    styling.auto_fit_columns(ws)
    wb.save(out)
    print(f"saved: {out}")
    return Path(out)


if __name__ == "__main__":
    main()
