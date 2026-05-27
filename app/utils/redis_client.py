import os
import json
import time
from typing import List, Dict
from dotenv import load_dotenv
import redis.asyncio as aioredis

load_dotenv()

# redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None

# 异步 Redis 连接池
redis_pool = aioredis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True  # 自动将字节转字符串
)

# 建议：实例化一个全局的 Redis 客户端，复用连接池，避免每次操作都重新实例化，提升性能
redis_client = aioredis.Redis(connection_pool=redis_pool)


class RedisMemoryManager:
    @staticmethod
    def _get_key(session_id: int) -> str:
        return f"agent:session:{session_id}:messages"
    
    @classmethod
    async def push_message(cls, session_id: int, role: str, content: str):
        """
        向 Redis 中以非阻塞 List 追加一条热记忆。
        使用 LTRIM 保持最多 10 条原始数据。
        """
        key = cls._get_key(session_id)
        
        # 封装消息格式
        # 【fix】：json.dump 用于写入文件对象，转换为字符串必须用 json.dumps
        payload = json.dumps({
            "role": role,
            "content": content,
            "create_at": time.time()
        }, ensure_ascii=False)
        
        # 使用 Pipeline 管道发送命令，复用连接
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.rpush(key, payload)
            pipe.ltrim(key, -10, -1)  # 保留最近的 10 条对话
            
            pipe.expire(key, 1800) # 半小时过期一次
            await pipe.execute()
            
    @classmethod
    async def get_message(cls, session_id: int) -> List[Dict]:
        """
        从 Redis 中获取最近的 10 条消息。
        """
        key = cls._get_key(session_id)
        
        # 【fix】：lrange(key, 10, -1) 在列表长度最大只有 10 时会返回空列表。
        # 应该使用 lrange(key, 0, -1) 来获取列表中的所有元素（因为 ltrim 已经保证它最大为 10）。
        raw_list = await redis_client.lrange(key, 0, -1)
        if not raw_list:
            return []
        
        messages = []
        for raw in raw_list:
            try:
                # 【fix】：json.load 用于从文件对象中加载，解析字符串必须使用 json.loads
                messages.append(json.loads(raw))
            except Exception as e:
                print(f"[RedisMemory] 反序列化失败: {e}")
                continue
            
        return messages
        
    @classmethod
    async def clear_message(cls, session_id: int):
        """
        清空 session_id 在 Redis 中的热数据：用户删除会话，开启新的会话
        """
        key = cls._get_key(session_id)
        await redis_client.delete(key)
