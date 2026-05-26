# Multi-User Multi-Tenant & Coroutine-Local ContextVars (多用户隔离与 ContextVars 详解)

本文档将深入分析在面对高并发、多用户同时在线的场景下，本项目（Community Agent API）是如何实现**多用户隔离（多租户状态管理）**的，以及在 Python 异步协程机制中，如何利用 **`ContextVars`** 实现安全的“协程本地存储”，防止用户身份凭证交叉污染。

---

## 1. 多租户/多用户隔离的核心设计

为了保证用户 A 的对话历史、Agent 会话状态、数据库记录以及代表其身份的 API 凭证**绝对不与**用户 B 混淆，系统在四个层级上实施了隔离设计：

```
+-------------------------------------------------------------------------+
|                         Layer 1: 连接层隔离                              |
|   ConnectionManager.active_connections = { "user_A": WS, "user_B": WS } |
+-------------------------------------------------------------------------+
                                     |
+-------------------------------------------------------------------------+
|                         Layer 2: 实例层隔离                              |
|   每个 WebSocket 协程拥有专属的 AgentSession 实例，不共享任何内存缓冲        |
+-------------------------------------------------------------------------+
                                     |
+-------------------------------------------------------------------------+
|                         Layer 3: 状态层隔离 (ContextVars)                |
|   利用 contextvars 库在底层协程间安全传递各自用户的 JWT Token              |
+-------------------------------------------------------------------------+
                                     |
+-------------------------------------------------------------------------+
|                         Layer 4: 数据存储隔离                            |
|   数据库消息表与会话表绑定唯一 user_id，按 session_id 进行范围查询         |
+-------------------------------------------------------------------------+
```

