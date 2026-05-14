#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ldap_sync_loop —— LDAP / AD 同步守护进程

设计见 docs/v3/enterprise-cluster-design.md §5.3
              deploy/enterprise-onprem/LDAP_SYNC.md

环境变量（在 docker-compose.onprem.yml 的 ldap-sync service 注入）::

    LDAP_URL=ldap://ad.corp.example:389
    LDAP_BIND_DN=CN=anxin-sync,OU=...,DC=corp,DC=example
    LDAP_BIND_PASSWORD=...
    LDAP_USER_BASE_DN=OU=Users,DC=corp,DC=example
    LDAP_DEPT_BASE_DN=OU=Departments,DC=corp,DC=example
    LDAP_SYNC_INTERVAL_SEC=300              # 默认 5 min
    LDAP_SYNC_ORG_ID=<org_id>               # 必填：同步到哪个租户
    LDAP_SYNC_CONFLICT_STRATEGY=ldap-wins   # 可选

用法::

    # 一次性
    python scripts/ldap_sync_loop.py --once

    # dry-run（不写库，只打印）
    python scripts/ldap_sync_loop.py --once --dry-run

    # 守护进程：每隔 LDAP_SYNC_INTERVAL_SEC 同步一次
    python scripts/ldap_sync_loop.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path

# 让脚本能 import src.*
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from src.core.database import async_session_maker  # noqa: E402
from src.services.enterprise_directory import (  # noqa: E402
    InMemoryLdapClient,
    Ldap3Client,
    Ldap3Config,
    LdapNotAvailable,
    LdapSyncService,
)

logger = logging.getLogger("ldap_sync")


def _build_client(args: argparse.Namespace):
    """根据参数 / 环境变量构造 LDAP 客户端。

    ``--use-fake`` 用于本地调试和单测，避免连真 LDAP。
    """
    if args.use_fake:
        logger.warning("使用 InMemoryLdapClient（仅供调试，不会拉真 LDAP）")
        return InMemoryLdapClient()
    cfg = Ldap3Config(
        url=os.environ.get("LDAP_URL", ""),
        bind_dn=os.environ.get("LDAP_BIND_DN", ""),
        bind_password=os.environ.get("LDAP_BIND_PASSWORD", ""),
        user_base_dn=os.environ.get("LDAP_USER_BASE_DN", ""),
        dept_base_dn=os.environ.get("LDAP_DEPT_BASE_DN", ""),
        use_ssl=os.environ.get("LDAP_USE_SSL", "true").lower() == "true",
    )
    missing = [k for k in ("url", "bind_dn", "user_base_dn", "dept_base_dn") if not getattr(cfg, k)]
    if missing:
        raise SystemExit(
            f"缺少必需环境变量: {', '.join('LDAP_' + k.upper() for k in missing)}"
        )
    return Ldap3Client(cfg)


async def _run_once(args: argparse.Namespace) -> int:
    """执行一次同步，返回 0 = 成功，非 0 = 有错。"""
    org_id = args.org_id or os.environ.get("LDAP_SYNC_ORG_ID", "")
    if not org_id:
        logger.error("必须通过 --org-id 或 LDAP_SYNC_ORG_ID 指定目标租户")
        return 2

    strategy = args.strategy or os.environ.get(
        "LDAP_SYNC_CONFLICT_STRATEGY", "ldap-wins"
    )

    try:
        client = _build_client(args)
    except LdapNotAvailable as exc:
        logger.error("LDAP 不可用: %s", exc)
        return 3

    def _audit(payload: dict) -> None:
        logger.info("ldap_sync 报告: %s", json.dumps(payload, ensure_ascii=False))

    try:
        async with async_session_maker() as session:
            svc = LdapSyncService(
                session,
                org_id=org_id,
                client=client,
                conflict_strategy=strategy,
                audit_hook=_audit,
            )
            report = await svc.sync_once(dry_run=args.dry_run)
            if not args.dry_run:
                await session.commit()
        # 有错也视为非 0
        return 0 if not report.errors else 1
    except Exception:
        logger.exception("ldap_sync 异常")
        return 4


async def _run_forever(args: argparse.Namespace) -> int:
    """守护进程模式：循环 sync，每次间隔 LDAP_SYNC_INTERVAL_SEC。"""
    interval = int(os.environ.get("LDAP_SYNC_INTERVAL_SEC", "300"))
    if interval < 30:
        logger.warning("LDAP_SYNC_INTERVAL_SEC 太小（%ds），强制提升到 30s", interval)
        interval = 30

    stop = asyncio.Event()
    loop = asyncio.get_event_loop()
    for sig_name in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(getattr(signal, sig_name), stop.set)
        except (NotImplementedError, AttributeError):
            # Windows / 部分环境不支持 signal handler
            pass

    last_rc = 0
    while not stop.is_set():
        rc = await _run_once(args)
        last_rc = rc
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
    logger.info("收到退出信号，停止守护")
    return last_rc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--once", action="store_true", help="只跑一次后退出")
    p.add_argument("--dry-run", action="store_true", help="不写库")
    p.add_argument("--org-id", default=None, help="目标租户 org_id")
    p.add_argument(
        "--strategy",
        default=None,
        choices=["ldap-wins", "local-wins", "merge"],
        help="冲突策略",
    )
    p.add_argument(
        "--use-fake",
        action="store_true",
        help="使用 InMemoryLdapClient（仅调试）",
    )
    p.add_argument("--log-level", default="INFO")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if args.once:
        return asyncio.run(_run_once(args))
    return asyncio.run(_run_forever(args))


if __name__ == "__main__":
    raise SystemExit(main())
