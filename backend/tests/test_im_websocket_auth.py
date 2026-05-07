from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.core.database import get_db
from src.services.im_hub import im_manager


@pytest.fixture
def im_ws_app():
    from src.api.main import app

    async def override_get_db():
        yield None

    app.dependency_overrides[get_db] = override_get_db
    im_manager.active_connections.clear()
    yield app
    app.dependency_overrides.clear()
    im_manager.active_connections.clear()


def test_im_websocket_requires_auth_first_packet(im_ws_app):
    with TestClient(im_ws_app) as client:
        with client.websocket_connect("/api/v1/im/ws") as ws:
            ws.send_json({"type": "message", "content": "hello"})
            assert ws.receive_json() == {"type": "error", "message": "首包必须为 auth"}
            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_json()
            assert exc.value.code == 4001


def test_im_websocket_authenticates_with_first_packet(im_ws_app, monkeypatch):
    monkeypatch.setattr(
        "src.api.routes.im.verify_token_with_blacklist",
        AsyncMock(return_value="user-1"),
    )

    with TestClient(im_ws_app) as client:
        with client.websocket_connect("/api/v1/im/ws") as ws:
            ws.send_json({"type": "auth", "data": {"token": "access-token"}})
            assert ws.receive_json() == {"type": "auth_ok", "user_id": "user-1"}


def test_im_websocket_sends_offline_messages_after_auth(im_ws_app, monkeypatch):
    from src.api.main import app

    db_marker = object()
    captured: dict[str, object] = {}

    async def override_get_db():
        yield db_marker

    class FakeIMService:
        def __init__(self, db):
            captured["db"] = db

        async def get_offline_messages(self, user_id, last_ack_message_id=None, limit=100):
            captured["user_id"] = user_id
            captured["last_ack_message_id"] = last_ack_message_id
            captured["limit"] = limit
            return [{"id": "msg-2", "content": "离线消息"}]

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(
        "src.api.routes.im.verify_token_with_blacklist",
        AsyncMock(return_value="user-1"),
    )
    monkeypatch.setattr("src.api.routes.im.IMService", FakeIMService)

    with TestClient(im_ws_app) as client:
        with client.websocket_connect("/api/v1/im/ws") as ws:
            ws.send_json(
                {
                    "type": "auth",
                    "data": {
                        "token": "access-token",
                        "last_ack_message_id": "msg-1",
                    },
                }
            )
            assert ws.receive_json() == {"type": "auth_ok", "user_id": "user-1"}
            assert ws.receive_json() == {
                "type": "offline_messages",
                "messages": [{"id": "msg-2", "content": "离线消息"}],
                "count": 1,
            }

    assert captured == {
        "db": db_marker,
        "user_id": "user-1",
        "last_ack_message_id": "msg-1",
        "limit": 100,
    }
