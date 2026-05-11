---
name: xlsx
display_name: Excel 表格处理
version: 1.0.0
description: 创建/读取/编辑 .xlsx 文件，含公式、图表、数据透视表、条件格式
category: office
type: tool
author: cowork
license: MIT
triggers:
  - 创建 excel
  - 编辑 xlsx
  - 表格分析
  - 数据透视
  - 财务报表
  - .xlsx 文件
personas:
  - anxin_assistant
  - doc_secretary
  - tax_finance_advisor
  - market_researcher
  - ecommerce_assistant
requires_apps: []
dependencies:
  - openpyxl
  - pandas
keywords:
  - office
  - spreadsheet
  - excel
  - data-analysis
---

# Excel 表格处理技能（xlsx）

> 来源：cowork `skills/xlsx`，已按「安心智能助手」V3 体系做本地化与 persona 适配。
> 引擎：openpyxl 3.1+（读写、公式、图表、样式）+ pandas 2+（分析、透视、清洗）。

## 一、典型业务场景

| 场景 | 触发方 | 典型动作 |
|------|--------|----------|
| 财务报表 | `tax_finance_advisor` / `doc_secretary` | 生成损益表、资产负债表、现金流量表，含 SUM/小计公式 |
| 销售看板 | `market_researcher` / `ecommerce_assistant` | 多 sheet 月度销售明细 + 柱状图 / 饼图 + 同比增长公式 |
| 库存跟踪 | `ecommerce_assistant` | 在库 / 安全库存 / 预警，红绿条件格式 |
| 数据分析 | `market_researcher` / `anxin_assistant` | csv → xlsx，groupby 聚合，pivot_table 多维交叉 |
| 通用文书 | `doc_secretary` | 名册、签到表、工时表 |

## 二、核心能力清单

### 创建 (`helpers/create.py`)
- `create_xlsx(path, sheets)` — 多 sheet 一次写入，sheets 是 `dict[sheet_name, list[list]]`
- `add_formula(ws, cell, formula)` — 写入公式，已做 = 起头 + 危险 token 校验
- `add_chart(ws, chart_type, data_range, anchor)` — bar / line / pie
- `merge_cells(ws, range_str)` — 合并单元格
- `auto_fit_columns(ws)` — 列宽自适应

### 读取 (`helpers/read.py`)
- `read_sheet(path, sheet_name=None) -> pd.DataFrame`
- `read_all_sheets(path) -> dict[str, pd.DataFrame]`
- `read_formulas(path, sheet_name=None) -> dict[str, str]` — `{"A1": "=SUM(B1:B10)"}`
- `read_charts_info(path) -> list[dict]`

### 编辑 (`helpers/edit.py`)
- `update_cell(path, sheet, cell, value)`
- `insert_rows(path, sheet, position, rows)`
- `recalc_formulas(path)` — 清 cached value，让下次打开重新求值

### 分析 (`helpers/analyze.py`，pandas)
- `summarize(df) -> dict` — `describe` + 缺失计数 + 唯一值数
- `groupby_agg(df, group_col, agg_col, func)` — sum/mean/max/min/count
- `pivot_table(df, index, columns, values, aggfunc='sum')`

### 样式 (`helpers/styling.py`)
- `apply_header_style(ws, row=1)` — 加粗 + 灰底 + 居中
- `apply_conditional_format(ws, range_str, rule, format_)` — 红高 / 绿低 / 数据条
- `auto_fit_columns(ws)`

## 三、快速示例

### 创建一个带公式和柱状图的销售表

```python
from skills.office.xlsx.helpers import create, styling

sheets = {
    "2026Q1": [
        ["月份", "华北", "华东", "华南", "合计"],
        ["1月", 120, 80, 95, "=SUM(B2:D2)"],
        ["2月", 135, 92, 110, "=SUM(B3:D3)"],
        ["3月", 158, 105, 124, "=SUM(B4:D4)"],
    ],
}
wb = create.create_xlsx("sales_q1.xlsx", sheets)
ws = wb["2026Q1"]
styling.apply_header_style(ws)
styling.auto_fit_columns(ws)
create.add_chart(ws, "bar", "A1:D4", anchor="G2")
wb.save("sales_q1.xlsx")
```

### 读取 + 分析

```python
from skills.office.xlsx.helpers import read, analyze

df = read.read_sheet("sales_q1.xlsx", "2026Q1")
print(analyze.summarize(df))
print(analyze.groupby_agg(df, group_col="月份", agg_col="华北", func="sum"))
```

### CSV → xlsx + pivot

```python
import pandas as pd
from skills.office.xlsx.helpers import analyze, create

df = pd.read_csv("orders.csv")
pivot = analyze.pivot_table(df, index="region", columns="category", values="amount")
create.create_xlsx("pivot.xlsx", {"pivot": [pivot.columns.tolist()] + pivot.values.tolist()})
```

## 四、模板列表

| 模板 | 说明 | 文件 |
|------|------|------|
| 财务报表 | 三表（损益/资产负债/现金流）+ 标准科目 | `templates/financial_report.md` |
| 销售看板 | 多 sheet（明细/汇总/图表）+ 同比公式 | `templates/sales_dashboard.md` |
| 库存跟踪 | 在库 / 安全库存 / 预警条件格式 | `templates/inventory_tracker.md` |

## 五、公式安全（防注入）

Excel 公式注入是 OWASP 已收录的真实风险。本 skill 在 `create.add_formula` 与 `create_xlsx` 写入时做以下防御：

1. **白名单起头**：用户传入字符串若以 `=` `+` `-` `@` 开头视为公式候选，否则当作纯文本写入。
2. **危险 token 拒绝**：包含 `cmd|`、`/c `、`HYPERLINK(`（带 javascript: / file:// 协议）、`DDE(`、`WEBSERVICE(`、`IMPORTDATA(` 等 token 直接抛 `ValueError("formula injection rejected")`。
3. **来自外部源（CSV / 用户表单）的字符串**：调用 `create.sanitize_external_value(s)`，如以 `=+-@` 开头则前置单引号 `'`，确保 Excel 当文本展示。

参考：[OWASP - CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection)、[Excel external content safety](https://learn.microsoft.com/en-us/deployoffice/security/internet-macros-blocked)。

## 六、依赖与许可

- `openpyxl >= 3.1`（MIT）
- `pandas >= 2.0`（BSD-3-Clause）

技能本体：MIT，沿用 cowork 上游许可。

## 七、与 P5-A（docx）协同

- 公文（`.docx`）→ 由 `skills/office/docx` 处理（A agent 输出）
- 表格（`.xlsx`）→ 本 skill（C agent 输出，当前任务）
- 演示（`.pptx`）→ 由 `skills/office/pptx` 处理（D agent）
- 报告（`.pdf`）→ 由 `skills/office/pdf` 处理（E agent）

四者共享同一 `helpers` 接口风格（create / read / edit / analyze / styling），且都遵守同一份 frontmatter 约定，便于 `skill_registry` 统一加载。
