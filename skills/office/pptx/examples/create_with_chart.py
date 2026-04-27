# -*- coding: utf-8 -*-
"""示例 2：创建带图表（柱状 + 饼图）的 PPT。"""

from __future__ import annotations

from pathlib import Path

from skills.office.pptx.helpers.create import create_pptx


def main() -> str:
    out = Path(__file__).parent / "output_with_chart.pptx"
    return create_pptx(
        str(out),
        slides=[
            {"layout": "title_only", "title": "Q1 业绩复盘"},
            {
                "layout": "title_content",
                "title": "月度营收（万元）",
                "chart": {
                    "type": "bar",
                    "categories": ["1月", "2月", "3月"],
                    "series": [("营收", [120, 150, 210])],
                },
            },
            {
                "layout": "title_content",
                "title": "客户构成",
                "chart": {
                    "type": "pie",
                    "categories": ["小微企业", "中型企业", "大型客户"],
                    "series": [("客户数", [60, 30, 10])],
                },
            },
        ],
    )


if __name__ == "__main__":
    print(main())
