# 5.29

1. 优化了冷启动时redis写回策略
```python
    @classmethod
    async def push_messages_batch(cls, session_id: int, messages: list[dict]):
        """
        将所有的历史消息一次性推入列表，并在 Pipeline 尾端统一执行 LTRIM 截断与 EXPIRE 延时。
        将服务冷启动阶段的未命中的历史消息写回延迟降低，提升主事件循环的调度效率。
        """
        if not messages:
            return
        
        key = cls._get_key(session_id)
        payloads = [
            json.dumps({
                "role": msg["role"],
                "content": msg["content"],
                "create_at": msg.get("create_at") or time.time()
            }, ensure_ascii=False) for msg in messages
        ]
        
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.rpush(key, *payloads)
            pipe.ltrim(key, -10, -1)  # 保留最近的 10 条对话
            
            pipe.expire(key, 1800) # 半小时过期一次
            await pipe.execute()
```

2. 结构化提示词与Prompt Caching（未修改）
```
    [
      {"role": "user", "content": "你好"},
      {"role": "assistant", "content": "你好！有什么可以帮助你？"},
      {"role": "user", "content": "帮我查询天气"}
    ]
```
通过这种方式，大模型可以在底层网络中直接识别角色边界，以原生多对话状态处理上下文。这能显著提高大模型对上下文意图的理解精确度，并在使用MCP 工具时防止误调用。

# 6.1
1. 使用BaseSetting重构了变量导入
2. 重构了core service model层

# 6.2
1. 重构了loguru 以及日志 `core/logger.py`
2. 将单例http重构到了 `core/http.py`