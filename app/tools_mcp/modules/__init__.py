# app/tools_mcp/modules/__init__.py

from .system import get_time, get_weather
from .community import (
    query_unpaid_bills,
    get_user_notifications,
    read_notification,
    send_private_messages,
    create_visitor,
    search_goods,
)
from .email import send_scheduled_email, get_scheduled_email, delete_scheduled_email
from .search import web_search, wikipedia_search, toutiao_hot_news, search_domains_info
from .media import generate_image_from_text

# 统一导出所有工具函数列表
ALL_TOOLS = [
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
]
