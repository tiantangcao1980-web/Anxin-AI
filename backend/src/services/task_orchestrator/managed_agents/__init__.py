# -*- coding: utf-8 -*-
"""
managed_agents —— 把 managed-agent-cookbooks/*/agent.yaml 落地为 Celery 任务

每个 cookbook 对应一个本模块下的 task module：

    managed-agent-cookbooks/regulation-monitor/agent.yaml
        ↓ deploy-managed-agent.sh --local
    backend/src/services/task_orchestrator/managed_agents/regulation_monitor.py
        ↓ celery worker + beat
    每天 08:00 Asia/Shanghai 触发

约定：
    - 每个 task module 暴露 ``run(cookbook_yaml_path: str) -> dict``
    - Celery beat 调度由 ``register_beat_schedule(celery_app)`` 统一注入
    - 所有任务都必须遵守 cookbook agent.yaml 中的 guardrails 与 humanGate
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from celery import Celery

COOKBOOK_DIR = Path(__file__).resolve().parents[4] / "managed-agent-cookbooks"


def _load(cookbook: str) -> dict:
    path = COOKBOOK_DIR / cookbook / "agent.yaml"
    if not path.exists():
        raise FileNotFoundError(f"cookbook not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def register_beat_schedule(celery_app: "Celery") -> None:
    """把 cookbook 的 cron 注入到 celery beat。

    在 task_orchestrator/celery_app.py 中调用：

        from src.services.task_orchestrator.managed_agents import register_beat_schedule
        register_beat_schedule(celery_app)
    """
    from celery.schedules import crontab

    if not COOKBOOK_DIR.exists():
        return

    schedule: dict = {}
    for cb_dir in sorted(COOKBOOK_DIR.glob("*/")):
        ay = cb_dir / "agent.yaml"
        if not ay.exists():
            continue
        meta = yaml.safe_load(ay.read_text(encoding="utf-8"))
        cron_expr = meta["trigger"]["cron"]
        parts = cron_expr.split()
        if len(parts) != 5:
            continue
        minute, hour, dom, month, dow = parts
        task_name = f"managed_agents.{cb_dir.name.replace('-', '_')}.run"
        schedule[f"managed_{cb_dir.name}"] = {
            "task": task_name,
            "schedule": crontab(
                minute=minute, hour=hour,
                day_of_month=dom, month_of_year=month, day_of_week=dow,
            ),
            "args": (cb_dir.name,),
        }
    # 内置周期任务：审计 JSONL ↔ DB 对账（每小时）
    schedule["governance_audit_reconcile_hourly"] = {
        "task": "managed_agents.audit_reconcile.run",
        "schedule": crontab(minute="7"),     # 每小时第 7 分
        "args": (1,),                        # since_days=1
    }
    # ConfirmTicket TTL 过期扫描（每 5 分钟）
    schedule["governance_confirm_expire_5min"] = {
        "task": "managed_agents.confirm_expire.run",
        "schedule": crontab(minute="*/5"),
    }

    celery_app.conf.beat_schedule = {
        **(celery_app.conf.beat_schedule or {}),
        **schedule,
    }
