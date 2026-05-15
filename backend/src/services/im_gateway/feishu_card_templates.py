"""
飞书交互卡片（Interactive Card）模板

返回的字典结构遵循飞书 v1 卡片协议（``msg_type=interactive``）：
    {
        "config": {...},
        "header": {...},
        "elements": [...],
    }

模板：
    - ``task_completed_card``       : 任务完成通知（绿色头）
    - ``approval_request_card``     : 需要审批（黄色头 + 同意/拒绝按钮）
    - ``pairing_request_card``      : 配对授权请求（蓝色头 + 授权/取消）
    - ``error_alert_card``          : 异常告警（红色头）

参考：https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/im-v1/message-cards-introduction
"""

from __future__ import annotations

from typing import Any


def _make_card(
    title: str,
    template_color: str,
    elements: list[dict[str, Any]],
) -> dict[str, Any]:
    """卡片公共结构构造器。"""
    return {
        "config": {"wide_screen_mode": True, "enable_forward": True},
        "header": {
            "template": template_color,
            "title": {"tag": "plain_text", "content": title},
        },
        "elements": elements,
    }


def task_completed_card(task: dict[str, Any]) -> dict[str, Any]:
    """任务完成通知卡片。

    ``task`` 期望字段：``id`` / ``title`` / ``summary`` / ``finished_at`` /
    ``detail_url``（可选，跳转到任务详情页）。
    """
    elements: list[dict[str, Any]] = [
        {
            "tag": "div",
            "fields": [
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**任务 ID**\n{task.get('id', '-')}",
                    },
                },
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**完成时间**\n{task.get('finished_at', '-')}",
                    },
                },
            ],
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{task.get('title', '任务')}**\n{task.get('summary', '已完成。')}",
            },
        },
    ]
    if task.get("detail_url"):
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "查看详情"},
                        "type": "primary",
                        "url": task["detail_url"],
                    }
                ],
            }
        )
    return _make_card("✅ 任务已完成", "green", elements)


def approval_request_card(task: dict[str, Any], reason: str) -> dict[str, Any]:
    """审批请求卡片。

    ``task`` 期望字段：``id`` / ``title``。
    ``reason`` 是 agent 给出的说明（"为什么需要人工审批"）。
    """
    elements: list[dict[str, Any]] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{task.get('title', '待审批任务')}**",
            },
        },
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**审批原因**\n{reason}"},
        },
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "同意"},
                    "type": "primary",
                    "value": {"action": "approval_approve", "task_id": task.get("id")},
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "拒绝"},
                    "type": "danger",
                    "value": {"action": "approval_reject", "task_id": task.get("id")},
                },
            ],
        },
    ]
    return _make_card("⚠️ 需要您的审批", "yellow", elements)


def pairing_request_card(request: dict[str, Any]) -> dict[str, Any]:
    """配对授权请求卡片。

    ``request`` 期望字段：``id`` / ``external_user_id`` / ``expires_at`` /
    ``code``（人类可读的 6-8 位配对码）。
    """
    elements: list[dict[str, Any]] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"飞书账号 **{request.get('external_user_id', '-')}** "
                    f"申请绑定到您的安心助手账号。"
                ),
            },
        },
        {
            "tag": "div",
            "fields": [
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**配对码**\n`{request.get('code', '------')}`",
                    },
                },
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**过期时间**\n{request.get('expires_at', '24h 后')}",
                    },
                },
            ],
        },
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "授权绑定"},
                    "type": "primary",
                    "value": {
                        "action": "pairing_approve",
                        "pairing_id": request.get("id"),
                    },
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "拒绝"},
                    "type": "default",
                    "value": {
                        "action": "pairing_reject",
                        "pairing_id": request.get("id"),
                    },
                },
            ],
        },
    ]
    return _make_card("🔗 IM 配对授权", "blue", elements)


def error_alert_card(error: dict[str, Any]) -> dict[str, Any]:
    """异常告警卡片。

    ``error`` 期望字段：``code`` / ``message`` / ``trace_id`` (可选) /
    ``occurred_at`` (可选)。
    """
    elements: list[dict[str, Any]] = [
        {
            "tag": "div",
            "fields": [
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**错误码**\n{error.get('code', 'UNKNOWN')}",
                    },
                },
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**发生时间**\n{error.get('occurred_at', '-')}",
                    },
                },
            ],
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**异常信息**\n{error.get('message', '未知错误')}",
            },
        },
    ]
    if error.get("trace_id"):
        elements.append(
            {
                "tag": "note",
                "elements": [{"tag": "plain_text", "content": f"trace_id: {error['trace_id']}"}],
            }
        )
    return _make_card("🚨 异常告警", "red", elements)