### 层级一：WebSocket 物理连接隔离
在 [manager.py](file:///D:/Projects/code/python/communitys-agent-banked-py/app/websocket/manager.py) 中，`ConnectionManager` 通过一个哈希表维护所有活跃连接：
```python
self.active_connections: Dict[str, WebSocket] = {}
```
* **键 (Key)**：经过 JWT 安全解密出来的唯一用户 ID `user_id`。
* **值 (Value)**：专属的 `WebSocket` TCP 套接字连接。
* **效果**：每个用户的网络通信在操作系统层面是完全独立的，服务端往 `active_connections["user_A"]` 发送消息，绝无可能被 "user_B" 接收。

### 层级二：AgentSession 实例级隔离
在 [routes.py](file:///D:/Projects/code/python/communitys-agent-banked-py/app/websocket/routes.py) 中，每当有一个新的 WebSocket 握手成功，都会在专属的协程栈里即时实例化一个独立的运行器：
```python
# 每个 WebSocket 协程独占一个独立的 AgentSession 实例
agent = AgentSession(user_id)
await agent.start()
```
* **效果**：这意味着内存中会有多个 `AgentSession` 实例并行工作。每个实例内部持有各自独立的 `ClaudeSDKClient` 连接和上下文变量。**用户 A 的 Agent 在运行时，其内存地址、状态和属性与用户 B 没有任何交集**。

### 层级三：数据持久化隔离
所有的历史消息在入库（PostgreSQL）和读取时，都强依赖于 `session_id`。而 `session_id` 在创建时是与当前认证的 `user_id` 强绑定的。因此：
* 用户 A 只能查询到属于自己的 `session_id` 的聊天历史（最近 10 条）。
* 在组装历史 Context 时，底层查询只会召回当前用户的私有对话。

---

## 2. 协程本地存储 ContextVars 深度解析

在大模型应用中，一个经典难题是：**如何让底层的工具函数（Tool）在无需层层传递参数的前提下，隐式获取到当前请求用户的 JWT Token 并用于微服务接口鉴权？**

本项目完美的解决方案正是 **`ContextVars`**。

### 2.1 什么是 `ContextVars`？
`ContextVars` 是 Python 3.7+ 引入的标准库 `contextvars`。
* 在**多线程**同步编程中，我们使用 **Thread-Local Storage（线程本地存储）** 来把数据绑定到线程。每个线程访问同一个全局变量时，读写的都是各自线程的私有副本。
* 然而，在 FastAPI / Uvicorn 等**异步协程**框架中，**成百上千个用户的并发请求都在同一个单线程上调度**！协程（`async def`）之间通过 `await` 不断交还控制权。
* 如果在异步场景下使用传统的 Thread-Local 变量，**用户 A 的 Token 就会直接覆盖用户 B 的 Token**，造成严重的越权和混乱。
* `ContextVars` 正是专门为**协程**量身定做的。它提供了 **“Coroutine-Local”**。当 asyncio 事件循环在不同的任务（Task）之间切换时，Python 会自动备份并恢复对应的 `ContextVars` 变量集合，从而在单个线程内部的并发协程间画出了绝对安全的“物理边界”。

---

### 2.2 本项目中 ContextVars 的流转机制

#### 1) 声明上下文变量
在 [context.py](file:///D:/Projects/code/python/communitys-agent-banked-py/app/utils/context.py) 中，声明了一个全局的上下文承载对象 `request_token`：
```python
# app/utils/context.py
from contextvars import ContextVar
from typing import Optional

# 创建一个用于存储字符串（即用户的 JWT）的协程级全局变量，默认值为 None
request_token: ContextVar[Optional[str]] = ContextVar("request_token", default=None)

def set_request_token(token: str):
    request_token.set(token)  # 仅在此协程上下文内设值

def get_request_token() -> Optional[str]:
    return request_token.get()  # 仅在此协程上下文内取值
```

#### 2) 接收消息时写入
在 [routes.py](file:///D:/Projects/code/python/communitys-agent-banked-py/app/websocket/routes.py) 中，每次用户发来消息触发协程任务时，立即将该用户的 `token` 写入上下文变量：
```python
# app/websocket/routes.py
while True:
    raw = await websocket.receive_text()
    data = json.loads(raw)
    
    # 每次处理消息前，在当前协程的私有上下文中写入该用户的 token
    set_request_token(token)
    
    # 后续执行的所有深度异步调用，都将承袭这个上下文
    await agent.handle_message(current_session_id, query_text)
```

#### 3) 底层工具执行时隐式获取
当大模型决策去调用如 `query_unpaid_bills` 这样需要鉴权的社区业务接口时，Python 端的工具注册函数在执行 HTTP 请求前，直接从上下文变量中提取：
```python
# app/tools_mcp/server.py
def _auth_headers() -> dict:
    # 隐式获取，无需将 token 声明为函数参数
    token = get_request_token()  
    return {"Authorization": f"Bearer {token}"} if token else {}

async def _get(endpoint: str, params: dict = None) -> dict:
    url = f"{BANKED_URL}{endpoint}"
    async with aiohttp.ClientSession() as s:
        # _auth_headers() 会自动把该用户的专用 Token 附加到 HTTP 请求头中发送给后端微服务
        async with s.get(url, params=params, headers=_auth_headers()) as r:
            return await r.json()
```

---

### 2.3 为什么不直接在工具参数里传 Token？

如果选择直接把 Token 声明在 `@tool` 修饰的 Python 函数参数里（例如 `async def query_unpaid_bills(args: dict, token: str)`），会引发以下严重的设计危机：
1. **打破标准协议**：大模型并不懂你的系统鉴权机制，它的 Schema 参数纯粹服务于业务（如“账单状态”）。让大模型去生成、装配并传递 `token` 给工具是绝无可能的。
2. **底层 SDK 的侵入修改**：如果使用参数传递，`claude-agent-sdk` 内部进行工具反射和调用时，就必须拦截并强行注入额外的 `token`，这会导致业务代码与底层第三方依赖包发生深度耦合。
3. **极差的可维护性**：一旦未来有 30 个甚至更多工具需要鉴权，开发人员就必须被迫在每个函数的参数列表中硬编码 `token` 参数，维护成本极高。

---

## 3. 并发切换时的安全性论证（以 A/B 用户为例）

为了确保绝无可能发生“串号”，我们可以通过以下具体的并发调度时序来验证 `ContextVars` 的安全性：

```
[时间轴轴线 ---->]

协程任务 A (处理用户 A): 
├─ 运行: set_request_token("JWT_A")
├─ 运行: 组装 Prompt 并调用 Claude SDK
└─ 运行: await self._client.query(prompt) ──> (遇到 I/O 阻塞，交出 CPU 控制权) 
                                                 │
                                           [发生协程切换]
                                                 │
协程任务 B (处理用户 B):                             ▼
├─ 运行: set_request_token("JWT_B")  <── (Python 自动将上下文变量空间切换为任务 B 的私有环境)
├─ 运行: 组装 Prompt 并调用 Claude SDK
└─ 运行: await self._client.query(...) ───> (遇到 I/O 阻塞，交出 CPU 控制权)
                                                 │
                                           [发生协程切换]
                                                 │
协程任务 A (处理用户 A 恢复运行):                      ▼
└─ 运行: 大模型回复触发工具 -> 执行 query_unpaid_bills -> 调用 _auth_headers()
   └─ 运行: get_request_token() ──> 稳稳拿到 "JWT_A" (Python 已自动切回任务 A 的独立上下文空间)
```

### 结论
通过上述机制，**即使高并发请求在单一物理线程上以非阻塞的协程方式频繁切换，每个用户专属的凭证也始终被完美锁死在各自的任务生命周期里**。这正是本系统能够支持多租户、多用户稳定运行，并保证接口高度安全的核心秘密。
