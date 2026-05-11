"""Unit tests for app/websocket/manager.py"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.websocket.manager import ConnectionManager


@pytest.fixture
def manager():
    return ConnectionManager()


@pytest.fixture
def mock_ws():
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


async def test_connect_accepts_websocket(manager, mock_ws):
    await manager.connect(mock_ws, "user-1")
    mock_ws.accept.assert_awaited_once()
    assert "user-1" in manager.active_connections


async def test_connect_registers_user(manager, mock_ws):
    await manager.connect(mock_ws, "user-42")
    assert manager.active_connections["user-42"] is mock_ws


async def test_connect_multiple_users(manager):
    ws1 = MagicMock()
    ws1.accept = AsyncMock()
    ws2 = MagicMock()
    ws2.accept = AsyncMock()

    await manager.connect(ws1, "user-1")
    await manager.connect(ws2, "user-2")

    assert len(manager.active_connections) == 2


def test_disconnect_removes_user(manager, mock_ws):
    manager.active_connections["user-1"] = mock_ws
    manager.disconnect("user-1")
    assert "user-1" not in manager.active_connections


def test_disconnect_nonexistent_user_is_noop(manager):
    manager.disconnect("ghost-user")
    assert "ghost-user" not in manager.active_connections


async def test_send_message_calls_send_json(manager, mock_ws):
    manager.active_connections["user-1"] = mock_ws
    await manager.send_message("user-1", {"type": "test"})
    mock_ws.send_json.assert_awaited_once_with({"type": "test"})


async def test_send_message_unknown_user_is_noop(manager, mock_ws):
    await manager.send_message("ghost", {"type": "test"})
    mock_ws.send_json.assert_not_awaited()


async def test_send_message_disconnects_on_send_error(manager, mock_ws):
    mock_ws.send_json = AsyncMock(side_effect=Exception("connection broken"))
    manager.active_connections["user-1"] = mock_ws

    with pytest.raises(RuntimeError, match="WebSocket send failed"):
        await manager.send_message("user-1", {"type": "test"})

    assert "user-1" not in manager.active_connections


async def test_send_text_chunk_sends_chunk_type(manager, mock_ws):
    manager.active_connections["user-1"] = mock_ws
    await manager.send_text_chunk("user-1", "hello", is_final=False)
    mock_ws.send_json.assert_awaited_once_with({
        "type": "chunk", "content": "hello", "is_final": False
    })


async def test_send_text_chunk_final_flag(manager, mock_ws):
    manager.active_connections["user-1"] = mock_ws
    await manager.send_text_chunk("user-1", "", is_final=True)
    sent = mock_ws.send_json.call_args[0][0]
    assert sent["is_final"] is True


async def test_send_error_sends_error_type(manager, mock_ws):
    manager.active_connections["user-1"] = mock_ws
    await manager.send_error("user-1", "something went wrong")
    mock_ws.send_json.assert_awaited_once_with({
        "type": "error", "content": "something went wrong"
    })


async def test_send_status_sends_status_type(manager, mock_ws):
    manager.active_connections["user-1"] = mock_ws
    await manager.send_status("user-1", "thinking", {"message": "正在思考"})
    mock_ws.send_json.assert_awaited_once_with({
        "type": "status", "status": "thinking", "data": {"message": "正在思考"}
    })


async def test_send_status_defaults_empty_data(manager, mock_ws):
    manager.active_connections["user-1"] = mock_ws
    await manager.send_status("user-1", "completed")
    sent = mock_ws.send_json.call_args[0][0]
    assert sent["data"] == {}
