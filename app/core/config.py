from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Claude Agent SDK 配置
    anthropic_api_key: str
    claude_model: str = "deepseek-v4-flash"
    claude_title_model: str = "deepseek-v4-flash"
    anthropic_base_url: str = ""

    # 后端服务接口配置
    banked_url: str
    fronted_url: str

    database_url: str

    # Redis 高速缓存配置
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    redis_memory_limit: int = 10
    redis_memory_ttl: int = 1800

    # JWT 认证配置
    jwt_secret: str
    jwt_expiration: int = 604800000

    # 第三方检索 API
    serp_key: str = ""
    domainsdb_key: str = ""

    # 通义万相文生图配置
    api_key: str = ""
    qwen_create_text_url: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
    qwen_get_result_url: str = "https://dashscope.aliyuncs.com/api/v1/tasks"

    class Config:
        env_file = ".env"
        # populate_by_name = True

settings = Settings()