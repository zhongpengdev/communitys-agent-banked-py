"""Unit tests for all 16 MCP tools in app/tools_mcp/server.py"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from app.tools_mcp.server import (
    get_time,
    get_weather,
    query_unpaid_bills,
    get_user_notifications,
    read_notification,
    send_private_messages,
    create_visitor,
    search_goods,
    send_scheduled_email,
    get_scheduled_email,
    delete_scheduled_email,
    web_search,
    wikipedia_search,
    toutiao_hot_news,
    search_domains_info,
    generate_image_from_text,
    _ok,
    _err,
    _auth_headers,
)
from app.utils.context import set_request_token


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_result(result: dict) -> str:
    return result["content"][0]["text"]


# ── _ok / _err ────────────────────────────────────────────────────────────────

def test_ok_with_string():
    result = _ok("hello")
    assert result["content"][0]["type"] == "text"
    assert result["content"][0]["text"] == "hello"


def test_ok_with_dict():
    result = _ok({"key": "value"})
    text = json.loads(result["content"][0]["text"])
    assert text["key"] == "value"


def test_err_returns_error_json():
    result = _err("something failed")
    text = json.loads(result["content"][0]["text"])
    assert text["success"] is False
    assert "something failed" in text["message"]


# ── _auth_headers ─────────────────────────────────────────────────────────────

def test_auth_headers_with_token():
    set_request_token("my-jwt")
    headers = _auth_headers()
    assert headers == {"Authorization": "Bearer my-jwt"}


def test_auth_headers_without_token():
    set_request_token(None)
    headers = _auth_headers()
    assert headers == {}


# ── get_time ──────────────────────────────────────────────────────────────────

async def test_get_time_returns_formatted_datetime():
    result = await get_time({})
    text = _parse_result(result)
    import re
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text)


# ── get_weather ───────────────────────────────────────────────────────────────

@patch("app.tools_mcp.server._get")
@patch("app.tools_mcp.server.aiohttp.ClientSession")
async def test_get_weather_with_city(mock_session_cls, mock_get):
    mock_response = AsyncMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_response.json = AsyncMock(return_value={"weather": "sunny", "city": "Beijing"})

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session_cls.return_value = mock_session

    result = await get_weather({"city": "Beijing"})
    text = _parse_result(result)
    assert "sunny" in text or "Beijing" in text


@patch("app.tools_mcp.server._get")
async def test_get_weather_without_city_uses_ip(mock_get):
    mock_get.return_value = {"data": "1.2.3.4"}

    with patch("app.tools_mcp.server.aiohttp.ClientSession") as mock_cls:
        mock_resp = AsyncMock()
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        mock_resp.json = AsyncMock(side_effect=[
            {"data": {"address": "北京市 朝阳区"}},
            {"weather": "cloudy"},
        ])

        mock_sess = AsyncMock()
        mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_sess.__aexit__ = AsyncMock(return_value=None)
        mock_sess.get = MagicMock(return_value=mock_resp)
        mock_cls.return_value = mock_sess

        result = await get_weather({})
    assert "content" in result


@patch("app.tools_mcp.server.aiohttp.ClientSession")
async def test_get_weather_returns_error_on_failure(mock_session_cls):
    mock_session_cls.side_effect = Exception("network error")
    result = await get_weather({"city": "Shanghai"})
    text = _parse_result(result)
    data = json.loads(text)
    assert data["success"] is False


# ── query_unpaid_bills ────────────────────────────────────────────────────────

@patch("app.tools_mcp.server._get")
async def test_query_unpaid_bills_success(mock_get):
    mock_get.return_value = {"data": [{"id": 1, "amount": 100}]}
    result = await query_unpaid_bills({"status": 0})
    text = _parse_result(result)
    assert "100" in text


@patch("app.tools_mcp.server._get")
async def test_query_unpaid_bills_default_status(mock_get):
    mock_get.return_value = {"data": []}
    await query_unpaid_bills({})
    mock_get.assert_called_once_with("/api/property-fee/bills", {"status": 0})


@patch("app.tools_mcp.server._get")
async def test_query_unpaid_bills_error(mock_get):
    mock_get.side_effect = Exception("timeout")
    result = await query_unpaid_bills({})
    data = json.loads(_parse_result(result))
    assert data["success"] is False


# ── get_user_notifications ────────────────────────────────────────────────────

@patch("app.tools_mcp.server._get")
async def test_get_user_notifications_success(mock_get):
    mock_get.return_value = {"data": [{"id": 1, "content": "公告"}]}
    result = await get_user_notifications({"pageNum": 0, "pageSize": 10})
    assert "content" in result


@patch("app.tools_mcp.server._get")
async def test_get_user_notifications_default_params(mock_get):
    mock_get.return_value = {"data": []}
    await get_user_notifications({})
    mock_get.assert_called_once_with(
        "/api/notification/list", {"pageNum": 0, "pageSize": 10}
    )


@patch("app.tools_mcp.server._get")
async def test_get_user_notifications_error(mock_get):
    mock_get.side_effect = Exception("error")
    result = await get_user_notifications({})
    data = json.loads(_parse_result(result))
    assert data["success"] is False


# ── read_notification ─────────────────────────────────────────────────────────

@patch("app.tools_mcp.server._post")
async def test_read_notification_success(mock_post):
    mock_post.return_value = {"success": True}
    result = await read_notification({"notificationId": "notif-abc"})
    mock_post.assert_called_once_with("/api/notification/notif-abc/read")
    assert "content" in result


@patch("app.tools_mcp.server._post")
async def test_read_notification_error(mock_post):
    mock_post.side_effect = Exception("404")
    result = await read_notification({"notificationId": "x"})
    data = json.loads(_parse_result(result))
    assert data["success"] is False


# ── send_private_messages ─────────────────────────────────────────────────────

@patch("app.tools_mcp.server._post")
async def test_send_private_messages_success(mock_post):
    mock_post.return_value = {"success": True}
    result = await send_private_messages({"content": "你好", "toUserId": "user-99"})
    mock_post.assert_called_once_with(
        "/api/message/send", {"content": "你好", "toUserId": "user-99"}
    )
    assert "content" in result


@patch("app.tools_mcp.server._post")
async def test_send_private_messages_error(mock_post):
    mock_post.side_effect = Exception("failed")
    result = await send_private_messages({"content": "hi", "toUserId": "u"})
    data = json.loads(_parse_result(result))
    assert data["success"] is False


# ── create_visitor ────────────────────────────────────────────────────────────

@patch("app.tools_mcp.server._post")
async def test_create_visitor_success(mock_post):
    mock_post.return_value = {"success": True, "visitorId": "v-123"}
    args = {
        "visitorName": "张三",
        "visitorPhone": "13800138000",
        "visitPurpose": "拜访",
        "allowTime": "2026-05-12 10:00:00",
        "validDate": "2026-05-12 18:00:00",
    }
    result = await create_visitor(args)
    mock_post.assert_called_once_with("/api/visitor/register", {
        "visitorName": "张三",
        "visitorPhone": "13800138000",
        "visitPurpose": "拜访",
        "allowTime": "2026-05-12 10:00:00",
        "validDate": "2026-05-12 18:00:00",
    })
    assert "content" in result


@patch("app.tools_mcp.server._post")
async def test_create_visitor_error(mock_post):
    mock_post.side_effect = Exception("validation error")
    result = await create_visitor({
        "visitorName": "x", "visitorPhone": "x",
        "visitPurpose": "x", "allowTime": "x", "validDate": "x",
    })
    data = json.loads(_parse_result(result))
    assert data["success"] is False


# ── search_goods ──────────────────────────────────────────────────────────────

@patch("app.tools_mcp.server._post")
async def test_search_goods_success(mock_post):
    mock_post.return_value = {"data": [{"name": "苹果", "price": 5.0}]}
    result = await search_goods({"keyword": "苹果", "category_id": 0, "page_num": 1, "page_size": 10})
    assert "content" in result


@patch("app.tools_mcp.server._post")
async def test_search_goods_uses_defaults(mock_post):
    mock_post.return_value = {"data": []}
    await search_goods({"keyword": "test"})
    mock_post.assert_called_once_with("/api/mall/list", {
        "categoryId": 0, "keyword": "test", "pageNum": 1, "pageSize": 10
    })


@patch("app.tools_mcp.server._post")
async def test_search_goods_error(mock_post):
    mock_post.side_effect = Exception("error")
    result = await search_goods({})
    data = json.loads(_parse_result(result))
    assert data["success"] is False


# ── send_scheduled_email ──────────────────────────────────────────────────────

@patch("app.tools_mcp.server._post")
async def test_send_scheduled_email_success(mock_post):
    mock_post.return_value = {"id": "email-1"}
    result = await send_scheduled_email({
        "subject": "测试邮件",
        "content": "邮件内容",
        "scheduledTime": "2026-05-12T10:00:00",
        "isHtml": False,
    })
    mock_post.assert_called_once_with("/api/scheduled-email", {
        "subject": "测试邮件",
        "content": "邮件内容",
        "scheduledTime": "2026-05-12T10:00:00",
        "isHtml": False,
    })
    assert "content" in result


@patch("app.tools_mcp.server._post")
async def test_send_scheduled_email_default_html_false(mock_post):
    mock_post.return_value = {}
    await send_scheduled_email({
        "subject": "s", "content": "c", "scheduledTime": "2026-01-01T00:00:00"
    })
    sent = mock_post.call_args[0][1]
    assert sent["isHtml"] is False


@patch("app.tools_mcp.server._post")
async def test_send_scheduled_email_error(mock_post):
    mock_post.side_effect = Exception("fail")
    result = await send_scheduled_email({"subject": "s", "content": "c", "scheduledTime": "t"})
    data = json.loads(_parse_result(result))
    assert data["success"] is False


# ── get_scheduled_email ───────────────────────────────────────────────────────

@patch("app.tools_mcp.server._get")
async def test_get_scheduled_email_success(mock_get):
    mock_get.return_value = {"data": [{"id": "e1"}]}
    result = await get_scheduled_email({"pageNum": 0, "pageSize": 10})
    mock_get.assert_called_once_with("/api/scheduled-email/list", {"page": 0, "size": 10})
    assert "content" in result


@patch("app.tools_mcp.server._get")
async def test_get_scheduled_email_error(mock_get):
    mock_get.side_effect = Exception("error")
    result = await get_scheduled_email({})
    data = json.loads(_parse_result(result))
    assert data["success"] is False


# ── delete_scheduled_email ────────────────────────────────────────────────────

@patch("app.tools_mcp.server._delete")
async def test_delete_scheduled_email_success(mock_delete):
    mock_delete.return_value = {"success": True}
    result = await delete_scheduled_email({"id": "email-42"})
    mock_delete.assert_called_once_with("/api/scheduled-email/email-42")
    assert "content" in result


@patch("app.tools_mcp.server._delete")
async def test_delete_scheduled_email_error(mock_delete):
    mock_delete.side_effect = Exception("not found")
    result = await delete_scheduled_email({"id": "bad-id"})
    data = json.loads(_parse_result(result))
    assert data["success"] is False


# ── web_search ────────────────────────────────────────────────────────────────

async def test_web_search_no_serp_key():
    with patch("app.tools_mcp.server.SERP_KEY", ""):
        result = await web_search({"query": "python"})
    data = json.loads(_parse_result(result))
    assert data["success"] is False
    assert "SERP_KEY" in data["message"]


@patch("app.tools_mcp.server.aiohttp.ClientSession")
async def test_web_search_with_organic_results(mock_session_cls):
    api_resp = {
        "organic_results": [
            {"title": "Python官网", "snippet": "编程语言", "link": "https://python.org"},
        ]
    }
    mock_resp = AsyncMock()
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)
    mock_resp.json = AsyncMock(return_value=api_resp)

    mock_sess = AsyncMock()
    mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_sess.__aexit__ = AsyncMock(return_value=None)
    mock_sess.get = MagicMock(return_value=mock_resp)
    mock_session_cls.return_value = mock_sess

    with patch("app.tools_mcp.server.SERP_KEY", "fake-key"):
        result = await web_search({"query": "python"})

    text = _parse_result(result)
    assert "Python官网" in text


@patch("app.tools_mcp.server.aiohttp.ClientSession")
async def test_web_search_error_returns_err(mock_session_cls):
    mock_session_cls.side_effect = Exception("network error")
    with patch("app.tools_mcp.server.SERP_KEY", "fake-key"):
        result = await web_search({"query": "test"})
    data = json.loads(_parse_result(result))
    assert data["success"] is False


# ── wikipedia_search ──────────────────────────────────────────────────────────

@patch("app.tools_mcp.server.aiohttp.ClientSession")
async def test_wikipedia_search_success(mock_session_cls):
    search_resp = {"query": {"search": [{"title": "Python (programming language)"}]}}
    detail_resp = {
        "query": {"pages": {"1234": {"extract": "Python is a programming language."}}}
    }

    call_count = 0

    async def fake_json():
        nonlocal call_count
        call_count += 1
        return search_resp if call_count == 1 else detail_resp

    mock_resp = AsyncMock()
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)
    mock_resp.json = fake_json

    mock_sess = AsyncMock()
    mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_sess.__aexit__ = AsyncMock(return_value=None)
    mock_sess.get = MagicMock(return_value=mock_resp)
    mock_session_cls.return_value = mock_sess

    result = await wikipedia_search({"query": "Python", "lang": "en"})
    text = _parse_result(result)
    assert "Python" in text


@patch("app.tools_mcp.server.aiohttp.ClientSession")
async def test_wikipedia_search_no_results(mock_session_cls):
    mock_resp = AsyncMock()
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)
    mock_resp.json = AsyncMock(return_value={"query": {"search": []}})

    mock_sess = AsyncMock()
    mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_sess.__aexit__ = AsyncMock(return_value=None)
    mock_sess.get = MagicMock(return_value=mock_resp)
    mock_session_cls.return_value = mock_sess

    result = await wikipedia_search({"query": "xyznonexistent"})
    text = _parse_result(result)
    assert "未找到" in text


@patch("app.tools_mcp.server.aiohttp.ClientSession")
async def test_wikipedia_search_error(mock_session_cls):
    mock_session_cls.side_effect = Exception("network error")
    result = await wikipedia_search({"query": "test"})
    data = json.loads(_parse_result(result))
    assert data["success"] is False


# ── toutiao_hot_news ──────────────────────────────────────────────────────────

@patch("app.tools_mcp.server.aiohttp.ClientSession")
async def test_toutiao_hot_news_success(mock_session_cls):
    news_data = {
        "data": [
            {"name": "新闻标题1", "url": "https://tt.com/1"},
            {"name": "新闻标题2", "url": "https://tt.com/2"},
        ]
    }
    mock_resp = AsyncMock()
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)
    mock_resp.json = AsyncMock(return_value=news_data)

    mock_sess = AsyncMock()
    mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_sess.__aexit__ = AsyncMock(return_value=None)
    mock_sess.get = MagicMock(return_value=mock_resp)
    mock_session_cls.return_value = mock_sess

    result = await toutiao_hot_news({"limit": 2})
    text = _parse_result(result)
    assert "新闻标题1" in text
    assert "新闻标题2" in text


@patch("app.tools_mcp.server.aiohttp.ClientSession")
async def test_toutiao_hot_news_error(mock_session_cls):
    mock_session_cls.side_effect = Exception("fail")
    result = await toutiao_hot_news({})
    data = json.loads(_parse_result(result))
    assert data["success"] is False


# ── search_domains_info ───────────────────────────────────────────────────────

async def test_search_domains_info_no_key():
    with patch("app.tools_mcp.server.DOMAINSDB_KEY", ""):
        result = await search_domains_info({"query": "example.com"})
    data = json.loads(_parse_result(result))
    assert data["success"] is False
    assert "DOMAINSDB_KEY" in data["message"]


@patch("app.tools_mcp.server.aiohttp.ClientSession")
async def test_search_domains_info_success(mock_session_cls):
    domain_data = {
        "total": 1,
        "domains": [{"domain": "example.com", "country": "US", "create_date": "2020-01-01"}],
    }
    mock_resp = AsyncMock()
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)
    mock_resp.json = AsyncMock(return_value=domain_data)

    mock_sess = AsyncMock()
    mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_sess.__aexit__ = AsyncMock(return_value=None)
    mock_sess.get = MagicMock(return_value=mock_resp)
    mock_session_cls.return_value = mock_sess

    with patch("app.tools_mcp.server.DOMAINSDB_KEY", "fake-key"):
        result = await search_domains_info({"query": "example.com", "limit": 10})
    text = _parse_result(result)
    assert "example.com" in text


# ── generate_image_from_text ──────────────────────────────────────────────────

async def test_generate_image_no_config():
    with patch("app.tools_mcp.server.API_KEY", ""), \
         patch("app.tools_mcp.server.QWEN_CREATE_URL", ""), \
         patch("app.tools_mcp.server.QWEN_GET_URL", ""):
        result = await generate_image_from_text({"prompt": "a cat"})
    data = json.loads(_parse_result(result))
    assert data["success"] is False
    assert "未配置" in data["message"]


@patch("app.tools_mcp.server.asyncio.sleep", new_callable=AsyncMock)
@patch("app.tools_mcp.server.aiohttp.ClientSession")
async def test_generate_image_success(mock_session_cls, mock_sleep):
    create_resp = {"output": {"task_id": "task-001"}}
    check_resp = {
        "output": {
            "task_status": "SUCCEEDED",
            "results": [{"url": "https://img.example.com/1.png"}],
        }
    }

    call_count = 0

    async def fake_json():
        nonlocal call_count
        call_count += 1
        return create_resp if call_count == 1 else check_resp

    mock_post_resp = AsyncMock()
    mock_post_resp.__aenter__ = AsyncMock(return_value=mock_post_resp)
    mock_post_resp.__aexit__ = AsyncMock(return_value=None)
    mock_post_resp.json = fake_json

    mock_get_resp = AsyncMock()
    mock_get_resp.__aenter__ = AsyncMock(return_value=mock_get_resp)
    mock_get_resp.__aexit__ = AsyncMock(return_value=None)
    mock_get_resp.json = fake_json

    mock_sess = AsyncMock()
    mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_sess.__aexit__ = AsyncMock(return_value=None)
    mock_sess.post = MagicMock(return_value=mock_post_resp)
    mock_sess.get = MagicMock(return_value=mock_get_resp)
    mock_session_cls.return_value = mock_sess

    with patch("app.tools_mcp.server.API_KEY", "key"), \
         patch("app.tools_mcp.server.QWEN_CREATE_URL", "http://create"), \
         patch("app.tools_mcp.server.QWEN_GET_URL", "http://get"):
        result = await generate_image_from_text({"prompt": "a cat", "size": "1024*1024", "n": 1})

    data = json.loads(_parse_result(result))
    assert data["success"] is True
    assert len(data["images"]) == 1


@patch("app.tools_mcp.server.aiohttp.ClientSession")
async def test_generate_image_no_task_id_returns_error(mock_session_cls):
    mock_resp = AsyncMock()
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)
    mock_resp.json = AsyncMock(return_value={"output": {}})

    mock_sess = AsyncMock()
    mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_sess.__aexit__ = AsyncMock(return_value=None)
    mock_sess.post = MagicMock(return_value=mock_resp)
    mock_session_cls.return_value = mock_sess

    with patch("app.tools_mcp.server.API_KEY", "key"), \
         patch("app.tools_mcp.server.QWEN_CREATE_URL", "http://create"), \
         patch("app.tools_mcp.server.QWEN_GET_URL", "http://get"):
        result = await generate_image_from_text({"prompt": "a cat"})

    data = json.loads(_parse_result(result))
    assert data["success"] is False
    assert "任务 ID" in data["message"]
