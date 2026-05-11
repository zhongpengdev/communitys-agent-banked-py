"""
会话标题生成器
使用 Anthropic 客户端，模型和 API 地址均从环境变量读取
"""

import os
from anthropic import AsyncAnthropic

CLAUDE_TITLE_MODEL = os.getenv("CLAUDE_TITLE_MODEL", "claude-haiku-4-5-20251001")

_client = AsyncAnthropic(
    base_url=os.getenv("ANTHROPIC_BASE_URL") or None,
)


async def generate_title(content: str) -> str:
    """
    根据用户第一条消息生成 10 字以内的会话标题

    Args:
        content: 用户输入内容

    Returns:
        简短标题字符串，失败时返回 "新会话"
    """
    try:
        message = await _client.messages.create(
            model=CLAUDE_TITLE_MODEL,
            max_tokens=50,
            system="你是一个对话标题生成助手。根据用户输入，生成一个不超过 10 个汉字的简短标题。只返回标题文字，不加引号或解释。如果输入太短或无意义，返回'新会话'。",
            messages=[{"role": "user", "content": content}],
        )
        title = message.content[0].text.strip()
        return title[:20] or "新会话"
    except Exception as e:
        print(f"[TitleGenerator] 生成标题失败: {e}")
        return "新会话"
