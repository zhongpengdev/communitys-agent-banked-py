"""
WebSocket 聊天处理器
使用 Claude Agent SDK 的 AgentSession 替代 LangGraph
"""

import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from app.websocket.manager import manager
from app.agent.runner import AgentSession
from app.database.service.session import create_session, update_session_title
from app.services.title_generator import generate_title
from app.utils.context import set_request_token


async def websocket_chat_handler(
    websocket: WebSocket,
    user_id: str,
    token: str,
    session_id: int | None = None,
    already_accepted: bool = False,
):
    """
    WebSocket 聊天处理器主函数

    生命周期：
    1. 建立 WebSocket 连接
    2. 创建并启动 AgentSession（持久化到 WebSocket 断开）
    3. 循环接收用户消息 → 流式响应 → 保存记录
    4. 断开时清理 AgentSession

    Args:
        websocket: WebSocket 连接对象
        user_id: 已通过 JWT 验证的用户 ID
        token: 原始 JWT token（工具调用时用于 API 鉴权）
        session_id: 初始会话 ID（可通过消息体动态切换）
        already_accepted: 连接是否已在上层 accept
    """
    if not already_accepted:
        await manager.connect(websocket, user_id)
    else:
        manager.active_connections[user_id] = websocket

    # 每个 WebSocket 连接独占一个 AgentSession
    agent = AgentSession(user_id)
    await agent.start()

    current_session_id = session_id

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            query_text = data.get("query", "")
            # 支持消息体中携带 sessionId 动态切换会话
            current_session_id = (
                data.get("session_id") or data.get("sessionId") or current_session_id
            )

            if not query_text:
                continue

            # 每次消息前将 token 注入 contextvars，供 MCP 工具使用
            set_request_token(token)

            # 若无会话，先自动创建
            if not current_session_id:
                try:
                    session_res = create_session(user_id, "新对话")
                    if session_res.data:
                        current_session_id = session_res.data[0]["id"]
                        await manager.send_message(user_id, {
                            "type": "session_created",
                            "data": {"sessionId": current_session_id, "title": "新对话"},
                        })
                        asyncio.create_task(
                            _bg_update_title(current_session_id, query_text, user_id)
                        )
                    else:
                        await manager.send_error(user_id, "创建会话失败，请稍后重试")
                        continue
                except Exception as db_err:
                    print(f"[WebSocket] 数据库错误: {db_err}")
                    await manager.send_error(user_id, "数据库操作失败，请检查配置")
                    continue

            # 调用 Agent 处理消息并流式推送
            try:
                await agent.handle_message(current_session_id, query_text)
            except Exception as agent_err:
                print(f"[WebSocket] Agent 错误: {agent_err}")
                await manager.send_error(user_id, f"处理消息时出错: {type(agent_err).__name__}")
                await manager.send_status(user_id, "completed", {"message": "出错了"})

    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        import traceback
        print(f"[WebSocket] 错误: {e}")
        print(traceback.format_exc())
        try:
            await manager.send_error(user_id, f"处理出错: {str(e)}")
        except Exception:
            pass
        manager.disconnect(user_id)
    finally:
        await agent.stop()


async def _bg_update_title(session_id: int, content: str, user_id: str):
    """后台任务：生成会话标题并通知前端"""
    try:
        new_title = await generate_title(content)
        update_session_title(session_id, new_title)
        await manager.send_message(user_id, {
            "type": "session_updated",
            "data": {"sessionId": session_id, "title": new_title},
        })
    except Exception as e:
        print(f"[WebSocket] 后台生成标题失败: {e}")
