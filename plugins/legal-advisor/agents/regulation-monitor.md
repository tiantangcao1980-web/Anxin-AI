---
name: regulation-monitor
type: managed-agent-reference
ownerPersona: legal-advisor
cookbookPath: ../../../managed-agent-cookbooks/regulation-monitor
schedule: 0 8 * * *
---

# Managed Agent: regulation-monitor

本文档是 [legal-advisor](../README.md) 拥有的无人值守 managed agent 的**引用**。
真实 spec 在 [`managed-agent-cookbooks/regulation-monitor/`](../../../managed-agent-cookbooks/regulation-monitor/)。

## 调度
- **Cron**: `0 8 * * *` (Asia/Shanghai)
- **触发方式**: schedule（定时）/ event（事件，预留）

## 与本 persona 的关系
- 本 cookbook 产出的草稿默认路由到 **legal-advisor** 的工作台 inbox。
- 草稿由 legal-advisor 的执业画像（CLAUDE.md）应用风格 / 红线 / 升级阈值。
- 用户在 legal-advisor 工作台 confirm 后，cookbook 才会执行外发 / 落地动作。

## 一键部署

```bash
# 本地 Celery（推荐先用 dry-run）
bash scripts/deploy-managed-agent.sh regulation-monitor --local

# 云端 Anthropic Managed Agents API
bash scripts/deploy-managed-agent.sh regulation-monitor
```

## 修改 spec
直接改 [`../../../managed-agent-cookbooks/regulation-monitor/agent.yaml`](../../../managed-agent-cookbooks/regulation-monitor/agent.yaml)。
