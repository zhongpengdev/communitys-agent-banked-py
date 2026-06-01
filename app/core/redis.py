"""
Redis connection initialization and global client instance.
"""

import redis.asyncio as aioredis
from app.core.config import settings

# 异步 Redis 连接池
redis_pool = aioredis.ConnectionPool(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password,
    decode_responses=True  # 自动将字节转字符串
)

# 实例化全局的 Redis 客户端以复用连接池并提供极致性能
redis_client = aioredis.Redis(connection_pool=redis_pool)