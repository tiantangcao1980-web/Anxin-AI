---
name: cross-border-pricing-radar
type: managed-agent-reference
ownerPersona: cross-border-ecom
cookbookPath: ../../../managed-agent-cookbooks/cross-border-pricing-radar
schedule: */30 * * * *
---

# Managed Agent: cross-border-pricing-radar

本文档是 [cross-border-ecom](../README.md) 拥有的无人值守 managed agent 的**引用**。
真实 spec 在 [`managed-agent-cookbooks/cross-border-pricing-radar/`](../../../managed-agent-cookbooks/cross-border-pricing-radar/)。

## 调度
- **Cron**: `*/30 * * * *` (Asia/Shanghai)
- **触发方式**: schedule（定时）/ event（事件，预留）

## 与本 persona 的关系
- 本 cookbook 产出的草稿默认路由到 **cross-border-ecom** 的工作台 inbox。
- 草稿由 cross-border-ecom 的执业画像（CLAUDE.md）应用风格 / 红线 / 升级阈值。
- 用户在 cross-border-ecom 工作台 confirm 后，cookbook 才会执行外发 / 落地动作。

## 一键部署

```bash
# 本地 Celery（推荐先用 dry-run）
bash scripts/deploy-managed-agent.sh cross-border-pricing-radar --local

# 云端 Anthropic Managed Agents API
bash scripts/deploy-managed-agent.sh cross-border-pricing-radar
```

## 修改 spec
直接改 [`../../../managed-agent-cookbooks/cross-border-pricing-radar/agent.yaml`](../../../managed-agent-cookbooks/cross-border-pricing-radar/agent.yaml)。
