"""Unit tests for helper functions in app/agent/runner.py"""

import pytest
from unittest.mock import patch, MagicMock
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

@patch("app.agent.runner.get_messages")
def test_build_history_context_returns_empty_when_no_data(mock_get_messages):
    mock_result = MagicMock()
    mock_result.data = []
    mock_get_messages.return_value = mock_result

    result = _build_history_context(42)
    assert result == ""


@patch("app.agent.runner.get_messages")
def test_build_history_context_formats_messages(mock_get_messages):
    mock_result = MagicMock()
    mock_result.data = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮助你？"},
    ]
    mock_get_messages.return_value = mock_result

    result = _build_history_context(1)
    assert "用户: 你好" in result
    assert "助手: 你好！有什么可以帮助你？" in result
    assert "以下是之前的对话记录：" in result


@patch("app.agent.runner.get_messages")
def test_build_history_context_limits_to_last_10(mock_get_messages):
    mock_result = MagicMock()
    mock_result.data = [{"role": "user", "content": f"msg{i}"} for i in range(20)]
    mock_get_messages.return_value = mock_result

    result = _build_history_context(1)
    # Only last 10 messages should be included
    assert "msg10" in result
    assert "msg19" in result
    assert "msg0" not in result
    assert "msg9" not in result


@patch("app.agent.runner.get_messages")
def test_build_history_context_returns_empty_on_exception(mock_get_messages):
    mock_get_messages.side_effect = Exception("DB error")
    result = _build_history_context(1)
    assert result == ""


# ── _save ────────────────────────────────────────────────────────────────────

@patch("app.agent.runner.save_message")
async def test_save_calls_save_message_twice(mock_save):
    await _save(1, "user input", "assistant response")
    assert mock_save.call_count == 2
    calls = mock_save.call_args_list
    assert calls[0][1]["role"] == "user"
    assert calls[0][1]["content"] == "user input"
    assert calls[1][1]["role"] == "assistant"
    assert calls[1][1]["content"] == "assistant response"


@patch("app.agent.runner.save_message")
async def test_save_handles_exception_gracefully(mock_save):
    mock_save.side_effect = Exception("DB write failed")
    # Should not raise
    await _save(1, "q", "a")
