# -*- coding: utf-8 -*-
"""示例 2：创建带柱状图的销售 xlsx。"""

from __future__ import annotations

from pathlib import Path

from skills.office.xlsx.helpers import create, styling


def main(out: str = "/tmp/anxin_sales.xlsx") -> Path:
    sheets = {
        "2026Q1": [
            ["月份", "华北", "华东", "华南", "合计"],
            ["1月", 120, 80, 95, "=SUM(B2:D2)"],
            ["2月", 135, 92, 110, "=SUM(B3:D3)"],
            ["3月", 158, 105, 124, "=SUM(B4:D4)"],
        ],
    }
    wb = create.create_xlsx(out, sheets)
    ws = wb["2026Q1"]
    styling.apply_header_style(ws)
    styling.auto_fit_columns(ws)
    create.add_chart(
        ws,
        chart_type="bar",
        data_range="A1:D4",
        anchor="G2",
        title="2026Q1 各区销售（万元）",
    )
    wb.save(out)
    print(f"saved: {out}")
    return Path(out)


if __name__ == "__main__":
    main()
