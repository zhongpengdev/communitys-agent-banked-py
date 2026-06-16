"""
会话业务逻辑服务层 (Service Layer)
协调 API 控制层与底层数据库仓储层之间的交互
"""

from app.database.repository.session import (
    get_sessions_paginated as db_get_sessions_paginated,
    create_session as db_create_session,
    delete_session_service as db_delete_session_service,
    rename_session_service as db_rename_session_service,
    check_session_owner as db_check_session_owner,
    update_session_title as db_update_session_title,
)

def get_sessions_paginated(user_id: str, page: int = 1, page_size: int = 10):
    """
    获取分页会话历史
    """
    return db_get_sessions_paginated(user_id, page, page_size)


def create_session(user_id: int, title: str):
    """
    创建会话记录
    """
    return db_create_session(user_id, title)


def check_session_owner(session_id: int, user_id: str) -> bool:
    """
    检查会话归属权
    """
    return db_check_session_owner(session_id, user_id)


def delete_session_service(session_id: int) -> bool:
    """
    删除会话
    """
    return db_delete_session_service(session_id)


def rename_session_service(session_id: int, new_title: str) -> bool:
    """
    重命名会话
    """
    return db_rename_session_service(session_id, new_title)


def update_session_title(session_id: int, title: str):
    """
    更新会话标题
    """
    return db_update_session_title(session_id, title)

