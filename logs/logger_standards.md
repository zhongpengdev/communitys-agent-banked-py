# Loguru 生产级日志规范与标准设计说明书

## 一、 评估结论：部分合规（不符合高标准生产规范）

当前 `main.py` 中的 Loguru 配置对于**本地开发环境（Development）**和单机轻量部署是合理且优雅的。但是，对于**云原生、分布式、高安全等级的生产环境（Production）**，当前配置存在数个严重的不合规项（Non-compliances），无法满足安全审计、日志分析（ELK/Loki）及统一收集的需求。

---

## 二、 核心不合规项深度分析

### 1. 敏感信息泄露风险（Security Compliance Violation）
* **当前配置**：`diagnose=True`
* **问题分析**：在 Loguru 中，`diagnose=True` 会在抛出异常时自动打印当前调用栈中**所有局部变量的具体数值**。虽然这极大地便利了本地 Debug，但在生产环境中，这些变量可能包含数据库密码、JWT Token、用户个人敏感信息（手机号、身份证号、支付令牌等）。一旦写入文件，会导致严重的合规合规审计灾难（如违反 GDPR、PCI-DSS 或中国网络安全法等级保护要求）。
* **标准要求**：生产环境必须强制关闭 `diagnose=False`，仅保留 `backtrace=True`（显示调用栈，不显示变量值）。

### 2. 控制台/文件日志字符污染（Log Pollution via ANSI Colors）
* **当前配置**：控制台采用 `<green>`、`<cyan>` 等 ANSI 颜色标签。
* **问题分析**：颜色代码是通过 ANSI 转义字符（如 `\x1b[32m`）实现的。当日志被重定向到文件、或者由容器引擎（如 Docker, Kubernetes）输出到标准输出时，这些转义字符会被当作原始文本记录下来，导致日志文件中充斥着乱码符号，严重破坏了日志的可读性，并会导致日志解析器（如 Fluentd, Logstash）解析失败。
* **标准要求**：输出到文件或由日志收集器提取的控制台日志必须是纯文本或 JSON 格式，绝不能带有 ANSI 颜色控制字符。

### 3. 缺乏结构化 JSON 日志格式（Non-structured Logging）
* **当前配置**：文件和控制台全部为 plain text 文本流格式。
* **问题分析**：在生产环境中（如 ELK、Grafana Loki、Splunk），日志通常需要被索引和结构化检索。传统的文本日志只能依靠复杂的正则表达式进行拆分，效率极低且易出错。
* **标准要求**：生产环境输出到控制台或文件的日志必须是**结构化 JSON 格式**（包含字段：`timestamp`, `level`, `module`, `function`, `line`, `message`, `exception` 等），便于日志收集器（如 Filebeat, Vector）直接打标签和入库。

### 4. 忽略了第三方库日志（Standard Logging Bypass）
* **当前配置**：仅配置了 Loguru 自身的 Sinks，使用 `from loguru import logger` 进行记录。
* **问题分析**：FastAPI、Uvicorn 访问日志（`uvicorn.access`）、SQLAlchemy 数据库执行日志（`sqlalchemy.engine`）等依赖 Python 标准库 `logging`。目前 Loguru 无法捕获这些第三方库的日志，导致 Uvicorn 报错和请求记录无法写入我们的 `app_*.log` 文件中，造成日志数据源分裂。
* **标准要求**：必须通过拦截器（Interceptor）将标准 Python `logging` 的所有日志流量重定向拦截到 Loguru 中，实现“单一可信源（Single Source of Truth）”。

---

## 三、 生产级标准 Logger 配置指南

为了满足上述合规和规范要求，生产级日志系统应当具备**动态环境识别**、**标准库拦截**、**无色纯文本/JSON 格式化**和**敏感信息保护**能力。

### 1. 标准化 Logger 模块设计 (`app/core/logger.py`)

在重构时，应当将日志初始化独立到 `app/core/logger.py` 中，其标准代码实现如下：

```python
import os
import sys
import logging
from loguru import logger
from app.core.config import settings

# 1. 定义标准库日志拦截器
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # 获得对应的 Loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 找到调用源头，避免定位到拦截器自身
        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def setup_app_logging():
    """生产级日志初始化配置"""
    
    # 移除 Loguru 默认控制台处理器，防止重复输出
    logger.remove()
    
    # 识别当前是否为生产模式（建议在 settings 中配置，如 settings.debug: bool）
    is_debug = getattr(settings, "debug", True)
    log_dir = getattr(settings, "log_dir", "loguru_logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # 2. 控制台 Sink 配置
    if is_debug:
        # 开发模式：控制台使用彩色美化 plain text 格式
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG"
        )
    else:
        # 生产模式：控制台使用结构化 JSON，无任何颜色污染，方便云原生日志收集
        logger.add(
            sys.stdout,
            serialize=True,  # 自动将日志转化为标准单行 JSON 格式
            level="INFO"
        )

    # 3. 文件 Sink 配置
    # 生产环境下对日志文件的安全等级、防溢出、防乱码要求极高
    logger.add(
        os.path.join(log_dir, "app_{time:YYYYMMDD}.log"),
        rotation="00:00",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
        level="DEBUG" if is_debug else "INFO",
        backtrace=True,
        diagnose=False,  # 强制关闭生产环境敏感变量打印，防止数据泄露
    )

    # 4. 拦截并重定向第三方/标准库日志（如 uvicorn, fastapi）
    # 覆盖所有标准库 handler，强行接入 Loguru 管道
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # 针对特定的高噪或关键三方日志做级别微调
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    logger.info("全局生产级日志处理器（Loguru Interceptor）初始化成功。")
```

### 2. 在项目启动时调用

在 `main.py` 中，直接调用该配置函数即可：

```python
from app.core.logger import setup_app_logging

# 优先初始化日志系统，拦截所有后续模块导入时的 logging 动作
setup_app_logging()

# 随后进行 app = FastAPI() 的实例化
```

### 3. 日志最佳实践与开发规约

1. **避免拼接字符串**：使用 Loguru 的内置格式化（大括号 `{}`）或 `f-string`，但推荐使用参数化以提升性能。
2. **记录异常**：在 `except` 块中捕获错误时，强制使用 `logger.exception("简短背景描述")` 代替 `logger.error(str(e))`。这样可以完整抓取堆栈信息，而无需导入 `traceback` 模块。
3. **分级清晰**：
   * `DEBUG`：仅用于细粒度调试，如提取后的敏感 JWT payload、TCP 连接数据包等。
   * `INFO`：系统关键流转节点，如“用户登录成功”、“会话创建成功”、“生命周期关闭”。
   * `WARNING`：非致命故障，如“数据库连接重试”、“MCP 工具返回警告状态”。
   * `ERROR`：捕获到的业务执行异常，但系统能够自行恢复。
   * `CRITICAL`：导致系统崩溃或无法提供服务的致命错误。
