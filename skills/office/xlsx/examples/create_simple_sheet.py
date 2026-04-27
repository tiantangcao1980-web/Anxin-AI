# -*- coding: utf-8 -*-
"""示例 1：创建一个最简单的多 sheet xlsx，含 SUM 公式。

运行：python -m skills.office.xlsx.examples.create_simple_sheet
"""

from __future__ import annotations

from pathlib import Path

from skills.office.xlsx.helpers import create, styling


def main(out: str = "/tmp/anxin_simple.xlsx") -> Path:
    sheets = {
        "员工名册": [
            ["工号", "姓名", "部门", "月薪"],
            ["E001", "张三", "法务", 18000],
            ["E002", "李四", "财税", 16500],
            ["E003", "王五", "市场", 22000],
            ["合计", "", "", "=SUM(D2:D4)"],
        ],
        "联系方式": [
            ["工号", "手机", "邮箱"],
            ["E001", "13800138001", "zhang@anxin.com"],
            ["E002", "13800138002", "li@anxin.com"],
        ],
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
