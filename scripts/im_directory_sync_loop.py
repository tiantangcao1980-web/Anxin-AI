#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
im_directory_sync_loop —— 飞书 / 钉钉 / 企业微信 通讯录同步守护进程

配合 backend/src/services/enterprise_directory/im_directory_clients.py 使用。
每家 IM 平台暴露 ``LdapClient`` 协议，直接喂给 ``LdapSyncService`` 即可。

环境变量（按 provider 分组）::

    # 通用
    IM_SYNC_ORG_ID=<org_id>                  # 必填
    IM_SYNC_INTERVAL_SEC=300                 # 默认 5min
    IM_SYNC_CONFLICT_STRATEGY=ldap-wins      # 可选

    # 飞书
    FEISHU_APP_ID=cli_xxx
    FEISHU_APP_SECRET=...

    # 钉钉
    DINGTALK_APP_KEY=ding_xxx
    DINGTALK_APP_SECRET=...

    # 企业微信
    WECOM_CORP_ID=ww_xxx
    WECOM_CONTACTS_SECRET=...

用法::

    # 飞书，一次性
    python scripts/im_directory_sync_loop.py --provider feishu --once

    # 钉钉，dry-run（不写库）
    python scripts/im_directory_sync_loop.py --provider dingtalk --once --dry-run

    # 企业微信，守护进程
    python scripts/im_directory_sync_loop.py --provider wecom
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from src.core.database import async_session_maker  # noqa: E402
from src.services.enterprise_directory import (  # noqa: E402
    DingtalkConfig,
    DingtalkDirectoryClient,
    FeishuConfig,
    FeishuDirectoryClient,
    ImDirectoryUnavailable,
    LdapSyncService,
    WecomConfig,
    WecomDirectoryClient,
)

logger = logging.getLogger("im_directory_sync")


def _build_client(provider: str):
    if provider == "feishu":
        cfg = FeishuConfig(
            app_id=os.environ.get("FEISHU_APP_ID", ""),
            app_secret=os.environ.get("FEISHU_APP_SECRET", ""),
        )
        return FeishuDirectoryClient(cfg)
    if provider == "dingtalk":
        cfg = DingtalkConfig(
            app_key=os.environ.get("DINGTALK_APP_KEY", ""),
            app_secret=os.environ.get("DINGTALK_APP_SECRET", ""),
        )
        return DingtalkDirectoryClient(cfg)
    if provider == "wecom":
        cfg = WecomConfig(
            corp_id=os.environ.get("WECOM_CORP_ID", ""),
            contacts_secret=os.environ.get("WECOM_CONTACTS_SECRET", ""),
        )
        return WecomDirectoryClient(cfg)
    raise SystemExit(f"未知 provider: {provider}")


async def _run_once(args: argparse.Namespace) -> int:
    org_id = args.org_id or os.environ.get("IM_SYNC_ORG_ID", "")
    if not org_id:
        logger.error("必须通过 --org-id 或 IM_SYNC_ORG_ID 指定目标租户")
        return 2

    strategy = args.strategy or os.environ.get(
        "IM_SYNC_CONFLICT_STRATEGY", "ldap-wins"
    )

    try:
        client = _build_client(args.provider)
    except ImDirectoryUnavailable as exc:
        logger.error("%s 客户端不可用：%s", args.provider, exc)
        return 3

    def _audit(payload: dict) -> None:
        logger.info(
            "im_sync(%s) 报告: %s",
            args.provider,
            json.dumps(payload, ensure_ascii=False),
        )

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
        return 0 if not report.errors else 1
    except Exception:
        logger.exception("im_sync 异常 provider=%s", args.provider)
        return 4


async def _run_forever(args: argparse.Namespace) -> int:
    interval = int(os.environ.get("IM_SYNC_INTERVAL_SEC", "300"))
    if interval < 30:
        logger.warning("IM_SYNC_INTERVAL_SEC 太小（%ds），强制提升到 30s", interval)
        interval = 30

    stop = asyncio.Event()
    loop = asyncio.get_event_loop()
    for sig_name in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(getattr(signal, sig_name), stop.set)
        except (NotImplementedError, AttributeError):
            pass

    last_rc = 0
    while not stop.is_set():
        rc = await _run_once(args)
        last_rc = rc
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
    logger.info("收到退出信号，停止 im_sync 守护")
    return last_rc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--provider",
        required=True,
        choices=["feishu", "dingtalk", "wecom"],
        help="IM 平台",
    )
    p.add_argument("--once", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--org-id", default=None)
    p.add_argument(
        "--strategy",
        default=None,
        choices=["ldap-wins", "local-wins", "merge"],
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
