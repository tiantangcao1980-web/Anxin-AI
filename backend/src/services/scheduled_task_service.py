# -*- coding: utf-8 -*-
"""
ScheduledTask 服务层 —— D-1 定时任务管理后端

职责：list / get / create / toggle / delete 真实落库，按 org 隔离。

next_run_at 计算：
    venv 当前 **没有** croniter 依赖（已实测 `import croniter` 失败）。
    为了不引入新依赖即满足契约，本模块内置一个轻量 cron 解析
    ``compute_next_run``，支持标准 5 段 cron 的常见子集：
        分 时 日 月 周
    每段支持 ``*``、单值、逗号列表（如 ``1,15``）；步进 ``*/n`` 与区间
    暂未支持（落地任务的 cron 均为固定时刻，不需要）。
    若未来装上 croniter，可在 ``compute_next_run`` 顶部直接改用它。

执行（cron 真跑 / agent persona 真运行）= P-later：
    本服务不写 last_run_at / last_run_ok，也无调度循环消费本表。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.scheduled_task import ScheduledTask

# 各 ScheduleKind 默认 agent persona（创建时未显式传 persona 时的兜底）
DEFAULT_PERSONA_BY_KIND: dict[str, str] = {
    "contract_expiry_alert": "legal",
    "case_status_daily": "legal",
    "sentiment_weekly": "intelligence",
    "compliance_monthly": "legal",
}

# 中文星期，用于 cron_human
_WEEKDAY_CN = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]


class ScheduledTaskError(Exception):
    """业务异常基类。"""


class ScheduledTaskNotFoundError(ScheduledTaskError):
    """任务不存在（或不属于当前 org）。"""


# ---------------------------------------------------------------------------
# cron 工具
# ---------------------------------------------------------------------------


def _parse_field(field: str, low: int, high: int) -> list[int]:
    """解析单个 cron 段为允许值列表。支持 ``*`` 与逗号列表与单值。"""
    if field == "*":
        return list(range(low, high + 1))
    values: list[int] = []
    for part in field.split(","):
        part = part.strip()
        if not part or not part.lstrip("-").isdigit():
            # 不支持的语法（区间 / 步进），退化为「全部允许」，
            # 保证 compute_next_run 不抛错（最坏给出偏早的 next_run）。
            return list(range(low, high + 1))
        v = int(part)
        if low <= v <= high:
            values.append(v)
    return sorted(set(values)) or list(range(low, high + 1))


def compute_next_run(cron: str, *, after: datetime | None = None) -> datetime:
    """从标准 5 段 cron 计算 ``after`` 之后的下一次触发（UTC, tz-aware）。

    croniter 不可用时的内置实现；逐分钟向前扫描（上限 ~366 天），
    对固定时刻的提醒类 cron 足够。
    """
    now = after or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    parts = cron.split()
    if len(parts) != 5:
        # 非法 cron：给一个安全占位（24h 后），并由调用方记录
        return now + timedelta(hours=24)

    minutes = _parse_field(parts[0], 0, 59)
    hours = _parse_field(parts[1], 0, 23)
    doms = _parse_field(parts[2], 1, 31)
    months = _parse_field(parts[3], 1, 12)
    dows = _parse_field(parts[4], 0, 6)  # 0 = 周日
    dom_restricted = parts[2] != "*"
    dow_restricted = parts[4] != "*"

    # 从下一分钟开始扫描
    candidate = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    limit = candidate + timedelta(days=366)
    while candidate <= limit:
        if candidate.month in months and candidate.hour in hours and candidate.minute in minutes:
            dom_ok = candidate.day in doms
            # cron 语义：day-of-month 与 day-of-week 都受限时取「或」
            dow_ok = (candidate.weekday() + 1) % 7 in dows
            if dom_restricted and dow_restricted:
                day_match = dom_ok or dow_ok
            else:
                day_match = dom_ok and dow_ok
            if day_match:
                return candidate
        candidate += timedelta(minutes=1)
    # 理论不可达
    return now + timedelta(hours=24)


def humanize_cron(cron: str) -> str:
    """把固定时刻 cron 转为简短中文串；无法识别时回退原表达式。"""
    parts = cron.split()
    if len(parts) != 5:
        return cron
    minute, hour, dom, month, dow = parts

    def _hm() -> str | None:
        if minute.isdigit() and hour.isdigit():
            return f"{int(hour):02d}:{int(minute):02d}"
        return None

    hm = _hm()
    if hm is None:
        return cron

    # 每天
    if dom == "*" and month == "*" and dow == "*":
        return f"每天 {hm}"
    # 每周固定星期
    if dom == "*" and month == "*" and dow.isdigit():
        return f"每{_WEEKDAY_CN[int(dow) % 7]} {hm}"
    # 工作日
    if dom == "*" and month == "*" and dow in ("1-5", "1,2,3,4,5"):
        return f"工作日 {hm}"
    # 每月某日
    if dom.isdigit() and month == "*" and dow == "*":
        return f"每月 {int(dom)} 日 {hm}"
    # 每年某月某日
    if dom.isdigit() and month.isdigit() and dow == "*":
        return f"每年 {int(month)} 月 {int(dom)} 日 {hm}"
    return cron


# ---------------------------------------------------------------------------
# 服务
# ---------------------------------------------------------------------------


class ScheduledTaskService:
    """定时任务管理服务（按 org 隔离）。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_org(self, org_id: str | None) -> list[ScheduledTask]:
        stmt = select(ScheduledTask).where(ScheduledTask.org_id == org_id)
        stmt = stmt.order_by(ScheduledTask.created_at.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_for_org(self, task_id: str, org_id: str | None) -> ScheduledTask:
        stmt = select(ScheduledTask).where(
            ScheduledTask.id == task_id,
            ScheduledTask.org_id == org_id,
        )
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if task is None:
            raise ScheduledTaskNotFoundError(task_id)
        return task

    async def create(
        self,
        *,
        org_id: str | None,
        created_by: str | None,
        name: str,
        kind: str,
        cron: str,
        agent_persona: str | None = None,
        cron_human: str | None = None,
        status: str = "active",
        config: dict | None = None,
    ) -> ScheduledTask:
        persona = agent_persona or DEFAULT_PERSONA_BY_KIND.get(kind, "")
        task = ScheduledTask(
            org_id=org_id,
            created_by=created_by,
            name=name,
            kind=kind,
            cron=cron,
            cron_human=cron_human or humanize_cron(cron),
            status=status,
            agent_persona=persona,
            next_run_at=compute_next_run(cron),
            config=config or {},
        )
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def toggle(
        self, task_id: str, org_id: str | None, new_status: str
    ) -> ScheduledTask:
        """切换 active|paused|failed。切到 active 时重算 next_run_at。"""
        task = await self.get_for_org(task_id, org_id)
        task.status = new_status
        if new_status == "active":
            task.next_run_at = compute_next_run(task.cron)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def delete(self, task_id: str, org_id: str | None) -> None:
        task = await self.get_for_org(task_id, org_id)
        await self.db.delete(task)
        await self.db.flush()
