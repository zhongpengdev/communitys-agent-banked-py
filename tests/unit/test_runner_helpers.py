"""Unit tests for helper functions in app/agent/runner.py"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.agent.runner import _strip_mcp_prefix, _build_history_context, _save

# ── _strip_mcp_prefix ────────────────────────────────────────────────────────

def test_strip_mcp_prefix_standard():
    assert _strip_mcp_prefix("mcp__community__get_weather") == "get_weather"


def test_strip_mcp_prefix_longer_name():
    assert _strip_mcp_prefix("mcp__community__query_unpaid_bills") == "query_unpaid_bills"


def test_strip_mcp_prefix_no_prefix_returns_as_is():
    assert _strip_mcp_prefix("plain_tool_name") == "plain_tool_name"


def test_strip_mcp_prefix_two_parts_returns_unchanged():
    # Requires ≥3 double-underscore segments to strip; 2 parts → unchanged
    assert _strip_mcp_prefix("mcp__tool") == "mcp__tool"


def test_strip_mcp_prefix_extracts_last_segment():
    assert _strip_mcp_prefix("mcp__srv__a__b") == "b"


# ── _build_history_context ───────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.agent.runner.RedisMemoryManager.get_message")
@patch("app.database.service.message.get_recent_messages")
async def test_build_history_context_returns_empty_when_no_data(mock_get_recent_messages, mock_redis_get):
    # Mock Redis to return empty list
    mock_redis_get.return_value = []
    
    # Mock DB to return empty list
    mock_get_recent_messages.return_value = []

    result = await _build_history_context(42)
    assert result == ""


@pytest.mark.asyncio
@patch("app.agent.runner.RedisMemoryManager.get_message")
@patch("app.database.service.message.get_recent_messages")
@patch("app.agent.runner.RedisMemoryManager.push_messages_batch")
async def test_build_history_context_formats_messages(mock_redis_push_batch, mock_get_recent_messages, mock_redis_get):
    # Mock Redis to return empty list
    mock_redis_get.return_value = []
    
    # Mock DB to return 2 messages
    mock_result = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮助你？"},
    ]
    mock_get_recent_messages.return_value = mock_result

    result = await _build_history_context(1)
    assert "用户: 你好" in result
    assert "社区助手: 你好！有什么可以帮助你？" in result
    assert "以下是用户和社区助手之前的历史对话：" in result
    mock_redis_push_batch.assert_called_once_with(1, mock_result)


@pytest.mark.asyncio
@patch("app.agent.runner.RedisMemoryManager.get_message")
async def test_build_history_context_hits_redis_cache(mock_redis_get):
    # Mock Redis to return cached messages
    mock_redis_get.return_value = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮助你？"},
    ]

    result = await _build_history_context(1)
    assert "用户: 你好" in result
    assert "社区助手: 你好！有什么可以帮助你？" in result
    assert "以下是用户和社区助手之前的历史对话：" in result


@pytest.mark.asyncio
@patch("app.agent.runner.RedisMemoryManager.get_message")
@patch("app.database.service.message.get_recent_messages")
async def test_build_history_context_returns_empty_on_exception(mock_get_recent_messages, mock_redis_get):
    mock_redis_get.side_effect = Exception("Redis error")
    result = await _build_history_context(1)
    assert result == ""


# ── _save ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.agent.runner.RedisMemoryManager.push_message")
@patch("app.agent.runner.save_message")
async def test_save_calls_redis_and_db_async(mock_save_msg, mock_redis_push):
    await _save(1, "user input", "assistant response")
    
    # Ensure Redis push is called twice
    assert mock_redis_push.call_count == 2
    
    # Ensure DB save was called asynchronously via thread (we give a tiny sleep to allow the thread to run)
    import asyncio
    await asyncio.sleep(0.1)
    assert mock_save_msg.call_count == 2
