"""
会话业务逻辑服务层 (Service Layer)
协调 API 控制层与底层数据库仓储层之间的交互，支持基于 Redis ZSET 与 String 的索引数据分离缓存机制
"""

import json
import asyncio
from datetime import datetime
from loguru import logger
from app.core.redis import redis_client
from app.database.repository.session import (
    create_session as db_create_session,
    delete_session_service as db_delete_session_service,
    rename_session_service as db_rename_session_service,
    check_session_owner as db_check_session_owner,
    update_session_title as db_update_session_title,
    get_session_by_id as db_get_session_by_id,
    get_user_session_ids_and_created_at as db_get_user_session_ids_and_created_at,
    get_sessions_paginated as db_get_sessions_paginated, # 异常时降级备用
)

INDEX_CACHE_EXPIRE = 86400       # ZSET 索引缓存 1天 (秒)
DETAIL_CACHE_EXPIRE = 604800     # 详情缓存 7天 (秒)


async def get_sessions_paginated(user_id: str, page: int = 1, page_size: int = 10) -> dict:
    """
    分页获取会话历史列表 (ZSET + MGET 索引数据分离架构)
    由于 redis_client 已配置 decode_responses=True，返回值均为 string 类型
    """
    zset_key = f"user:sessions:{user_id}"
    start = (page - 1) * page_size
    stop = start + page_size - 1
    
    # 1. 检查 ZSET 索引缓存是否存在，若不存在则回源构建
    try:
        exists = await redis_client.exists(zset_key)
        if not exists:
            await _rebuild_user_session_index(user_id, zset_key)
    except Exception as e:
        logger.error(f"Redis 检查索引失败，降级回源 DB: {e}")
        return db_get_sessions_paginated(user_id, page, page_size)

    # 2. 从 ZSET 分页获取当前页的 session_id 列表，并获取总数 (ZCARD)
    try:
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.zrevrange(zset_key, start, stop)
            pipe.zcard(zset_key)
            session_ids, total_count = await pipe.execute()
    except Exception as e:
        logger.error(f"Redis 分页查询索引失败: {e}")
        return db_get_sessions_paginated(user_id, page, page_size)

    # ZSET 中可能存在空索引防击穿占位符
    if "placeholder" in session_ids:
        session_ids = [sid for sid in session_ids if sid != "placeholder"]
        total_count = max(0, total_count - 1)

    if not session_ids:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    # 3. 批量 MGET 获取这组 session_id 的详情缓存
    detail_keys = [f"session:detail:{sid}" for sid in session_ids]
    try:
        cached_details = await redis_client.mget(detail_keys)
    except Exception as e:
        logger.error(f"Redis 批量获取会话详情失败: {e}")
        cached_details = [None] * len(session_ids)

    # 4. 遍历详情结果，对缺失缓存的 session_id 进行单条回源并回写
    items = []
    for i, sid in enumerate(session_ids):
        detail_json = cached_details[i]
        
        if detail_json:
            try:
                items.append(json.loads(detail_json))
            except Exception as parse_err:
                logger.error(f"解析会话详情缓存失败: {parse_err}")
                detail_json = None
                
        if not detail_json:
            # 缓存未命中，精准回源 DB 并回写缓存
            session_data = db_get_session_by_id(int(sid))
            if session_data:
                items.append(session_data)
                # 异步单条回写 String 详情缓存
                asyncio.create_task(
                    redis_client.set(
                        f"session:detail:{sid}", 
                        json.dumps(session_data), 
                        ex=DETAIL_CACHE_EXPIRE
                    )
                )

    # 封装为 Controller 期望的 response 结构
    return {
        "items": items,
        "total": total_count
    }


async def _rebuild_user_session_index(user_id: str, zset_key: str):
    """
    回源 DB 加载该用户所有的会话 ID 与时间戳，并重建 ZSET 索引缓存
    """
    try:
        sessions_db = db_get_user_session_ids_and_created_at(user_id)
        
        if not sessions_db:
            # 写入空缓存占位符以防止缓存穿透，设置较短的过期时间 (60秒)
            async with redis_client.pipeline(transaction=True) as pipe:
                pipe.delete(zset_key)
                pipe.zadd(zset_key, {"placeholder": 0})
                pipe.expire(zset_key, 60)
                await pipe.execute()
            return

        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.delete(zset_key)
            for s in sessions_db:
                created_at = s["created_at"]
                # 优先获取 created_at，缺省使用当前时间戳保证排序
                score = created_at.timestamp() if isinstance(created_at, datetime) else datetime.utcnow().timestamp()
                pipe.zadd(zset_key, {str(s["id"]): score})
            pipe.expire(zset_key, INDEX_CACHE_EXPIRE)
            await pipe.execute()
    except Exception as e:
        logger.error(f"重建用户 ZSET 会话索引缓存失败: {e}")


