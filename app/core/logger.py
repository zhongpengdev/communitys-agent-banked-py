import os, sys
import logging
from loguru import logger
from app.core.config import settings

# 标准库日志拦截
class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
            
        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
            
        logger.opt(depth=depth, 
                   exception=record.exc_info).log(level, record.getMessage())        
        
def setup_app_logging():
    
    logger.remove()
    
    # 识别当前环境
    is_debug = settings.debug
    log_dir = settings.log_dir
    os.makedirs(log_dir, exist_ok=True)
    
    # 控制台Sink设置
    if is_debug:
        # 开发者模式
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG"  
        )
    else:
        # 生产环境使用结构化JSON，无颜色
        logger.add(
            sys.stdout,
            serialize=True, # 将日志转化为标准单行JSON
            level="INFO"
        )
        
    # 文件Sink设置，生产环境下的要求
    logger.add(
        os.path.join(log_dir, "app_{time:YYYYMMDD}.log"),  # 按天分割日志文件
        rotation="00:00",        # 每天凌晨 00:00 自动切分新文件
        retention="7 days",      # 只保留最近 7 天的日志，超出的自动删除
        compression="zip",       # 旧的日志文件自动打包成 zip 压缩，节省磁盘空间
        encoding="utf-8",        
        level="DEBUG" if is_debug else "INFO",
        backtrace=True,          # 发生异常时显示完整的调用链
        diagnose=False
    )
    
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    logger.info("全局生产级日志处理器（Loguru Interceptor）初始化成功。")