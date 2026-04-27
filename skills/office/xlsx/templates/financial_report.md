# 财务报表模板（financial_report）

> 适用 persona：`tax_finance_advisor`、`doc_secretary`
> 三表联动：损益表、资产负债表、现金流量表

## Sheet 列表

### 1. `损益表`（Income Statement）

| 列 | 说明 | 示例公式 |
|----|------|----------|
| A 科目 | 营业收入 / 成本 / 费用 / 利润 | — |
| B 本期金额 | 元 | — |
| C 上期金额 | 元 | — |
| D 同比增长 | % | `=(B2-C2)/C2` |

关键小计公式：
- 营业利润 = `=B营业收入 - B营业成本 - B税金附加 - B销售费用 - B管理费用 - B研发费用`
- 利润总额 = `=B营业利润 + B营业外收入 - B营业外支出`
- 净利润 = `=B利润总额 - B所得税费用`

### 2. `资产负债表`（Balance Sheet）

| 区段 | 行 |
|------|----|
| 流动资产 | 货币资金 / 应收账款 / 存货 |
| 非流动资产 | 固定资产 / 无形资产 / 长期股权投资 |
| 流动负债 | 短期借款 / 应付账款 / 应交税费 |
| 非流动负债 | 长期借款 / 应付债券 |
| 所有者权益 | 实收资本 / 资本公积 / 盈余公积 / 未分配利润 |

校验公式（单元格 J1）：
- `=资产合计 - (负债合计 + 所有者权益合计)`，应为 0

### 3. `现金流量表`（Cash Flow）

三大段：经营活动 / 投资活动 / 筹资活动；末行汇总：
- `=经营活动产生现金净额 + 投资活动产生现金净额 + 筹资活动产生现金净额`

## 样式约定

- 表头：调用 `styling.apply_header_style(ws)`，灰底加粗
- 同比列：> 0 红色 / < 0 绿色（中国会计习惯：红正绿负）
  - `styling.apply_conditional_format(ws, "D2:D50", "high", threshold=0, color_high="FFC7CE")`
  - `styling.apply_conditional_format(ws, "D2:D50", "low", threshold=0, color_low="C6EFCE")`
- 列宽：`styling.auto_fit_columns(ws)`

## 安全提醒

如果科目名称、附注从外部 CSV / 用户输入导入，必须走 `create.sanitize_external_value`，
否则 `=cmd|/c calc.exe!A1` 这类字符串会被 Excel 解析为公式触发 RCE。