def create_session(user_id: int, title: str) -> dict:
    """
    同步创建会话记录，并异步将其 ID 添加入 ZSET 缓存，同时直接写入 String 详情缓存
    """
    session_res = db_create_session(user_id, title)
    if not session_res:
        return {}
        
    session_id = session_res["id"]
    created_at_str = session_res["created_at"]
    
    try:
        # 兼容带 'Z' 的 UTC 字符串时间转换
        dt_str = created_at_str.replace("Z", "+00:00") if created_at_str else None
        score = datetime.fromisoformat(dt_str).timestamp() if dt_str else datetime.utcnow().timestamp()
    except Exception:
        score = datetime.utcnow().timestamp()

    zset_key = f"user:sessions:{user_id}"
    detail_data = {
        "id": session_id,
        "user_id": str(user_id),
        "title": title,
        "created_at": created_at_str
    }
    
    # 异步同步写入 Redis 索引与详情
    async def _write_cache():
        try:
            async with redis_client.pipeline(transaction=True) as pipe:
                pipe.zadd(zset_key, {str(session_id): score})
                pipe.set(f"session:detail:{session_id}", json.dumps(detail_data), ex=DETAIL_CACHE_EXPIRE)
                await pipe.execute()
        except Exception as err:
            logger.error(f"创建会话同步写入缓存失败: {err}")
            
    asyncio.create_task(_write_cache())
    return session_res


def check_session_owner(session_id: int, user_id: str) -> bool:
    """
    检查会话归属权
    """
    return db_check_session_owner(session_id, user_id)


def delete_session_service(session_id: int, user_id: str | None = None) -> bool:
    """
    删除会话，同步级联删除数据库，并清理 Redis 索引与详情
    """
    if not user_id:
        # 降级：若上层未传入，先查数据库以获得所属 user_id 用来构造 key
        session_data = db_get_session_by_id(session_id)
        if session_data:
            user_id = session_data["user_id"]

    db_success = db_delete_session_service(session_id)
    if not db_success:
        return False
        
    if user_id:
        zset_key = f"user:sessions:{user_id}"
        detail_key = f"session:detail:{session_id}"
        
        async def _clean_cache():
            try:
                async with redis_client.pipeline(transaction=True) as pipe:
                    pipe.zrem(zset_key, str(session_id))
                    pipe.delete(detail_key)
                    await pipe.execute()
            except Exception as err:
                logger.error(f"删除会话时清理缓存失败: {err}")
                
            # 清空对话记忆
            try:
                from app.services.memory import RedisMemoryManager
                await RedisMemoryManager.clear_message(session_id)
            except Exception as err:
                logger.error(f"清理会话对话热缓存失败: {err}")
                
        asyncio.create_task(_clean_cache())
        
    return True


def rename_session_service(session_id: int, new_title: str) -> bool:
    """
    重命名会话，同步写 DB，并精确单条覆盖写入 String 详情缓存，保持 ZSET 命中率 100%
    """
    db_success = db_rename_session_service(session_id, new_title)
    if not db_success:
        return False
        
    detail_key = f"session:detail:{session_id}"
    
    async def _update_cache():
        session_data = db_get_session_by_id(session_id)
        if session_data:
            try:
                await redis_client.set(detail_key, json.dumps(session_data), ex=DETAIL_CACHE_EXPIRE)
            except Exception as err:
                logger.error(f"覆盖写入会话详情缓存失败: {err}")
                
    asyncio.create_task(_update_cache())
    return True


def update_session_title(session_id: int, title: str):
    """
    修改标题 (供 WebSocket 处理器后台任务使用)
    """
    session_res = db_update_session_title(session_id, title)
    if not session_res:
        return {}
        
    detail_key = f"session:detail:{session_id}"
    
    async def _update_cache():
        session_data = db_get_session_by_id(session_id)
        if session_data:
            try:
                await redis_client.set(detail_key, json.dumps(session_data), ex=DETAIL_CACHE_EXPIRE)
            except Exception as err:
                logger.error(f"覆盖写入会话详情缓存失败: {err}")
                
    asyncio.create_task(_update_cache())
    return session_res
