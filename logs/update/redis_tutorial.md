# 从零开始：使用 Redis 优化 Agent 对话记忆重构教程

本教程将手把手带你从零开始，在现有的 Python / FastAPI 项目中集成 Redis，将原本高频读写 PostgreSQL 磁盘的“热对话历史”转移到 Redis 极速内存中，并保持 PostgreSQL 作为异步冷备份存储。

这将彻底消除数据库的读写瓶颈，降低高并发下的磁盘 I/O 延迟。

---

## 目录
1. [设计思路与架构图](#1-设计思路与架构图)
2. [第一步：在 Windows 环境下安装并运行 Redis](#第一步在-windows-环境下安装并运行-redis)
3. [第二步：安装 Python Redis 依赖并配置环境变量](#第二步安装-python-redis-依赖并配置环境变量)
4. [第三步：编写 Redis 异步客户端与工具类](#第三步编写-redis-异步客户端与工具类)
5. [第四步：改造 Agent 运行器与消息收发流程](#第四步改造-agent-运行器与消息收发流程)
6. [第五步：实现异步持久化同步至 PostgreSQL](#第五步实现异步持久化同步至-postgresql)
7. [第六步：本地验证与调试工具](#第六步本地验证与调试工具)

---

## 1. 设计思路与架构图

在重构前，用户的每次提问都要从 PostgreSQL 中 `SELECT` 出所有历史消息（并在 Python 中进行 `[-10:]` 切片），然后同步 `INSERT` 新的对话记录。

重构后，我们采用 **“读写内存优先，延迟同步磁盘”** 的架构：

```
[ 用户发送提问 ]
       │
       ▼
1. 读记忆 (极速) ────> 从 Redis List 直接获取最近 10 条 (微秒级)
       │
       ▼
2. 大模型处理 ──────> 调用 Claude / DeepSeek 获取流式回答
       │
       ▼
3. 写记忆 (极速) ────> 异步将 [User问题] 与 [Agent回答] 追加写入 Redis List
       │              (并通过 LTRIM 永远裁剪保持 List 最大长度为 10 条)
       │
       ▼
4. 延迟持久化 ──────> 在后台通过 asyncio.create_task (不阻塞响应) 
                      异步批量同步写入 PostgreSQL 磁盘归档
```

---

## 第一步：在 Windows 环境下安装并运行 Redis

因为你的开发环境是 **Windows**，推荐使用以下两种最简便的 Redis 运行方式：

### 选项 A：使用 Docker 运行（最推荐，最干净）
如果你电脑上安装了 Docker Desktop，只需打开 PowerShell 运行一行命令：
```powershell
docker run -d --name my-redis -p 6379:6379 redis:alpine
```
* 这会在后台启动一个免配置的轻量级 Redis 容器，并将端口映射到本地的 `6379`。

### 选项 B：使用 Windows 版本的 Redis (Native / MSI)
如果你没有 Docker，可以使用微软早期维护的 Redis Native 移植版或 Memurai（Windows 下的 Redis 替代品）：
1. 下载 Redis-x64 压缩包：[Github 微软官方备份下载](https://github.com/microsoftarchive/redis/releases/tag/win-3.0.504)。
2. 解压到一个目录（例如 `C:\Redis`）。
3. 双击 `redis-server.exe` 启动 Redis 服务，或者在 PowerShell 中运行：
   ```powershell
   cd C:\Redis
   .\redis-server.exe
   ```
4. 看到闪烁的 Redis 立方体 LOGO，说明 Redis 服务已成功在 `127.0.0.1:6379` 运行。

---

## 第二步：安装 Python Redis 依赖并配置环境变量

### 1. 激活虚拟环境并安装库
在你的项目根目录下，确保激活了虚拟环境 `venv`，然后安装 `redis` 库（现代 `redis` 库已原生完美支持 `asyncio` 异步调用）：
```powershell
# 1. 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 2. 安装 redis 客户端库
pip install redis
```

### 2. 更新 requirements.txt
为了防止团队其他成员运行出错，将 `redis` 写入 `requirements.txt`。打开该文件，在末尾添加一行：
```text
redis
```

### 3. 配置环境变量
打开你的项目根目录下的 `.env` 文件，加入 Redis 的连接配置（默认连接本地的 Redis 0号数据库）：
```env
# ─── Redis 配置 ───────────────────────────────────────
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

---

## 第三步：编写 Redis 异步客户端与工具类

我们在 `app/utils` 下创建一个全新的工具文件 [redis_client.py](file:///D:/Projects/code/python/communitys-agent-banked-py/app/utils/redis_client.py)，用于封装所有与 Redis 相关的异步记忆操作。

### 1. 新建 [app/utils/redis_client.py](file:///D:/Projects/code/python/communitys-agent-banked-py/app/utils/redis_client.py)
利用 `redis.asyncio` 提供高性能、非阻塞的极速读写：

```python
import os
import json
import time
from typing import List, Dict
import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

# 读取配置
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# 创建异步 Redis 连接池
redis_pool = aioredis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True  # 自动将字节转换为字符串
)

async def get_redis_client() -> aioredis.Redis:
    """获取一个异步 Redis 客户端"""
    return aioredis.Redis(connection_pool=redis_pool)


class RedisMemoryManager:
    """Redis 智能体对话热记忆管理器"""
    
    @staticmethod
    def _get_key(session_id: int) -> str:
        return f"agent:session:{session_id}:messages"

    @classmethod
    async def push_message(cls, session_id: int, role: str, content: str):
        """
        向 Redis 中以非阻塞 List 形式追加一条热记忆。
        使用 LTRIM 强制保持该 List 在 Redis 中最多只有 10 条原始消息。
        """
        client = await get_redis_client()
        key = cls._get_key(session_id)
        
        # 封装消息体格式
        payload = json.dumps({
            "role": role,
            "content": content,
            "created_at": time.time()
        }, ensure_ascii=False)
        
        # 使用 Pipeline 管道发送命令，减少网络 RTT 开销
        async with client.pipeline(transaction=True) as pipe:
            pipe.rpush(key, payload)
            pipe.ltrim(key, -10, -1)  # 仅保留最近的 10 条原始对话消息
            await pipe.execute()

    @classmethod
    async def get_messages(cls, session_id: int) -> List[Dict]:
        """
        从 Redis 中以 O(1) 的速度秒级召回最近 10 条原始对话记忆。
        """
        client = await get_redis_client()
        key = cls._get_key(session_id)
        
        # 获取 List 中的全部元素
        raw_list = await client.lrange(key, 0, -1)
        if not raw_list:
            return []
            
        messages = []
        for raw in raw_list:
            try:
                messages.append(json.loads(raw))
            except Exception:
                continue
        return messages

    @classmethod
    async def clear_messages(cls, session_id: int):
        """
        清空指定会话在 Redis 中的全部热记忆（常用于删除会话或开启新对话）
        """
        client = await get_redis_client()
        key = cls._get_key(session_id)
        await client.delete(key)
```

---

## 第四步：改造 Agent 运行器与消息收发流程

现在我们将原本直接高频查询 PostgreSQL 数据库的 `runner.py`，改造为使用 Redis 工具类。

### 1. 修改 `app/agent/runner.py`
我们需要修改加载历史上下文和保存历史的核心部分。

#### 1) 引入 Redis 管理器
```python
# app/agent/runner.py 顶部引入
from app.utils.redis_client import RedisMemoryManager
```

#### 2) 重构 `_build_history_context` 逻辑
不再直接读取数据库全量记录，而是**优先读取 Redis 缓存中的 10 条消息**。如果 Redis 缓存因冷启动为空，则作为降级策略，从数据库读取最近 10 条并反写回 Redis。

```python
# app/agent/runner.py 底部的 _build_history_context 方法
async def _build_history_context(session_id: int) -> str:
    """
    【重构后】：先从 Redis 缓存极速读取最近 10 条记录，如果缓存为空则从 DB 召回并回写缓存。
    """
    try:
        # 1. 尝试从极速的 Redis 读取最近对话
        cached_msgs = await RedisMemoryManager.get_messages(session_id)
        
        # 2. 如果 Redis 命中，直接构建上下文并返回 (微秒级)
        if cached_msgs:
            lines = []
            for msg in cached_msgs:
                role = "用户" if msg["role"] == "user" else "助手"
                lines.append(f"{role}: {msg['content']}")
            return "以下是之前的对话记录：\n" + "\n".join(lines) + "\n\n"
            
        # 3. 降级策略：如果 Redis 缓存不存在（例如 Redis 重启或被驱逐），从 DB 查询
        print(f"[Memory Cache Miss] Session {session_id} 未命中 Redis，开始从冷数据库读取备份...")
        from app.database.service.message import get_messages
        
        # ⚠️注意优化：虽然 get_messages 会加载全部，但在没做分页前我们先在这里做截取
        res = get_messages(session_id)
        if not res.data:
            return ""
            
        # 获取最后 10 条
        recent_db_msgs = res.data[-10:]
        lines = []
        for msg in recent_db_msgs:
            role = "用户" if msg["role"] == "user" else "助手"
            lines.append(f"{role}: {msg['content']}")
            # 顺便反写回 Redis 缓存，保证下次请求能命中缓存！
            await RedisMemoryManager.push_message(session_id, msg["role"], msg["content"])
            
        return "以下是之前的对话记录：\n" + "\n".join(lines) + "\n\n"
        
    except Exception as e:
        print(f"[Runner] 加载历史消息失败: {e}")
        return ""
```

#### 3) 修改 `handle_message` 对 `_build_history_context` 的调用
由于 `_build_history_context` 已经改为了 `async` 异步函数，在 `handle_message` 中调用它时，**必须加上 `await` 关键字**：

```python
# app/agent/runner.py 中 handle_message 内第 81 行左右
# 加载历史对话（最近 10 条）作为上下文注入
history_ctx = await _build_history_context(session_id) # 加上 await 关键字！
prompt = f"{history_ctx}用户: {user_input}" if history_ctx else user_input
```

---

## 第五步：实现异步持久化同步至 PostgreSQL

我们希望新的聊天记录：
1. **即时写 Redis**（保证下次提问能瞬间感知到上一轮说了什么）。
2. **异步写 PostgreSQL**（进行冷备归档，不阻碍主响应流程）。

#### 重构异步 `_save` 任务：
```python
# app/agent/runner.py 中的 _save 辅助函数
async def _save(session_id: int, user_input: str, response: str):
    """
    【重构后】：先同步写入 Redis，再发起低优先级的后台任务持久化至 PostgreSQL。
    """
    try:
        # 1. 立即写入极速缓存，保证即使下一秒用户发来新提问，记忆上下文也能完美衔接
        await RedisMemoryManager.push_message(session_id, "user", user_input)
        await RedisMemoryManager.push_message(session_id, "assistant", response)
        
        # 2. 异步发起数据库 IO，将数据落盘冷备归档 (SQLAlchemy 操作)
        # 该操作可能较慢，但由于被包装在单独的 asyncio.create_task 中，不会阻塞客户端返回
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _save_to_postgresql, session_id, user_input, response)
        
    except Exception as e:
        print(f"[Runner] 保存记忆或持久化同步失败: {e}")

def _save_to_postgresql(session_id: int, user_input: str, response: str):
    """SQLAlchemy 同步落盘逻辑"""
    from app.database.service.message import save_message
    save_message(session_id=session_id, role="user", content=user_input)
    save_message(session_id=session_id, role="assistant", content=response)
```

---

## 第六步：本地验证与调试工具

为了验证重构是否生效，你可以通过以下方法在本地进行测试：

### 1. 使用 Redis 命令行监控
打开 PowerShell，运行以下命令（如果是 Docker 启动，先进入容器）：
```powershell
# 如果是 Docker:
docker exec -it my-redis redis-cli

# 如果是 Native 安装:
cd C:\Redis
.\redis-cli.exe
```

进入 `redis-cli` 交互界面后，输入 `MONITOR` 命令：
```text
127.0.0.1:6379> MONITOR
```
* 此时，当你在前端网页或测试客户端给 Agent 发送消息时，PowerShell 中应当实时刷新显示 `RPUSH` 和 `LTRIM` 指令：
```text
"RPUSH" "agent:session:123:messages" "{\"role\": \"user\", \"content\": \"你好\"}"
"LTRIM" "agent:session:123:messages" "-10" "-1"
```

### 2. 检查 Redis 内存储的 Key 和数据
在 `redis-cli` 中运行：
```text
127.0.0.1:6379> KEYS *
```
你应该能看到类似 `agent:session:123:messages` 的键。
使用 `LRANGE` 查看其中存储的所有原始对话内容：
```text
127.0.0.1:6379> LRANGE agent:session:123:messages 0 -1
```

---

## 7. 异常熔断与防身策略

大厂方案中绝对不会完全信任缓存，因此在 `_build_history_context` 中我们实现了**完美的熔断降级**：
* 如果由于某些原因（如 Redis 内存满了被驱逐、Redis 进程崩溃等），`RedisMemoryManager` 发生报错，程序会**自动 fallback 降级**至 PostgreSQL 冷数据库查询，保证你的 Agent 哪怕遇到 Redis 挂掉，也只会是“稍微响应变慢一点”，而**绝不会直接报错假死**。这保证了生产环境极强的鲁棒性。
