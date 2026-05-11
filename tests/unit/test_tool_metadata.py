"""Unit tests for app/tools/tool_metadata.py"""

import pytest
from app.tools.tool_metadata import (
    TOOL_METADATA,
    get_tool_display_info,
    get_all_tools_metadata,
)

KNOWN_TOOLS = [
    "get_user_notifications",
    "read_notification",
    "query_unpaid_bills",
    "send_private_messages",
    "get_weather",
    "get_time",
    "send_scheduled_email",
    "get_scheduled_email",
    "delete_scheduled_email",
    "web_search",
    "wikipedia_search",
    "toutiao_hot_news",
    "search_domains_info",
    "generate_image_from_text",
    "create_visitor",
    "search_goods",
]


def test_all_known_tools_in_metadata():
    for tool in KNOWN_TOOLS:
        assert tool in TOOL_METADATA, f"{tool} missing from TOOL_METADATA"


def test_each_entry_has_required_fields():
    required = {"display_name", "description", "icon", "category"}
    for name, meta in TOOL_METADATA.items():
        missing = required - set(meta.keys())
        assert not missing, f"{name} is missing fields: {missing}"


def test_get_tool_display_info_known_tool():
    info = get_tool_display_info("get_weather")
    assert info["display_name"] == "查询天气"
    assert info["icon"] == "weather"
    assert info["category"] == "weather"


def test_get_tool_display_info_unknown_tool_returns_defaults():
    info = get_tool_display_info("unknown_tool_xyz")
    assert info["display_name"] == "unknown_tool_xyz"
    assert "unknown_tool_xyz" in info["description"]
    assert info["icon"] == "tool"
    assert info["category"] == "other"


def test_get_all_tools_metadata_returns_dict():
    all_meta = get_all_tools_metadata()
    assert isinstance(all_meta, dict)
    assert len(all_meta) >= len(KNOWN_TOOLS)


def test_get_all_tools_metadata_is_same_as_module_constant():
    assert get_all_tools_metadata() is TOOL_METADATA


def test_display_names_are_nonempty_strings():
    for name, meta in TOOL_METADATA.items():
        assert isinstance(meta["display_name"], str)
        assert len(meta["display_name"]) > 0, f"{name} has empty display_name"


def test_categories_are_valid_strings():
    for name, meta in TOOL_METADATA.items():
        assert isinstance(meta["category"], str)
        assert len(meta["category"]) > 0
