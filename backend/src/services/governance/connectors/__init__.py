# -*- coding: utf-8 -*-
"""
受治理的 connector 包装层

所有 connector（feishu / dingtalk / email / amazon-sp / shopify / stripe ...）
要外发动作时**必须**经过这里，而非直接调底层 adapter。

调用约定：

    from src.services.governance.connectors.feishu import send_message

    result = await send_message(
        db, requester=requester,
        channel_id="chat_xxx", content="审查意见草稿……", msg_type="text",
    )

如 PDP 判定 REQUIRE_CONFIRM，``result`` 含 ``ticket_id`` 而非 ``message_id``，
调用方应据此告知用户「已进入审批队列」。
"""
from __future__ import annotations
