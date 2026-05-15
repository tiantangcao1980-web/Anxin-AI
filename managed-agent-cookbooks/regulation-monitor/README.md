# 中国法规监控

> 每日扫描人大、国务院、市场监管总局公告，识别影响业务的新法规，自动生成合规变更摘要推送到飞书。

## Cookbook 元数据

| 字段 | 值 |
|---|---|
| 调度 | `0 8 * * *` (Asia/Shanghai) |
| 负责 Persona | [legal-advisor](../../plugins/legal-advisor/README.md) |
| 模型 | `claude-opus-4-7` |
| Human-in-loop | 是 |

## 人工守门规则

推送前由值班律师 confirm；生效日 ≤ 30 天的强制提醒。

## 数据源

| Source | URL |
|---|---|
| 人大法规库 | `http://www.npc.gov.cn/npc/c2/` |
| 国务院公报 | `https://www.gov.cn/zhengce/` |
| 市场监督管理总局 | `https://www.samr.gov.cn/zw/zfxxgk/` |

## 部署

### 本地（Backend Celery beat）

本 cookbook 已在 `backend/src/tasks/managed_agents/regulation_monitor.py` 注册；启动 Celery worker + beat 即可生效：

```bash
make celery-up
```

### 云端（Anthropic Managed Agents API）

```bash
export ANTHROPIC_API_KEY=sk-ant-...
bash scripts/deploy-managed-agent.sh regulation-monitor
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

保存后运行 `python3 scripts/claude-plugin-validate.py managed-agent-cookbooks/regulation-monitor` 验证。
