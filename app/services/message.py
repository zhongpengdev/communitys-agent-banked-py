"""
会话消息业务逻辑服务层 (Service Layer)
协调 API 控制层/WebSocket 处理器与底层数据库消息仓储层之间的交互
"""

from app.database.repository.message import (
    save_message as db_save_message,
    get_messages as db_get_messages,
    get_recent_messages as db_get_recent_messages,
)

def save_message(session_id: int, role: str, content: str):
    """
    保存一条消息到数据库
    """
    return db_save_message(session_id, role, content)


def get_messages(session_id: int):
    """
    获取某个会话的所有历史消息
    """
    return db_get_messages(session_id)


def get_recent_messages(session_id: int, limit: int = 10):
    """
    获取最近指定数量的历史消息（用于上下文热记忆）
    """
    return db_get_recent_messages(session_id, limit)
