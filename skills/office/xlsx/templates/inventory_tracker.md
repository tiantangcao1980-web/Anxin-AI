# 库存跟踪模板（inventory_tracker）

> 适用 persona：`ecommerce_assistant`
> SKU 维度的实时库存 + 安全库存预警 + 补货建议。

## Sheet 列表

### 1. `库存现状`（Stock）

| 列 | 字段 | 公式 / 说明 |
|----|------|-------------|
| A | SKU | — |
| B | 商品名 | — |
| C | 仓库 | 上海 / 广州 / 北京 |
| D | 在库数 | — |
| E | 在途数 | — |
| F | 安全库存 | — |
| G | 可用库存 | `=D + E` |
| H | 缺口 | `=F - G` |
| I | 是否预警 | `=IF(G < F, "预警", "正常")` |
| J | 建议补货 | `=MAX(0, F * 1.5 - G)` |

### 2. `出入库流水`（Movement）

| 字段 | 说明 |
|------|------|
| 单号 | 主键 |
| 日期 | — |
| SKU | 外键 → 库存现状.A |
| 类型 | 入库 / 出库 / 调拨 |
| 数量 | — |
| 经办人 | — |

### 3. `周库存周转`（Turnover）

由 `helpers.analyze.groupby_agg` 按 SKU 汇总周出库量，再算：
- 周转率 = `=出库量 / 平均库存`

## 条件格式（核心价值）

| 列 | 规则 | 颜色 |
|----|------|------|
| H 缺口 | > 0 | 红 `#FFC7CE` |
| I 是否预警 | = "预警" | 红底白字 |
| G 可用库存 | < 安全库存 50% | 深红 `#E06666` |

调用：
```python
from skills.office.xlsx.helpers import styling

styling.apply_conditional_format(ws, "H2:H1000", "high", threshold=0)
styling.apply_conditional_format(ws, "G2:G1000", "color_scale")
```

## 自动化补货链路（可选）

可与「P2 task_orchestrator」联动：
- 每日 9:00 跑读 `库存现状`，筛选 `H > 0` 的 SKU
- 推送到飞书 / 钉钉群（P3 IM gateway）
- 生成补货单 docx（P5-A）+ 物流面单 pdf（P5-E）
