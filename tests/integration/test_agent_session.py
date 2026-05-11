"""Integration tests for AgentSession in app/agent/runner.py

Imports are done lazily inside tests/fixtures to avoid a circular import between
app.agent.runner (imports app.websocket.manager) and app.websocket.routes
(imports app.agent.runner).  When the full app has been loaded (e.g., after
the first fixture that imports main.app), sys.modules caches all modules and
the cycle is resolved.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _bootstrap_app():
    """Ensure the full app is imported so circular deps are resolved."""
    from main import app  # noqa: F401


@pytest.fixture
def AgentSession():
    from app.agent.runner import AgentSession as _Cls
    return _Cls


@pytest.fixture
def sdk_classes():
    from claude_agent_sdk import (
        AssistantMessage,
        TextBlock,
        ToolUseBlock,
        ToolResultBlock,
        ResultMessage,
    )
    return AssistantMessage, TextBlock, ToolUseBlock, ToolResultBlock, ResultMessage


def _make_mock_client():
    mock = MagicMock()
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.query = AsyncMock()
    return mock


# ── start / stop ──────────────────────────────────────────────────────────────

async def test_agent_session_start_connects_client(AgentSession):
    mock_client = _make_mock_client()

    with patch("app.agent.runner.ClaudeSDKClient", return_value=mock_client):
        session = AgentSession("user-1")
        await session.start()

    mock_client.connect.assert_awaited_once()
    assert session._client is mock_client


async def test_agent_session_stop_disconnects_client(AgentSession):
    mock_client = _make_mock_client()

    with patch("app.agent.runner.ClaudeSDKClient", return_value=mock_client):
        session = AgentSession("user-1")
        await session.start()
        await session.stop()

    mock_client.disconnect.assert_awaited_once()
    assert session._client is None


async def test_agent_session_stop_without_start_is_noop(AgentSession):
    session = AgentSession("user-1")
    await session.stop()


# ── handle_message: thinking status ──────────────────────────────────────────

async def test_handle_message_sends_thinking_status(AgentSession, sdk_classes):
    _, _, _, _, ResultMessage = sdk_classes
    mock_client = _make_mock_client()

    async def mock_receive():
        yield ResultMessage()

    mock_client.receive_response = mock_receive

    with patch("app.agent.runner.ClaudeSDKClient", return_value=mock_client), \
         patch("app.agent.runner.manager") as mock_manager, \
         patch("app.agent.runner._build_history_context", return_value=""):
        mock_manager.send_status = AsyncMock()
        mock_manager.send_text_chunk = AsyncMock()

        session = AgentSession("user-1")
        await session.start()
        await session.handle_message(1, "你好")

    mock_manager.send_status.assert_any_await("user-1", "thinking", {"message": "正在思考..."})


# ── handle_message: text streaming ────────────────────────────────────────────

async def test_handle_message_streams_text_chunks(AgentSession, sdk_classes):
    AssistantMessage, TextBlock, _, _, ResultMessage = sdk_classes
    mock_client = _make_mock_client()

    async def mock_receive():
        msg = AssistantMessage()
        msg.content = [TextBlock("你好！"), TextBlock("有什么可以帮您？")]
        yield msg
        yield ResultMessage()

    mock_client.receive_response = mock_receive
    chunks = []

    async def capture_chunk(user_id, chunk, is_final=False):
        chunks.append((chunk, is_final))

    with patch("app.agent.runner.ClaudeSDKClient", return_value=mock_client), \
         patch("app.agent.runner.manager") as mock_manager, \
         patch("app.agent.runner._build_history_context", return_value=""):
        mock_manager.send_status = AsyncMock()
        mock_manager.send_text_chunk = AsyncMock(side_effect=capture_chunk)

        session = AgentSession("user-1")
        await session.start()
        await session.handle_message(1, "你好")

    text_chunks = [c for c, f in chunks if not f]
    assert any("你好" in c for c in text_chunks)
    assert chunks[-1] == ("", True)


async def test_handle_message_sends_completed_status(AgentSession, sdk_classes):
    _, _, _, _, ResultMessage = sdk_classes
    mock_client = _make_mock_client()

    async def mock_receive():
        yield ResultMessage()

    mock_client.receive_response = mock_receive
    status_calls = []

    async def capture_status(user_id, status, data=None):
        status_calls.append(status)

    with patch("app.agent.runner.ClaudeSDKClient", return_value=mock_client), \
         patch("app.agent.runner.manager") as mock_manager, \
         patch("app.agent.runner._build_history_context", return_value=""):
        mock_manager.send_status = AsyncMock(side_effect=capture_status)
        mock_manager.send_text_chunk = AsyncMock()

        session = AgentSession("user-1")
        await session.start()
        await session.handle_message(1, "test")

    assert "completed" in status_calls


# ── handle_message: tool calls ─────────────────────────────────────────────────

async def test_handle_message_sends_tool_calling_status(AgentSession, sdk_classes):
    AssistantMessage, TextBlock, ToolUseBlock, _, ResultMessage = sdk_classes
    mock_client = _make_mock_client()

    async def mock_receive():
        msg1 = AssistantMessage()
        msg1.content = [ToolUseBlock("mcp__community__get_weather")]
        yield msg1

        msg2 = AssistantMessage()
        msg2.content = [TextBlock("北京今天晴天")]
        yield msg2

        yield ResultMessage()

    mock_client.receive_response = mock_receive
    status_calls = []

    async def capture_status(user_id, status, data=None):
        status_calls.append(status)

    with patch("app.agent.runner.ClaudeSDKClient", return_value=mock_client), \
         patch("app.agent.runner.manager") as mock_manager, \
         patch("app.agent.runner._build_history_context", return_value=""):
        mock_manager.send_status = AsyncMock(side_effect=capture_status)
        mock_manager.send_text_chunk = AsyncMock()

        session = AgentSession("user-1")
        await session.start()
        await session.handle_message(1, "北京天气")

    assert "tool_calling" in status_calls
    assert "tool_completed" in status_calls


async def test_handle_message_tool_result_sends_completed(AgentSession, sdk_classes):
    AssistantMessage, TextBlock, ToolUseBlock, ToolResultBlock, ResultMessage = sdk_classes
    mock_client = _make_mock_client()

    async def mock_receive():
        msg = AssistantMessage()
        msg.content = [ToolUseBlock("mcp__community__get_time"), ToolResultBlock(), TextBlock("当前时间是...")]
        yield msg
        yield ResultMessage()

    mock_client.receive_response = mock_receive
    status_calls = []

    async def capture_status(user_id, status, data=None):
        status_calls.append(status)

    with patch("app.agent.runner.ClaudeSDKClient", return_value=mock_client), \
         patch("app.agent.runner.manager") as mock_manager, \
         patch("app.agent.runner._build_history_context", return_value=""):
        mock_manager.send_status = AsyncMock(side_effect=capture_status)
        mock_manager.send_text_chunk = AsyncMock()

        session = AgentSession("user-1")
        await session.start()
        await session.handle_message(1, "现在几点")

    assert "tool_completed" in status_calls


# ── handle_message: history context ──────────────────────────────────────────

async def test_handle_message_uses_history_context(AgentSession, sdk_classes):
    _, _, _, _, ResultMessage = sdk_classes
    mock_client = _make_mock_client()

    async def mock_receive():
        yield ResultMessage()

    mock_client.receive_response = mock_receive

    with patch("app.agent.runner.ClaudeSDKClient", return_value=mock_client), \
         patch("app.agent.runner.manager") as mock_manager, \
         patch("app.agent.runner._build_history_context", return_value="历史上下文\n\n") as mock_ctx:
        mock_manager.send_status = AsyncMock()
        mock_manager.send_text_chunk = AsyncMock()

        session = AgentSession("user-1")
        await session.start()
        await session.handle_message(5, "新消息")

    mock_ctx.assert_called_once_with(5)
    call_args = mock_client.query.call_args[0][0]
    assert "历史上下文" in call_args
    assert "新消息" in call_args


async def test_handle_message_no_history_sends_raw_input(AgentSession, sdk_classes):
    _, _, _, _, ResultMessage = sdk_classes
    mock_client = _make_mock_client()

    async def mock_receive():
        yield ResultMessage()

    mock_client.receive_response = mock_receive

    with patch("app.agent.runner.ClaudeSDKClient", return_value=mock_client), \
         patch("app.agent.runner.manager") as mock_manager, \
         patch("app.agent.runner._build_history_context", return_value=""):
        mock_manager.send_status = AsyncMock()
        mock_manager.send_text_chunk = AsyncMock()

        session = AgentSession("user-1")
        await session.start()
        await session.handle_message(1, "直接问题")

    call_args = mock_client.query.call_args[0][0]
    assert call_args == "直接问题"


# ── handle_message: DB persistence ───────────────────────────────────────────

async def test_handle_message_saves_to_db_when_response_exists(AgentSession, sdk_classes):
    AssistantMessage, TextBlock, _, _, ResultMessage = sdk_classes
    mock_client = _make_mock_client()

    async def mock_receive():
        msg = AssistantMessage()
        msg.content = [TextBlock("回答内容")]
        yield msg
        yield ResultMessage()

    mock_client.receive_response = mock_receive

    def _close_coro(coro):
        coro.close()
        return MagicMock()

    with patch("app.agent.runner.ClaudeSDKClient", return_value=mock_client), \
         patch("app.agent.runner.manager") as mock_manager, \
         patch("app.agent.runner._build_history_context", return_value=""), \
         patch("app.agent.runner.asyncio.create_task", side_effect=_close_coro) as mock_task:
        mock_manager.send_status = AsyncMock()
        mock_manager.send_text_chunk = AsyncMock()

        session = AgentSession("user-1")
        await session.start()
        await session.handle_message(1, "问题")

    mock_task.assert_called_once()


async def test_handle_message_skips_db_when_empty_response(AgentSession, sdk_classes):
    _, _, _, _, ResultMessage = sdk_classes
    mock_client = _make_mock_client()

    async def mock_receive():
        yield ResultMessage()

    mock_client.receive_response = mock_receive

    with patch("app.agent.runner.ClaudeSDKClient", return_value=mock_client), \
         patch("app.agent.runner.manager") as mock_manager, \
         patch("app.agent.runner._build_history_context", return_value=""), \
         patch("app.agent.runner.asyncio.create_task") as mock_task:
        mock_manager.send_status = AsyncMock()
        mock_manager.send_text_chunk = AsyncMock()

        session = AgentSession("user-1")
        await session.start()
        await session.handle_message(1, "问题")

    mock_task.assert_not_called()
