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
from loguru import logger
load_dotenv()

log_dir = "loguru_logs"
os.makedirs(log_dir, exist_ok=True)

logger.remove()

logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"  # 生产环境控制台一般只显示 INFO 及以上级别
)

logger.add(
    os.path.join(log_dir, "app_{time:YYYYMMDD}.log"),  # 按天分割日志文件
    rotation="00:00",        # 每天凌晨 00:00 自动切分新文件
    retention="7 days",      # 只保留最近 7 天的日志，超出的自动删除
    compression="zip",       # 旧的日志文件自动打包成 zip 压缩，节省磁盘空间
    encoding="utf-8",        # 防止中文乱码
    level="DEBUG",           # 文件中记录更详细的 DEBUG 信息，方便出问题时排查
    backtrace=True,          # 发生异常时显示完整的调用链
    diagnose=True            # 显示异常的详细上下文变量（生产环境若担心泄露敏感信息可设为 False）
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await HttpClientManager.init_session()
    yield
    
    await HttpClientManager.close_session()

app = FastAPI(title="Community Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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
