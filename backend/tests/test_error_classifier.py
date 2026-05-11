# -*- coding: utf-8 -*-
"""
P19-A 错误聚类测试

覆盖：
- 同类错误（同 type + 同 frame + 同 endpoint）-> 同 fingerprint，count 累加
- 不同 endpoint -> 不同 fingerprint
- 不同 exception type -> 不同 fingerprint
- fingerprint 稳定性（多次运行结果一致）
- top_n 排序
"""

from __future__ import annotations

import pytest

from src.services.monitoring.error_classifier import (
    ErrorClassifier,
    ErrorFingerprint,
    classify_error,
    reset_default_classifier,
    top_errors,
)


def _raise_value_error():
    raise ValueError("boom")


def _raise_runtime_error():
    raise RuntimeError("crash")


# ==================== 1. 同 fingerprint 累加 ====================
def test_same_fingerprint_increments_count():
    c = ErrorClassifier()
    for _ in range(3):
        try:
            _raise_value_error()
        except ValueError as e:
            fp = c.classify(e, endpoint="/api/v1/foo")
    assert fp.count == 3
    assert c.total_unique() == 1
    assert c.total_events() == 3


# ==================== 2. 不同 endpoint -> 不同 fingerprint ====================
def test_different_endpoint_yields_different_fingerprint():
    c = ErrorClassifier()
    try:
        _raise_value_error()
    except ValueError as e:
        fp1 = c.classify(e, endpoint="/api/v1/a")
    try:
        _raise_value_error()
    except ValueError as e:
        fp2 = c.classify(e, endpoint="/api/v1/b")
    assert fp1.fingerprint != fp2.fingerprint
    assert c.total_unique() == 2


# ==================== 3. 不同 exception 类型 -> 不同 fingerprint ====================
def test_different_exception_type_yields_different_fingerprint():
    c = ErrorClassifier()
    try:
        _raise_value_error()
    except ValueError as e:
        fp_v = c.classify(e, endpoint="/api/v1/x")
    try:
        _raise_runtime_error()
    except RuntimeError as e:
        fp_r = c.classify(e, endpoint="/api/v1/x")
    assert fp_v.fingerprint != fp_r.fingerprint
    assert fp_v.exception_type == "ValueError"
    assert fp_r.exception_type == "RuntimeError"


# ==================== 4. fingerprint 稳定性 ====================
def _capture_value_error(c: ErrorClassifier, endpoint: str) -> ErrorFingerprint:
    """统一调用点，确保 traceback 上 user frame 完全一致。"""
    try:
        _raise_value_error()
    except ValueError as e:
        return c.classify(e, endpoint=endpoint)


def test_fingerprint_is_stable_across_classifier_instances():
    """不同 classifier 实例对相同错误产生相同 fingerprint。"""
    c1 = ErrorClassifier()
    c2 = ErrorClassifier()
    f1 = _capture_value_error(c1, "/api/v1/stable")
    f2 = _capture_value_error(c2, "/api/v1/stable")
    assert f1.fingerprint == f2.fingerprint
    # fingerprint 是 16 位 hex
    assert len(f1.fingerprint) == 16
    assert all(ch in "0123456789abcdef" for ch in f1.fingerprint)


# ==================== 5. top_n 排序 + 默认实例 ====================
def test_top_n_sorted_desc_by_count():
    reset_default_classifier()
    # 制造 3 个 ValueError(/x), 2 个 RuntimeError(/x), 1 个 ValueError(/y)
    for _ in range(3):
        try:
            _raise_value_error()
        except ValueError as e:
            classify_error(e, endpoint="/x")
    for _ in range(2):
        try:
            _raise_runtime_error()
        except RuntimeError as e:
            classify_error(e, endpoint="/x")
    try:
        _raise_value_error()
    except ValueError as e:
        classify_error(e, endpoint="/y")

    top = top_errors(10)
    assert len(top) == 3
    counts = [t["count"] for t in top]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] == 3
