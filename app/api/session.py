from fastapi import APIRouter, Depends, Query
from app.core.security import verify_token
from app.database.service.session import create_session
from app.services.title_generator import generate_title
from app.database.service.session import delete_session_service, rename_session_service
from app.database.service.session import check_session_owner
from app.database.service.message import delete_messages
from app.schemas import (
    BaseResponse,
    PaginatedResponse,
    SessionResponse,
    SessionCreateResponseData,
    NewSessionRequest
)
from app.database.service.session import get_sessions_paginated
from loguru import logger

router = APIRouter(tags=["会话"])


@router.get("/sessions", response_model=PaginatedResponse[SessionResponse])
async def get_session_history(
    user_id: str = Depends(verify_token),
    page: int = Query(1, ge=1, description="当前页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
):
    """获取聊天历史"""

    logger.info(f"用户 ID: {user_id}")

    try:
        result = get_sessions_paginated(user_id, page, page_size)

        logger.info(f"---获取历史记录成功，{result}----")

        # RestFul API
        return {
            "code": 200,
            "message": "获取成功",
            "data": {
                "items": result["items"],  # 具体的会话列表
                "total": result["total"],  # 总条数
                "page": page,
                "page_size": page_size,
            },
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"获取失败，{e}",
            "data": None,
        }




@router.post("/create_new_session", response_model=BaseResponse[SessionCreateResponseData])
async def create_new_session(
    data: NewSessionRequest, user_id: int = Depends(verify_token)
):
    """
    新建会话接口：
    1. 在 sessions 表创建一个新 ID
    2. 在 messages 表存入用户的第一条消息
    """
    try:
        # 生成标题
        title = await generate_title(data.content)

        # 1. 创建 Session 记录
        session_res = create_session(user_id, title)

        if not session_res:
            return {"code": 500, "message": "创建会话记录失败", "data": None}

        new_session_id = session_res["id"]

        # 3. 返回给前端
        return {
            "code": 200,
            "message": "会话创建成功",
            "data": {
                "sessionId": new_session_id,
                "title": title,
            },
        }

    except Exception as e:
        return {"code": 500, "message": f"服务器内部错误: {str(e)}", "data": None}


# 删除会话
@router.delete("/delete-session", response_model=BaseResponse[None])
async def delete_session(session_id: int, user_id: int = Depends(verify_token)):
    try:
        if not check_session_owner(session_id, user_id):
            return {"code": 403, "message": "无权访问此会话", "data": None}

        deleted_session = delete_session_service(session_id)

        deleted_messages = delete_messages(session_id)

        if deleted_session and deleted_messages:
            return {"code": 200, "message": "会话删除成功", "data": None}

        return {"code": 500, "message": "会话删除失败", "data": None}
    except Exception as e:
        return {"code": 500, "message": f"服务器内部错误: {str(e)}", "data": None}
    
# 会话标题重命名
@router.post("/rename-session", response_model=BaseResponse[None]) 
async def rename_session(session_id: int, rename_title: str, user_id: int = Depends(verify_token)):
    try:
        if not check_session_owner(session_id, user_id):
            return {"code": 403, "message": "无权访问此会话", "data": None}
        
        have_renamed = rename_session_service(session_id, rename_title)
    
        if have_renamed:
            return {"code": 200, "message": "已修改标题", "data": None}
    
        return {"code": 500, "message": "修改标题失败，稍后重试", "data": None}
    except Exception as e:
        return {"code": 500, "message": f"服务器内部错误: {str(e)}", "data": None}
