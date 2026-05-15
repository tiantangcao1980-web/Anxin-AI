# Managed Agent Celery Tasks

从 `managed-agent-cookbooks/*/agent.yaml` 落地的 Celery 任务。

## 启动

```bash
cd backend

# Worker
celery -A src.services.task_orchestrator.celery_app:celery_app worker -l info -Q agent_tasks

# Beat（定时调度）
celery -A src.services.task_orchestrator.celery_app:celery_app beat -l info
```

## 任务清单

| Cookbook | Persona | Cron | Task |
|---|---|---|---|
| regulation-monitor | legal-advisor | `0 8 * * *` | `managed_agents.regulation_monitor.run` |
| contract-renewal-watcher | contract-steward | `0 9 * * 1` | `managed_agents.contract_renewal_watcher.run` |
| ar-aging-watcher | finance-tax-advisor | `0 9 * * 1-5` | `managed_agents.ar_aging_watcher.run` |
| cross-border-pricing-radar | cross-border-ecom | `*/30 * * * *` | `managed_agents.cross_border_pricing_radar.run` |

## 守门规则

每个 task 的 `run()` 只产出 staged draft（写到 `.claude/managed-agent-runs/<cookbook>/`），
**不会主动外发**。外发动作必须经 persona 工作台 inbox 中的人工 confirm。

## 新增 cookbook

1. 在 `managed-agent-cookbooks/<name>/agent.yaml` 创建 spec
2. 在本目录新增 `<name_underscore>.py`，模仿现有 4 个文件结构
3. 跑 `python3 scripts/claude-plugin-validate.py managed-agent-cookbooks/<name>` 校验
4. 重启 Celery worker + beat
