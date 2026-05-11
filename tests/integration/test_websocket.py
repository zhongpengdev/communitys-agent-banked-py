"""Integration tests for the WebSocket /ws/chat endpoint."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import jwt
from datetime import datetime, timezone, timedelta


def _make_token(user_id="test-user-123") -> str:
    payload = {
        "userId": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, "test-secret-for-testing-only", algorithm="HS512")


def _make_expired_token() -> str:
    payload = {
        "userId": "user-1",
        "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
    }
    return jwt.encode(payload, "test-secret-for-testing-only", algorithm="HS512")


# ── Auth flow ─────────────────────────────────────────────────────────────────

def test_websocket_rejects_missing_token(client):
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_text(json.dumps({"type": "auth", "token": ""}))
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "token" in msg["content"].lower()


def test_websocket_rejects_invalid_token(client):
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_text(json.dumps({"type": "auth", "token": "invalid.jwt.token"}))
        msg = ws.receive_json()
        assert msg["type"] == "error"


def test_websocket_rejects_expired_token(client):
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_text(json.dumps({"type": "auth", "token": _make_expired_token()}))
        msg = ws.receive_json()
        assert msg["type"] == "error"


def test_websocket_auth_success_sends_auth_success(client):
    token = _make_token()

    mock_agent = MagicMock()
    mock_agent.start = AsyncMock()
    mock_agent.stop = AsyncMock()
    mock_agent.handle_message = AsyncMock()

    with patch("app.websocket.routes.AgentSession", return_value=mock_agent), \
         patch("app.websocket.routes.manager") as mock_manager:
        mock_manager.active_connections = {}
        mock_manager.send_message = AsyncMock()
        mock_manager.send_status = AsyncMock()
        mock_manager.send_text_chunk = AsyncMock()
        mock_manager.send_error = AsyncMock()
        mock_manager.disconnect = MagicMock()

        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text(json.dumps({"type": "auth", "token": token}))
            msg = ws.receive_json()

    assert msg["type"] == "auth_success"
    assert "user_id" in msg


def test_websocket_message_calls_handle_message(client):
    token = _make_token()

    mock_agent = MagicMock()
    mock_agent.start = AsyncMock()
    mock_agent.stop = AsyncMock()
    mock_agent.handle_message = AsyncMock()

    mock_session_result = MagicMock()
    mock_session_result.data = [{"id": 10}]

    with patch("app.websocket.routes.AgentSession", return_value=mock_agent), \
         patch("app.websocket.routes.create_session", return_value=mock_session_result), \
         patch("app.websocket.routes.manager") as mock_manager:
        mock_manager.active_connections = {}
        mock_manager.send_message = AsyncMock()
        mock_manager.send_status = AsyncMock()
        mock_manager.send_text_chunk = AsyncMock()
        mock_manager.send_error = AsyncMock()
        mock_manager.disconnect = MagicMock()

        with client.websocket_connect("/ws/chat") as ws:
            # Auth
            ws.send_text(json.dumps({"type": "auth", "token": token}))
            ws.receive_json()  # auth_success

            # Send a chat message
            ws.send_text(json.dumps({"query": "你好", "sessionId": 10}))

    mock_agent.handle_message.assert_awaited()


def test_websocket_empty_query_is_ignored(client):
    token = _make_token()

    mock_agent = MagicMock()
    mock_agent.start = AsyncMock()
    mock_agent.stop = AsyncMock()
    mock_agent.handle_message = AsyncMock()

    with patch("app.websocket.routes.AgentSession", return_value=mock_agent), \
         patch("app.websocket.routes.manager") as mock_manager:
        mock_manager.active_connections = {}
        mock_manager.send_message = AsyncMock()
        mock_manager.send_status = AsyncMock()
        mock_manager.send_text_chunk = AsyncMock()
        mock_manager.send_error = AsyncMock()
        mock_manager.disconnect = MagicMock()

        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text(json.dumps({"type": "auth", "token": token}))
            ws.receive_json()  # auth_success
            ws.send_text(json.dumps({"query": ""}))

    # handle_message should NOT have been called
    mock_agent.handle_message.assert_not_awaited()


def test_websocket_auto_creates_session_when_missing(client):
    token = _make_token()

    mock_agent = MagicMock()
    mock_agent.start = AsyncMock()
    mock_agent.stop = AsyncMock()
    mock_agent.handle_message = AsyncMock()

    mock_session_result = MagicMock()
    mock_session_result.data = [{"id": 99}]

    with patch("app.websocket.routes.AgentSession", return_value=mock_agent), \
         patch("app.websocket.routes.create_session", return_value=mock_session_result) as mock_create, \
         patch("app.websocket.routes.generate_title", new_callable=AsyncMock, return_value="新标题"), \
         patch("app.websocket.routes.manager") as mock_manager:
        mock_manager.active_connections = {}
        mock_manager.send_message = AsyncMock()
        mock_manager.send_status = AsyncMock()
        mock_manager.send_text_chunk = AsyncMock()
        mock_manager.send_error = AsyncMock()
        mock_manager.disconnect = MagicMock()

        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text(json.dumps({"type": "auth", "token": token}))
            ws.receive_json()  # auth_success
            # No sessionId → should trigger auto-create
            ws.send_text(json.dumps({"query": "帮我查询天气"}))

    mock_create.assert_called()
