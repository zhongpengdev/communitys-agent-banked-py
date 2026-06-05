import os, sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.api.session import router as session_router
from app.api.dialog import router as dialog_router
from app.api.tools import router as tools_router
from app.api.message import router as message_router
from app.core.http import HttpClientManager
from contextlib import asynccontextmanager
from app.core.logger import setup_app_logging
from app.core.config import settings

load_dotenv()

# 初始化全局统一日志配置，并开启标准库/第三方日志拦截
setup_app_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await HttpClientManager.init_session()
    yield
    
    await HttpClientManager.close_session()

app = FastAPI(title="Community Agent API", lifespan=lifespan)

# 工业级跨域配置：从配置中动态加载允许的源（支持逗号分隔），并附带本地开发默认域。
# 开启 allow_credentials=True 时，origins 必须是具体的域名，绝对不能使用通配符 "*"。
origins = []
if settings.fronted_url:
    origins.extend([origin.strip() for origin in settings.fronted_url.split(",") if origin.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(session_router)
app.include_router(dialog_router)
app.include_router(tools_router)
app.include_router(message_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8081"))
    uvicorn.run(app, host="0.0.0.0", port=port)
