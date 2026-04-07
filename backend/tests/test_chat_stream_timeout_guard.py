import asyncio
from unittest.mock import AsyncMock

import pytest

from src.api.routes.chat import _consume_streaming_tokens


@pytest.mark.asyncio
async def test_consume_streaming_tokens_raises_timeout_when_queue_stalls():
    token_queue: asyncio.Queue[str | None] = asyncio.Queue()
    ctx = AsyncMock()

    with pytest.raises(asyncio.TimeoutError):
        await _consume_streaming_tokens(
            token_queue=token_queue,
            ctx=ctx,
            agent_name="文书起草Agent",
            timeout_seconds=0.01,
        )

    ctx.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_consume_streaming_tokens_streams_tokens_before_finish():
    token_queue: asyncio.Queue[str | None] = asyncio.Queue()
    await token_queue.put("第一段")
    await token_queue.put("第二段")
    await token_queue.put(None)
    ctx = AsyncMock()

    response = await _consume_streaming_tokens(
        token_queue=token_queue,
        ctx=ctx,
        agent_name="文书起草Agent",
        timeout_seconds=0.01,
    )

    assert response == "第一段第二段"
    assert ctx.send.await_count == 2
