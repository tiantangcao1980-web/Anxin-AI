# 跨境定价雷达

> 每 30 分钟抓取 Amazon / Shopify / eBay 竞品定价，与本店 SKU 对比，触发自动调价建议或 BuyBox 失守预警。

## Cookbook 元数据

| 字段 | 值 |
|---|---|
| 调度 | `*/30 * * * *` (Asia/Shanghai) |
| 负责 Persona | [cross-border-ecom](../../plugins/cross-border-ecom/README.md) |
| 模型 | `claude-opus-4-7` |
| Human-in-loop | 是 |

## 人工守门规则

调价幅度 > 10% 必须人工 confirm；BuyBox 失守自动开启 24h 观察期再调价。

## 数据源

| Source | URL |
|---|---|
| Amazon SP-API | `https://sellingpartnerapi-na.amazon.com` |
| Shopify Admin API | `https://{shop}.myshopify.com/admin/api/2024-04/` |
| eBay Browse API | `https://api.ebay.com/buy/browse/v1/` |

## 部署

### 本地（Backend Celery beat）

本 cookbook 已在 `backend/src/tasks/managed_agents/cross_border_pricing_radar.py` 注册；启动 Celery worker + beat 即可生效：

```bash
make celery-up
```

### 云端（Anthropic Managed Agents API）

```bash
export ANTHROPIC_API_KEY=sk-ant-...
bash scripts/deploy-managed-agent.sh cross-border-pricing-radar
```

将上传 `agent.yaml` 到 Anthropic Managed Agents API（`/v1/agents`），由 Anthropic 托管运行。

## 风险守门（与 agent.yaml 中 guardrails 字段对应）

1. **Draft-only** — 仅产出草稿；推送 / 发件 / 价格变更全部走人工 confirm。
2. **Source attribution** — 每条结论附数据源 URL 与抓取时间戳。
3. **Jurisdiction transparency** — 跨境议题显式声明法域，强制人工复核。
4. **No PII leak** — 个人信息脱敏后再外发。

## 修改 cookbook

直接改 `agent.yaml`：
- 调度频率 → `trigger.cron`
- 数据源 → `dataSources`
- 推送渠道 → `outputs[*].channel`
- 升级阈值 → `humanGate`

保存后运行 `python3 scripts/claude-plugin-validate.py managed-agent-cookbooks/cross-border-pricing-radar` 验证。
