# 合同续约监控

> 扫描进入 60 天到期窗口的合同，评估涨幅 / 谈判筹码 / 续约风险，生成续约建议。

## Cookbook 元数据

| 字段 | 值 |
|---|---|
| 调度 | `0 9 * * 1` (Asia/Shanghai) |
| 负责 Persona | [contract-steward](../../plugins/contract-steward/README.md) |
| 模型 | `claude-opus-4-7` |
| Human-in-loop | 是 |

## 人工守门规则

续约函与价格变更必须由合同负责人 + 法务双签；> 100 万走老板审批。

## 数据源

| Source | URL |
|---|---|
| ERP 合同表 | `internal://erp/contracts` |
| DMS 合同文件 | `internal://dms/contracts` |

## 部署

### 本地（Backend Celery beat）

本 cookbook 已在 `backend/src/tasks/managed_agents/contract_renewal_watcher.py` 注册；启动 Celery worker + beat 即可生效：

```bash
make celery-up
```

### 云端（Anthropic Managed Agents API）

```bash
export ANTHROPIC_API_KEY=sk-ant-...
bash scripts/deploy-managed-agent.sh contract-renewal-watcher
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

保存后运行 `python3 scripts/claude-plugin-validate.py managed-agent-cookbooks/contract-renewal-watcher` 验证。
