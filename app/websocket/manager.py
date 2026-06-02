"""
WebSocket 连接管理器
用于管理 WebSocket 连接和消息发送
"""

from fastapi import WebSocket
from typing import Dict
from loguru import logger


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 存储活跃的连接：{user_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """
        接受 WebSocket 连接

        Args:
            websocket: WebSocket 连接对象
            user_id: 用户 ID
        """
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(
            f"已建立一个websocket连接 | User {user_id} connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, user_id: str):
        """
        断开连接

        Args:
            user_id: 用户 ID
        """
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(
                f"关闭一个连接 | User {user_id} disconnected. Total connections: {len(self.active_connections)}"
            )

    async def send_message(self, user_id: str, message: dict):
        """
        发送消息给指定用户

        Args:
            user_id: 用户 ID
            message: 消息字典
        """
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")
                self.disconnect(user_id)
                # 抛出异常，让上层知道连接已断开
                raise RuntimeError(f"WebSocket send failed for user {user_id}: {e}")

    async def send_text_chunk(self, user_id: str, chunk: str, is_final: bool = False):
        """
        发送文本片段（打字机效果）

        Args:
            user_id: 用户 ID
            chunk: 文本片段
            is_final: 是否是最后一个片段
        """
        message = {"type": "chunk", "content": chunk, "is_final": is_final}
        await self.send_message(user_id, message)

    async def send_error(self, user_id: str, error: str):
        """
        发送错误消息

        Args:
            user_id: 用户 ID
            error: 错误信息
        """
        message = {"type": "error", "content": error}
        await self.send_message(user_id, message)

    async def send_status(self, user_id: str, status: str, data: dict = None):
        """
        发送状态消息

        Args:
            user_id: 用户 ID
            status: 状态（如 "thinking", "tool_calling", "completed"）
            data: 额外数据
        """
        message = {"type": "status", "status": status, "data": data or {}}
        await self.send_message(user_id, message)


# 创建全局连接管理器实例
manager = ConnectionManager()
