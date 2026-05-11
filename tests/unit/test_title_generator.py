"""Unit tests for app/services/title_generator.py"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


async def test_generate_title_returns_string():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="查询天气")]

    with patch("app.services.title_generator._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        from app.services.title_generator import generate_title
        result = await generate_title("今天北京天气怎么样？")

    assert isinstance(result, str)
    assert result == "查询天气"


async def test_generate_title_truncates_to_20_chars():
    long_title = "这是一个非常非常非常非常非常非常长的标题超过二十个汉字了"
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=long_title)]

    with patch("app.services.title_generator._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        from app.services.title_generator import generate_title
        result = await generate_title("something")

    assert len(result) <= 20


async def test_generate_title_falls_back_on_exception():
    with patch("app.services.title_generator._client") as mock_client:
        mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))

        from app.services.title_generator import generate_title
        result = await generate_title("any input")

    assert result == "新会话"


async def test_generate_title_falls_back_on_empty_response():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="   ")]

    with patch("app.services.title_generator._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        from app.services.title_generator import generate_title
        result = await generate_title("test")

    assert result == "新会话"


async def test_generate_title_passes_correct_model():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="标题")]

    with patch("app.services.title_generator._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        from app.services.title_generator import generate_title, CLAUDE_TITLE_MODEL
        await generate_title("test content")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == CLAUDE_TITLE_MODEL
        assert call_kwargs["max_tokens"] == 50


async def test_generate_title_passes_content_to_api():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="标题")]

    with patch("app.services.title_generator._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        from app.services.title_generator import generate_title
        await generate_title("用户的具体问题")

        call_kwargs = mock_client.messages.create.call_args[1]
        messages = call_kwargs["messages"]
        assert any("用户的具体问题" in str(m) for m in messages)
