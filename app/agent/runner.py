"""
Claude Agent SDK 核心运行器
使用 ClaudeSDKClient 实现持久会话，替代原有 LangGraph + Qwen 方案
"""

import os
import asyncio
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)
from app.websocket.manager import manager
from app.tools_mcp.server import community_server
from app.tools.tool_metadata import get_tool_display_info
from app.database.service.message import save_message, get_messages

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


# 所有 MCP 工具的全限定名，格式：mcp__<server>__<tool>
_MCP_TOOLS = [
    "mcp__community__get_time",
    "mcp__community__get_weather",
    "mcp__community__query_unpaid_bills",
    "mcp__community__get_user_notifications",
    "mcp__community__read_notification",
    "mcp__community__send_private_messages",
    "mcp__community__create_visitor",
    "mcp__community__search_goods",
    "mcp__community__send_scheduled_email",
    "mcp__community__get_scheduled_email",
    "mcp__community__delete_scheduled_email",
    "mcp__community__web_search",
    "mcp__community__wikipedia_search",
    "mcp__community__toutiao_hot_news",
    "mcp__community__search_domains_info",
    "mcp__community__generate_image_from_text",
]


class AgentSession:
    """
    封装 ClaudeSDKClient，管理单个 WebSocket 连接的 Agent 会话。
    一个 WebSocket 连接对应一个 AgentSession，跨多条消息共享上下文。
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._client: ClaudeSDKClient | None = None

    async def start(self):
        """建立与 Claude Agent SDK 的连接"""
        options = ClaudeAgentOptions(
            model=CLAUDE_MODEL,
            mcp_servers={"community": community_server},
            allowed_tools=_MCP_TOOLS,
            permission_mode="bypassPermissions",
        )
        self._client = ClaudeSDKClient(options=options)
        await self._client.connect()

    async def stop(self):
        """断开连接，释放资源"""
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def handle_message(self, session_id: int, user_input: str):
        """
        处理一条用户消息：
        1. 向 Claude 发送消息（含历史上下文）
        2. 流式将响应推送到 WebSocket
        3. 异步保存消息到数据库
        """
        # 加载历史对话（最近 10 条）作为上下文注入
        history_ctx = _build_history_context(session_id)
        prompt = f"{history_ctx}用户: {user_input}" if history_ctx else user_input

        await manager.send_status(self.user_id, "thinking", {"message": "正在思考..."})

        full_response = ""
        last_tool_name: str | None = None

        await self._client.query(prompt)

        async for msg in self._client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        last_tool_name = block.name
                        short_name = _strip_mcp_prefix(block.name)
                        info = get_tool_display_info(short_name)
                        await manager.send_status(self.user_id, "tool_calling", {
                            "tool": short_name,
                            "display_name": info["display_name"],
                            "message": info["description"],
                            "icon": info["icon"],
                            "category": info["category"],
                        })

                    elif isinstance(block, ToolResultBlock):
                        if last_tool_name:
                            short_name = _strip_mcp_prefix(last_tool_name)
                            info = get_tool_display_info(short_name)
                            await manager.send_status(self.user_id, "tool_completed", {
                                "tool": short_name,
                                "display_name": info["display_name"],
                                "message": f"{info['display_name']}执行完成",
                                "icon": info["icon"],
                                "category": info["category"],
                            })
                            last_tool_name = None

                    elif isinstance(block, TextBlock) and block.text:
                        # 如果前一步是工具调用而尚未发送 tool_completed，在文本前补发
                        if last_tool_name:
                            short_name = _strip_mcp_prefix(last_tool_name)
                            info = get_tool_display_info(short_name)
                            await manager.send_status(self.user_id, "tool_completed", {
                                "tool": short_name,
                                "display_name": info["display_name"],
                                "message": f"{info['display_name']}执行完成",
                                "icon": info["icon"],
                                "category": info["category"],
                            })
                            last_tool_name = None

                        full_response += block.text
                        await manager.send_text_chunk(self.user_id, block.text, is_final=False)

            elif isinstance(msg, ResultMessage):
                # 响应完成
                pass

        # 结束信号
        await manager.send_text_chunk(self.user_id, "", is_final=True)
        await manager.send_status(self.user_id, "completed", {"message": "回答完成"})

        # 异步保存（不阻塞响应）
        if session_id and full_response:
            asyncio.create_task(_save(session_id, user_input, full_response))


# ─── 工具函数 ─────────────────────────────────────────────────────────────────

def _strip_mcp_prefix(name: str) -> str:
    """将 'mcp__community__get_weather' 转换为 'get_weather'"""
    parts = name.split("__")
    return parts[-1] if len(parts) >= 3 else name


def _build_history_context(session_id: int) -> str:
    """从数据库加载最近 10 条消息，构建历史上下文字符串"""
    try:
        res = get_messages(session_id)
        if not res.data:
            return ""
        lines = []
        for msg in res.data[-10:]:
            role = "用户" if msg["role"] == "user" else "助手"
            lines.append(f"{role}: {msg['content']}")
        return "以下是之前的对话记录：\n" + "\n".join(lines) + "\n\n"
    except Exception as e:
        print(f"[Runner] 加载历史消息失败: {e}")
        return ""


async def _save(session_id: int, user_input: str, response: str):
    try:
        save_message(session_id=session_id, role="user", content=user_input)
        save_message(session_id=session_id, role="assistant", content=response)
    except Exception as e:
        print(f"[Runner] 保存消息失败: {e}")
