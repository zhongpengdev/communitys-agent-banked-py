# 单例模式全局只活跃一个aiohttp实例

import aiohttp
import logging
from typing import Optional

logger = logging.getLogger("app.http")

class HttpClientManager:
    """
    全局单例HTTP管理器
    """
    session: Optional[aiohttp.ClientSession] = None
    
    @classmethod
    def get_session(cls) -> aiohttp.ClientSession:
        # 复用ClientSession实例
        if cls.session is None or cls.session.closed:
            raise RuntimeError("HttpClientManager has not been initialized")

        return cls.session
    
    @classmethod
    async def init_session(cls):
        if cls.session is None or cls.session.closed:
            connector = aiohttp.TCPConnector(
                limit=100, # 最大100个并发连接
                ttl_dns_cache=300, # 缓存DNS解析结果 5分钟
                use_dns_cache=True
            )   
            
            # 统一超时策略
            timeout = aiohttp.ClientTimeout(total=15)
            
            cls.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )   
            
            logger.info("全局 aiohttp.ClientSession 连接池初始化成功。")
            
    @classmethod
    async def close_session(cls):
        if cls.session and not cls.session.closed:
            await cls.session.close()
            logger.info("全局 aiohttp.ClientSession 已关闭释放。")