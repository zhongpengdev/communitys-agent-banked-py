from fastapi import APIRouter, WebSocket, Query
from app.websocket import websocket_chat_handler
from app.utils.JWTutils.jwt_helper import get_user_id
import json

router = APIRouter(tags=["对话"])


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    session_id: int | None = Query(None),
):
    """
    WebSocket 聊天端点

    握手协议：
    - 客户端首条消息必须为：{ "type": "auth", "token": "<JWT>" }
    - 服务端返回：{ "type": "auth_success", "user_id": "..." }
    - 此后双向通信正常消息格式：{ "query": "...", "sessionId": 123 }
    """
    await websocket.accept()

    try:
        # 1. 读取认证消息
        raw = await websocket.receive_text()
        auth_msg = json.loads(raw)
        token = auth_msg.get("token", "")

        if not token:
            await websocket.send_json({"type": "error", "content": "缺少 token"})
            await websocket.close()
            return

        # 2. 验证 token
        try:
            user_id = get_user_id(token)
        except Exception as e:
            print(f"[Dialog] Token 验证失败: {e}")
            await websocket.send_json({"type": "error", "content": f"Token 验证失败: {str(e)}"})
            await websocket.close()
            return

        # 3. 通知前端验证成功
        await websocket.send_json({"type": "auth_success", "user_id": user_id})

        # 4. 进入聊天主循环（连接已 accept，token 传入供工具鉴权使用）
        await websocket_chat_handler(
            websocket,
            user_id=user_id,
            token=token,
            session_id=session_id,
            already_accepted=True,
        )

    except Exception as e:
        print(f"[Dialog] WebSocket 错误: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
