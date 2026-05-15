"""
P19-A Prometheus 业务 metric 测试

每个 metric 一个用例 + endpoint normalization：
- record_http_request
- record_agent_task
- record_oauth_callback
- record_webhook
- record_fetch_request
- record_db_query
- normalize_endpoint
- exposition format
"""

from __future__ import annotations

import pytest

from src.services.monitoring.prometheus_metrics import (
    AGENT_TASKS_TOTAL,
    DB_QUERY_DURATION_SECONDS,
    FETCH_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    OAUTH_CALLBACK_TOTAL,
    REGISTRY,
    WEBHOOK_RECEIVED_TOTAL,
    normalize_endpoint,
    record_agent_task,
    record_db_query,
    record_fetch_request,
    record_http_request,
    record_oauth_callback,
    record_webhook,
    render_exposition,
)


def _counter_value(counter, **labels):
    """读取 counter 当前值。"""
    return counter.labels(**labels)._value.get()


# ==================== 1. http_requests_total + duration ====================
def test_record_http_request_increments_counter_and_observes_duration():
    before = _counter_value(
        HTTP_REQUESTS_TOTAL, method="GET", endpoint="/api/v1/test", status="200"
    )
    record_http_request("get", "/api/v1/test", 200, 0.123)
    after = _counter_value(HTTP_REQUESTS_TOTAL, method="GET", endpoint="/api/v1/test", status="200")
    assert after == before + 1

    # histogram 总计样本数 +1
    h = HTTP_REQUEST_DURATION_SECONDS.labels(method="GET", endpoint="/api/v1/test")
    assert h._sum.get() >= 0.123


# ==================== 2. agent_tasks_total ====================
def test_record_agent_task_increments_counter():
    before = _counter_value(AGENT_TASKS_TOTAL, persona="legal", status="success")
    record_agent_task("legal", "success", 1.5)
    after = _counter_value(AGENT_TASKS_TOTAL, persona="legal", status="success")
    assert after == before + 1


# ==================== 3. oauth_callback_total ====================
def test_record_oauth_callback():
    before = _counter_value(OAUTH_CALLBACK_TOTAL, provider="wechat", result="success")
    record_oauth_callback("wechat", "success")
    after = _counter_value(OAUTH_CALLBACK_TOTAL, provider="wechat", result="success")
    assert after == before + 1


# ==================== 4. webhook_received_total ====================
def test_record_webhook():
    before = _counter_value(WEBHOOK_RECEIVED_TOTAL, source="esign", result="ok")
    record_webhook("esign", "ok")
    after = _counter_value(WEBHOOK_RECEIVED_TOTAL, source="esign", result="ok")
    assert after == before + 1


# ==================== 5. fetch_requests_total ====================
def test_record_fetch_request():
    before = _counter_value(FETCH_REQUESTS_TOTAL, tier="l3_headlessx", result="success")
    record_fetch_request("l3_headlessx", "success")
    after = _counter_value(FETCH_REQUESTS_TOTAL, tier="l3_headlessx", result="success")
    assert after == before + 1


# ==================== 6. db_query_duration_seconds ====================
def test_record_db_query_observes_histogram():
    h = DB_QUERY_DURATION_SECONDS.labels(operation="select")
    before = h._sum.get()
    record_db_query("SELECT", 0.025)
    after = h._sum.get()
    assert after >= before + 0.025


# ==================== 7. endpoint normalization ====================
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("/api/v1/cases/123", "/api/v1/cases/{id}"),
        ("/api/v1/users/550e8400-e29b-41d4-a716-446655440000", "/api/v1/users/{uuid}"),
        ("/api/v1/personas/legal/chat", "/api/v1/personas/legal/chat"),
        ("/", "/"),
        ("", "/"),
    ],
)
def test_normalize_endpoint(raw, expected):
    assert normalize_endpoint(raw) == expected


# ==================== 8. exposition format ====================
def test_exposition_includes_business_metrics():
    record_http_request("GET", "/api/v1/dummy", 200, 0.01)
    text = render_exposition().decode("utf-8")
    assert "anxin_http_requests_total" in text
    assert "anxin_http_request_duration_seconds" in text
    assert "anxin_agent_tasks_total" in text
    # prometheus exposition 格式合法（HELP/TYPE 行存在）
    assert "# HELP " in text
    assert "# TYPE " in text


# ==================== 9. registry isolation ====================
def test_registry_is_independent():
    """业务 metric 注册到独立 REGISTRY，不污染默认全局。"""
    from prometheus_client import REGISTRY as DEFAULT_REGISTRY

    assert REGISTRY is not DEFAULT_REGISTRY
