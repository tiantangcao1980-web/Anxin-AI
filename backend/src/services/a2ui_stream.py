"""
A2UI StreamObject 协议 — 流式生成式 UI 助手

支持后端 Agent 逐步构建并发送 A2UI 组件到前端：
1. stream_start  — 开始一个新的流式 A2UI 消息
2. stream_component — 推送完整组件
3. stream_delta — 增量更新组件字段
4. stream_end — 结束流式

用法:
    stream = A2UIStream(ws_callback, stream_id="abc", agent="legal_advisor")
    await stream.start()
    await stream.push_component({
        "id": "lawyer-1",
        "type": "lawyer-card",
        "data": { ... }
    })
    await stream.update_component("lawyer-1", {"status": "online"})
    await stream.end()
"""

import uuid
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


class A2UIStream:
    """流式 A2UI 消息构建器"""

    def __init__(
        self,
        ws_callback: Callable[..., Coroutine],
        stream_id: Optional[str] = None,
        agent: str = "AI 助手",
    ):
        self.ws_callback = ws_callback
        self.stream_id = stream_id or str(uuid.uuid4())[:12]
        self.agent = agent
        self._components: List[Dict[str, Any]] = []
        self._started = False
        self._ended = False

    async def start(self, metadata: Optional[Dict] = None):
        """发送 stream_start 事件"""
        if self._started:
            return
        self._started = True
        await self._send("stream_start", metadata=metadata)

    async def push_component(self, component: Dict[str, Any]):
        """推送一个完整的 A2UI 组件"""
        if self._ended:
            logger.warning(f"[A2UIStream] 流已结束，忽略 push_component: {component.get('type')}")
            return
        if not self._started:
            await self.start()
        
        # 确保组件有 id
        if "id" not in component:
            component["id"] = f"comp-{len(self._components)}-{uuid.uuid4().hex[:6]}"
        
        self._components.append(component)
        await self._send("stream_component", component=component)

    async def update_component(self, component_id: str, delta: Dict[str, Any]):
        """增量更新已推送组件的数据字段"""
        if self._ended:
            return
        await self._send("stream_delta", component_id=component_id, delta=delta)

    async def end(self, metadata: Optional[Dict] = None):
        """结束流式"""
        if self._ended:
            return
        self._ended = True
        await self._send("stream_end", metadata=metadata)

    async def _send(self, action: str, **kwargs):
        """发送 a2ui_stream 事件"""
        try:
            payload = {
                "type": "a2ui_stream",
                "streamId": self.stream_id,
                "action": action,
                "agent": self.agent,
            }
            # 添加可选字段
            if "component" in kwargs and kwargs["component"] is not None:
                payload["component"] = kwargs["component"]
            if "component_id" in kwargs and kwargs["component_id"] is not None:
                payload["componentId"] = kwargs["component_id"]
            if "delta" in kwargs and kwargs["delta"] is not None:
                payload["delta"] = kwargs["delta"]
            if "metadata" in kwargs and kwargs["metadata"] is not None:
                payload["metadata"] = kwargs["metadata"]

            await self.ws_callback("a2ui_stream", payload)
        except Exception as e:
            logger.warning(f"[A2UIStream] 发送失败: {e}")

    @property
    def components(self) -> List[Dict[str, Any]]:
        """获取已推送的组件列表"""
        return list(self._components)


# ========== 法务专用卡片工厂函数 ==========

def make_lawyer_card(
    lawyer_id: str,
    name: str,
    firm: str,
    specialties: List[str],
    rating: float = 4.5,
    status: str = "online",
    **kwargs,
) -> Dict[str, Any]:
    """构建律师推荐卡片组件"""
    return {
        "id": f"lawyer-{lawyer_id}",
        "type": "lawyer-card",
        "data": {
            "lawyerId": lawyer_id,
            "name": name,
            "firm": firm,
            "specialties": specialties,
            "rating": rating,
            "status": status,
            "title": kwargs.get("title"),
            "winRate": kwargs.get("win_rate"),
            "experience": kwargs.get("experience"),
            "responseTime": kwargs.get("response_time"),
            "consultFee": kwargs.get("consult_fee"),
            "introduction": kwargs.get("introduction"),
            "avatar": kwargs.get("avatar"),
            "action": kwargs.get("action", {
                "label": "立即咨询",
                "actionId": "consult_lawyer",
                "payload": {"lawyerId": lawyer_id},
            }),
        },
    }


def make_contract_compare_card(
    title: str,
    left_label: str,
    right_label: str,
    clauses: List[Dict],
    **kwargs,
) -> Dict[str, Any]:
    """构建合同条款对比卡片组件"""
    return {
        "id": f"compare-{uuid.uuid4().hex[:8]}",
        "type": "contract-compare",
        "data": {
            "title": title,
            "subtitle": kwargs.get("subtitle"),
            "leftLabel": left_label,
            "rightLabel": right_label,
            "clauses": clauses,
            "summary": kwargs.get("summary"),
            "actions": kwargs.get("actions", [
                {"label": "接受修改", "actionId": "accept_changes", "variant": "primary"},
                {"label": "导出报告", "actionId": "export_report", "variant": "outline"},
            ]),
        },
    }


def make_fee_estimate_card(
    title: str,
    items: List[Dict],
    total: Dict,
    **kwargs,
) -> Dict[str, Any]:
    """构建费用估算卡片组件"""
    return {
        "id": f"fee-{uuid.uuid4().hex[:8]}",
        "type": "fee-estimate",
        "data": {
            "title": title,
            "subtitle": kwargs.get("subtitle"),
            "items": items,
            "total": total,
            "discounts": kwargs.get("discounts"),
            "packages": kwargs.get("packages"),
            "paymentMethods": kwargs.get("payment_methods"),
            "notes": kwargs.get("notes"),
            "actions": kwargs.get("actions", [
                {"label": "确认费用", "actionId": "confirm_fee", "variant": "primary"},
            ]),
        },
    }
