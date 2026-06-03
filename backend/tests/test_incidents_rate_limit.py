# -*- coding: utf-8 -*-
"""
Incidents 二级限频单测 — A10 (2026-05-14)

覆盖:
1. test_fingerprint_burst_blocks_after_threshold  — 同指纹超 20/60s → 第 21 次返回 429
2. test_user_burst_blocks_after_threshold         — 同用户超 30/60s → 第 31 次返回 429
3. test_different_fingerprints_are_independent    — 不同 url+message 不共享 bucket
4. test_window_expiry_resets                      — bucket 内时间戳过期后重新允许

直接调底层 helper, 不起 FastAPI test client (避免认证设置开销)。
"""

import time
from collections import deque

from src.utils.rate_limit_burst import (
    _FINGERPRINT_BURST_LIMIT,
    _FINGERPRINT_WINDOW_SECONDS,
    _USER_BURST_LIMIT,
    _USER_WINDOW_SECONDS,
    check_burst,
    fingerprint_buckets,
    fingerprint_preview,
    user_buckets,
)


def _reset() -> None:
    fingerprint_buckets.clear()
    user_buckets.clear()


def test_fingerprint_burst_blocks_after_threshold():
    _reset()
    fp = fingerprint_preview("https://x.com/foo", "TypeError: boom")
    bucket = fingerprint_buckets[fp]
    for _ in range(_FINGERPRINT_BURST_LIMIT):
        assert check_burst(bucket, _FINGERPRINT_WINDOW_SECONDS, _FINGERPRINT_BURST_LIMIT) is False
    assert check_burst(bucket, _FINGERPRINT_WINDOW_SECONDS, _FINGERPRINT_BURST_LIMIT) is True


def test_user_burst_blocks_after_threshold():
    _reset()
    bucket = user_buckets["u_a10"]
    for _ in range(_USER_BURST_LIMIT):
        assert check_burst(bucket, _USER_WINDOW_SECONDS, _USER_BURST_LIMIT) is False
    assert check_burst(bucket, _USER_WINDOW_SECONDS, _USER_BURST_LIMIT) is True


def test_different_fingerprints_are_independent():
    _reset()
    fp1 = fingerprint_preview("/a", "Error A")
    fp2 = fingerprint_preview("/b", "Error B")
    assert fp1 != fp2
    for _ in range(_FINGERPRINT_BURST_LIMIT):
        check_burst(fingerprint_buckets[fp1], _FINGERPRINT_WINDOW_SECONDS, _FINGERPRINT_BURST_LIMIT)
    assert check_burst(fingerprint_buckets[fp1], _FINGERPRINT_WINDOW_SECONDS, _FINGERPRINT_BURST_LIMIT) is True
    assert check_burst(fingerprint_buckets[fp2], _FINGERPRINT_WINDOW_SECONDS, _FINGERPRINT_BURST_LIMIT) is False


def test_window_expiry_resets():
    """模拟窗口过期: 手工往 bucket 注入过老的 timestamp, check_burst 应弹出并放行。"""
    _reset()
    bucket: deque[float] = fingerprint_buckets["expiry_test"]
    now = time.monotonic()
    for _ in range(_FINGERPRINT_BURST_LIMIT):
        bucket.append(now - _FINGERPRINT_WINDOW_SECONDS - 1)
    assert check_burst(bucket, _FINGERPRINT_WINDOW_SECONDS, _FINGERPRINT_BURST_LIMIT) is False
    assert len(bucket) == 1


# ============================================================
# F2: Redis 后端 fallback 测试
# ============================================================

def test_check_burst_redis_fallback_when_no_redis(monkeypatch):
    """F2: RATE_LIMIT_REDIS_URL 未设置 → check_burst_redis 自动 fallback 到内存。"""
    import src.utils.rate_limit_burst as mod
    from src.utils.rate_limit_burst import (
        _redis_fallback_buckets,
        check_burst_redis,
    )

    # 强制 init 重置
    monkeypatch.delenv("RATE_LIMIT_REDIS_URL", raising=False)
    mod._redis_init_attempted = False
    mod._redis_client = None
    _redis_fallback_buckets.clear()

    # 前 N 次放行, 第 N+1 次阻断 — 行为应与内存版一致
    for _ in range(3):
        assert check_burst_redis("fb_test", window_seconds=60, limit=3) is False
    assert check_burst_redis("fb_test", window_seconds=60, limit=3) is True
    assert "fb_test" in _redis_fallback_buckets
