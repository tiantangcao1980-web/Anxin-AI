---
name: contract-renewal-watcher
type: managed-agent-reference
ownerPersona: contract-steward
cookbookPath: ../../../managed-agent-cookbooks/contract-renewal-watcher
schedule: 0 9 * * 1
---

# Managed Agent: contract-renewal-watcher

本文档是 [contract-steward](../README.md) 拥有的无人值守 managed agent 的**引用**。
真实 spec 在 [`managed-agent-cookbooks/contract-renewal-watcher/`](../../../managed-agent-cookbooks/contract-renewal-watcher/)。

## 调度
- **Cron**: `0 9 * * 1` (Asia/Shanghai)
- **触发方式**: schedule（定时）/ event（事件，预留）

## 与本 persona 的关系
- 本 cookbook 产出的草稿默认路由到 **contract-steward** 的工作台 inbox。
- 草稿由 contract-steward 的执业画像（CLAUDE.md）应用风格 / 红线 / 升级阈值。
- 用户在 contract-steward 工作台 confirm 后，cookbook 才会执行外发 / 落地动作。

## 一键部署

```bash
# 本地 Celery（推荐先用 dry-run）
bash scripts/deploy-managed-agent.sh contract-renewal-watcher --local

# 云端 Anthropic Managed Agents API
bash scripts/deploy-managed-agent.sh contract-renewal-watcher
```

## 修改 spec
直接改 [`../../../managed-agent-cookbooks/contract-renewal-watcher/agent.yaml`](../../../managed-agent-cookbooks/contract-renewal-watcher/agent.yaml)。
