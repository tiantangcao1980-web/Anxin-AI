import pytest

from src.services.a2ui_stream import (
    A2UIStream,
    make_fee_estimate_card,
    make_lawyer_card,
)


@pytest.mark.asyncio
async def test_a2ui_stream_emits_start_component_delta_end():
    sent: list[tuple[str, dict[str, object]]] = []

    async def ws_callback(event_type: str, payload: dict[str, object]) -> None:
        sent.append((event_type, payload))

    stream = A2UIStream(ws_callback, stream_id="stream-1", agent="测试 Agent")
    component = {"type": "notice", "data": {"text": "hello"}}

    await stream.start(metadata={"source": "test"})
    await stream.push_component(component)
    await stream.update_component(component["id"], {"data.status": "ready"})
    await stream.end(metadata={"finished": True})

    assert [payload["action"] for _, payload in sent] == [
        "stream_start",
        "stream_component",
        "stream_delta",
        "stream_end",
    ]
    assert sent[0][0] == "a2ui_stream"
    assert sent[0][1]["metadata"] == {"source": "test"}
    assert sent[1][1]["component"] == component
    assert sent[2][1]["componentId"] == component["id"]
    assert stream.components == [component]


def test_a2ui_card_factories_keep_expected_payload_shape():
    lawyer = make_lawyer_card(
        "42",
        "张律师",
        "安心律所",
        ["劳动法"],
        win_rate=0.9,
    )
    fee = make_fee_estimate_card(
        "费用估算",
        items=[{"label": "咨询费", "amount": 1000}],
        total={"amount": 1000, "currency": "CNY"},
    )

    assert lawyer["id"] == "lawyer-42"
    assert lawyer["type"] == "lawyer-card"
    assert lawyer["data"]["winRate"] == 0.9
    assert fee["type"] == "fee-estimate"
    assert fee["data"]["total"]["currency"] == "CNY"
