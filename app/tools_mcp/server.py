"""
MCP 工具服务器 - 纯净模块化注册中心
"""

from claude_agent_sdk import create_sdk_mcp_server
from app.tools_mcp.modules import ALL_TOOLS

# 一键注册所有模块化工具并向外暴露 community_server 实例
community_server = create_sdk_mcp_server(
    name="community",
    tools=ALL_TOOLS,
)
