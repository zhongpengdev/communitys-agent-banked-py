"""
Redis Memory Management Service.
Handles fast-access chat memory operations using Pydantic settings.
"""

import json
import time
import logging
from typing import List, Dict
from app.core.config import settings
from app.core.redis import redis_client

# 初始化标准日志记录器
logger = logging.getLogger("app.redis")


class RedisMemoryManager:
    """
    基于 Redis Pipeline 和 LTRIM 实现的极速热记忆管理器。
    """
    @staticmethod
    def _get_key(session_id: int) -> str:
        return f"agent:session:{session_id}:messages"
    
    @classmethod
    async def push_message(cls, session_id: int, role: str, content: str):
        """
        向 Redis 中以非阻塞 List 追加一条热记忆。
        使用 LTRIM 保持最多 N 条原始数据（从配置 settings.redis_memory_limit 读取）。
        """
        key = cls._get_key(session_id)
        
        payload = json.dumps({
            "role": role,
            "content": content,
            "create_at": time.time()
        }, ensure_ascii=False)
        
        limit = settings.redis_memory_limit
        ttl = settings.redis_memory_ttl
        
        # 使用 Pipeline 管道发送命令，复用连接并提升效率
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.rpush(key, payload)
            pipe.ltrim(key, -limit, -1)  # 保持最近的配置限额条对话
            pipe.expire(key, ttl)        # 每次写入自动续期
            await pipe.execute()
            
    @classmethod
    async def push_messages_batch(cls, session_id: int, messages: list[dict]):
        """
        将所有的历史消息一次性推入列表，并在 Pipeline 尾端统一执行 LTRIM 截断与 EXPIRE 延时。
        降低未命中缓存时的写回开销，提升主事件循环 of 调度效率。
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
        
        limit = settings.redis_memory_limit
        ttl = settings.redis_memory_ttl
        
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.rpush(key, *payloads)
            pipe.ltrim(key, -limit, -1)
            pipe.expire(key, ttl)
            await pipe.execute()
        
    @classmethod
    async def get_message(cls, session_id: int) -> List[Dict]:
        """
        从 Redis 中获取最近缓存的历史消息。
        """
        key = cls._get_key(session_id)
        
        # lrange(key, 0, -1) 获取列表中的所有元素（因为 ltrim 已经截断到 limit 大小）
        raw_list = await redis_client.lrange(key, 0, -1)
        if not raw_list:
            return []
        
        messages = []
        for raw in raw_list:
            try:
                messages.append(json.loads(raw))
            except Exception as e:
                logger.error("[RedisMemory] 反序列化消息失败: %s, 原始数据: %r", e, raw)
                continue
            
        return messages
        
    @classmethod
    async def clear_message(cls, session_id: int):
        """
        清空 session_id 在 Redis 中的热数据。
        """
        key = cls._get_key(session_id)
        await redis_client.delete(key)
