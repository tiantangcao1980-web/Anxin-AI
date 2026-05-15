import json
from collections.abc import Coroutine
from typing import Any

import pytest

from src.services.event_bus import EventBus, EventPayload


class _FakeRedis:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    async def publish(self, channel: str, payload: str) -> None:
        self.published.append((channel, payload))


class _FakePubSub:
    def __init__(self) -> None:
        self.subscribed: list[str] = []

    async def subscribe(self, channel: str) -> None:
        self.subscribed.append(channel)


@pytest.mark.asyncio
async def test_publish_adds_timestamp_and_serializes_payload() -> None:
    bus = EventBus()
    fake_redis = _FakeRedis()
    bus.redis = fake_redis  # type: ignore[assignment]
    bus.is_connected = True

    await bus.publish("agent_events", {"agent": "legal", "status": "thinking"})

    assert len(fake_redis.published) == 1
    channel, raw_payload = fake_redis.published[0]
    payload = json.loads(raw_payload)
    assert channel == "agent_events"
    assert payload["agent"] == "legal"
    assert payload["status"] == "thinking"
    assert isinstance(payload["timestamp"], float)


@pytest.mark.asyncio
async def test_subscribe_registers_callback_and_starts_listener(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bus = EventBus()
    fake_pubsub = _FakePubSub()
    bus._pubsub = fake_pubsub
    bus.is_connected = True
    created: list[bool] = []

    def fake_create_task(coro: Coroutine[Any, Any, None]) -> object:
        created.append(True)
        coro.close()
        return object()

    async def callback(payload: EventPayload) -> None:
        payload["seen"] = True

    monkeypatch.setattr("asyncio.create_task", fake_create_task)

    await bus.subscribe("agent_events", callback)

    assert fake_pubsub.subscribed == ["agent_events"]
    assert bus.subscribers["agent_events"] == [callback]
    assert created == [True]
