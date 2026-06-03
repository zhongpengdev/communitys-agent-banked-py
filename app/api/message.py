from fastapi import APIRouter, Depends
from app.core.security import verify_token
from app.database.service.message import get_messages
from app.database.service.session import check_session_owner

router = APIRouter(prefix="/message", tags=["消息"])


@router.get("/get-all-messages")
async def get_all_message(session_id: int, user_id: str = Depends(verify_token)):
    try:
        if not check_session_owner(session_id, user_id):
            return {"code": 403, "message": "无权访问此会话", "data": None}

        result = get_messages(session_id)

        return {"code": "200", "message": "获取成功", "data": result}

    except Exception as e:
        return {"code": "500", "message": f"获取失败，{e}", "data": None}
