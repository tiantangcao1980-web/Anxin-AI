"""
A2UI 协议版本字段 + 未知事件降级 回归测试

来自任务：TASK-04 P0-3/P0-4
方案：docs/audit/04-a2ui/PROPOSAL-action-coverage.md

修复内容：
- a2ui_message / a2ui_stream_start 顶层加 protocolVersion 字段
- 老客户端未来可据此决定是否提示升级
"""

from src.services.a2ui_protocol import (
    A2UI_PROTOCOL_VERSION,
    a2ui_message,
    a2ui_stream_start,
)


def test_a2ui_message_includes_protocol_version():
    """a2ui_message 顶层应携带 protocolVersion 字段"""
    msg = a2ui_message(components=[], text="hello", agent="test")
    assert "protocolVersion" in msg
    assert msg["protocolVersion"] == A2UI_PROTOCOL_VERSION


def test_a2ui_stream_start_includes_protocol_version():
    """a2ui_stream_start 顶层应携带 protocolVersion 字段"""
    event = a2ui_stream_start(stream_id="abc12345", agent="test")
    assert "protocolVersion" in event
    assert event["protocolVersion"] == A2UI_PROTOCOL_VERSION


def test_a2ui_protocol_version_is_semver():
    """版本字符串应符合 major.minor.patch 形式"""
    parts = A2UI_PROTOCOL_VERSION.split(".")
    assert len(parts) == 3
    for p in parts:
        assert p.isdigit()


def test_a2ui_message_keeps_existing_fields():
    """加版本号不破坏既有字段"""
    msg = a2ui_message(components=[], text="hello", agent="test", message_id="m1")
    expected_keys = {"type", "protocolVersion", "text", "agent", "a2ui_id", "components"}
    assert set(msg.keys()) == expected_keys
    assert msg["type"] == "a2ui_message"
    assert msg["a2ui_id"] == "m1"


def test_a2ui_stream_start_keeps_existing_fields():
    """流式开始事件加版本号不破坏既有字段"""
    event = a2ui_stream_start(stream_id="s1", agent="test", metadata={"foo": "bar"})
    assert event["type"] == "a2ui_stream"
    assert event["streamId"] == "s1"
    assert event["action"] == "stream_start"
    assert event["metadata"] == {"foo": "bar"}
    assert event["protocolVersion"] == A2UI_PROTOCOL_VERSION
