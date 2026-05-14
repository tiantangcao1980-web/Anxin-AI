# -*- coding: utf-8 -*-
"""
通用滑窗 burst 限流工具 — A10 (2026-05-14)

提取自 backend/src/api/routes/incidents.py, 让 rate-limit 单测可独立运行,
不被 FastAPI 路由 / DB 模型导入链拖累.

设计:
  - 内存滑动窗口 (生产建议替换为 Redis)
  - bucket 内只存 timestamp.monotonic, 自然按窗口过期
  - 通过 _check_burst(bucket, window, limit) 单点判定
  - 配套 _fingerprint_preview 工具生成简单的 (url, message) 指纹
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from threading import Lock


_FINGERPRINT_WINDOW_SECONDS = 60
_FINGERPRINT_BURST_LIMIT = 20
_USER_WINDOW_SECONDS = 60
_USER_BURST_LIMIT = 30


fingerprint_buckets: dict[str, deque[float]] = defaultdict(deque)
user_buckets: dict[str, deque[float]] = defaultdict(deque)
rate_lock = Lock()


def check_burst(bucket: deque[float], window_seconds: int, limit: int) -> bool:
    """滑动窗口判定; True=超限。

    把过期 timestamp 弹出后, 如果剩余 >= limit 则返回 True (本次不放行),
    否则记录当前 timestamp 并返回 False。
    """
    now = time.monotonic()
    cutoff = now - window_seconds
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False


def fingerprint_preview(url: str | None, message: str | None) -> str:
    """前置指纹预估; 与 collector 内部 fingerprint 不强耦合, 仅用于限流分桶。"""
    raw = f"{url or ''}|{message or ''}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]
