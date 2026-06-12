"""
会话标题生成器
使用 Anthropic 客户端，模型和 API 地址均从环境变量读取
"""

from anthropic import AsyncAnthropic
from app.core.config import settings
from loguru import logger

CLAUDE_TITLE_MODEL = settings.claude_title_model

_client = AsyncAnthropic(
    base_url=settings.anthropic_base_url,
    api_key=settings.anthropic_api_key
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
            max_tokens=1024,
            system="你是一个对话标题生成助手。根据用户输入，生成一个不超过 10 个汉字的简短标题。只返回标题文字，不加引号或解释。",
            messages=[{"role": "user", "content": content}],
        )
        # 遍历获取首个文本块内容，忽略思考块等其他类型的块，并兼容单元测试的 Mock 对象
        title = "新会话"
        for block in message.content:
            block_type = getattr(block, "type", None)
            if block_type == "text" or (hasattr(block, "text") and not isinstance(block_type, str)):
                title = block.text.strip()
                break
        return title[:20] or "新会话"
    except Exception as e:
        logger.error(f"生成标题失败: {e}")
        return "新会话"
