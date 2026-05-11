# 销售数据看板模板（sales_dashboard）

> 适用 persona：`market_researcher`、`ecommerce_assistant`
> 多 sheet 销售明细 + 汇总 + 图表，月度 / 季度 / 年度均可复用。

## Sheet 列表

### 1. `明细`（Detail）

| 字段 | 类型 | 说明 |
|------|------|------|
| 订单号 | 字符串 | 主键 |
| 下单日期 | 日期 | yyyy-mm-dd |
| 渠道 | 字符串 | 天猫 / 京东 / 抖音 / 私域 |
| 品类 | 字符串 | — |
| 单价 | 数字 | — |
| 数量 | 数字 | — |
| 金额 | 公式 | `=单价 * 数量` |

### 2. `月度汇总`（Monthly Summary）

由 `helpers.analyze.pivot_table` 生成：
```python
pivot = pivot_table(
    df_detail,
    index="月份",
    columns="渠道",
    values="金额",
    aggfunc="sum",
)
```

附加列：
- 合计 = `=SUM(B2:E2)`
- 同比 = `=(B2 - 去年同月 B2) / 去年同月 B2`

### 3. `图表`（Charts）

调用 `helpers.create.add_chart`：
- 月度趋势：line chart，data_range="月度汇总!A1:E13"
- 渠道占比：pie chart，data_range="月度汇总最后一行"
- 品类对比：bar chart

## 配色（避免 AI 通用色）

主色 `#FF6B35`（暖橙，安心品牌色）；
辅色 `#1B4332`（深绿，盈利）/ `#9D0208`（深红，亏损）；
表头灰 `#D9D9D9`。

## 样式

- `styling.apply_header_style(ws_summary)`
- 同比列：`apply_conditional_format(ws, "F2:F13", "color_scale")`
- 列宽：`auto_fit_columns(ws)`

## 性能

明细行数 > 10w 时，建议先用 pandas 在内存里做 `pivot_table`，再调 `create_xlsx` 一次性写汇总，
不要在 openpyxl 里逐行累加（慢 5-10 倍）。
