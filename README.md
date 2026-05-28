# 智能社区 AI Agent 后端系统

本项目是基于 FastAPI、WebSocket 以及 Claude Agent SDK 构建的高性能、模块化智能社区 AI Agent 后端服务系统。

系统通过集成大语言模型的意图识别与工具调用能力，为社区用户提供费用查询、访客登记、公告通知、定时邮件、网络检索以及 AI 绘图等多维度智能化管家服务。

---

## 核心技术架构设计

### 1. 异步实时流式通信
- 采用高性能 FastAPI WebSockets 协议，建立低延迟的长连接会话通道。
- 结合 Claude Agent SDK 提供的流式响应生成能力（handle_message 方法），实现 Thinking 状态追踪与文本 Chunk 流式下发，向客户端提供低延迟的流式交互体验。

### 2. 双层 Chat 记忆缓存机制 (Redis + PostgreSQL)
针对高频会话上下文读写磁盘的性能瓶颈，系统设计了双层混合存储记忆架构：
- **内存滑动窗口缓存**：在 Redis 内存中维护每个会话最近的 10 条活跃消息（基于 LTRIM 操作实现滑动窗口），使用 Pipeline 批处理减少网络往返时延，并配以 24 小时动态滑动续期过期策略（TTL）。
- **异步非阻塞持久化**：采用 asyncio.to_thread 机制，在后台线程将完整对话持久化到 PostgreSQL 数据库，避免阻塞主线程的实时 WebSocket 输出流。
- **主键顺序单调排序**：查询与记忆合并时严格基于自增主键（ID）进行单调升序/降序排列，彻底规避了高并发下使用 created_at 相同时间戳导致的排序抖动和数据重复问题。

### 3. 模块化 MCP 工具注册中心 (Model Context Protocol)
- 采用规范的 Model Context Protocol (MCP) 协议定义工具。
- 将 16 个工具从主服务中完全解耦，放置在 `app/tools_mcp/modules/` 目录下，按照业务职责进行高内聚划分：
  - **system**：系统时间服务、天气查询等系统工具。
  - **community**：物业欠费查询、访客登记、商城搜索、私信与已读处理等社区核心业务工具。
  - **email**：定时邮件发送、查询与删除工具。
  - **search**：Google 联网搜索（SerpAPI）、维基百科检索、今日头条热榜及域名信息反查工具。
  - **media**：基于通义万相（WANX-V1）的文本生成图像工具。
- `app/tools_mcp/server.py` 作为纯净的注册中心，仅用作一键装配及服务暴露，极大降低了组件耦合度。

### 4. 全局高效 HTTP 连接池
- 实现全局单例的 `HttpClientManager` 管理器，集中维护单一的 `aiohttp.ClientSession` 实例。
- 连接池预设最大 100 个并发连接限制，支持 5 分钟 DNS 本地缓存与统一的超时释放策略，消除了频繁建立 TCP 握手带来的连接开销，降低了高并发环境下的 TIME_WAIT 端口耗尽风险。

### 5. 多租户隔离与异步上下文 Token 转发
- 内置基于 JWT (HS512) 算法的用户身份验证机制。
- 采用 Python ContextVars 原生协程上下文实现跨协程的安全多租户数据隔离，确保在任意异步调用链（如工具调用深层网络请求中）均能透明下发当前会话的 Authorization Token，保证了系统多租户隔离的严密性。

---

## 技术栈选型

| 组件 / 框架 | 作用说明 | 选型依据 |
| :--- | :--- | :--- |
| **Python 3.11** | 核心开发语言 | 提供稳定且强大的异步协程原生支持 |
| **FastAPI** | Web 服务框架 | 基于 Starlette 与 Pydantic，提供高性能的异步 ASGI 接口 |
| **Claude Agent SDK** | 智能体框架 | Anthropic 官方 Agent SDK，高度集成意图识别与工具编排 |
| **Redis** | 高速缓存 | 用作会话上下文最新记忆流的极速读写缓存 |
| **PostgreSQL** | 持久化数据库 | 企业级、高可靠的关系型数据库，用作长期数据持久化存储 |
| **SQLAlchemy 2.0** | ORM 映射 | 现代 Python 对象关系映射，支持高性能异步 DB 事务操作 |
| **aiohttp** | 异步网络客户端 | 配合全局连接池，执行非阻塞外部 API 交互请求 |
| **PyJWT** | 身份令牌验证 | 基于 HS512 签名算法生成的安全 JWT Handshake 验证 |
| **Pytest** | 自动化测试框架 | 配合 pytest-asyncio 进行完备的并发和异步场景单元回归 |

---

## 项目目录结构

```text
D:\Projects\code\python\communitys-agent-banked-py
├── app/
│   ├── api/                   # RESTful 控制器（Session, Dialog, Tools, Message）
│   ├── database/              # 数据库连接、Session 封装及 Base 声明
│   ├── models/                # SQLAlchemy 数据模型声明（SessionModel, MessageModel）
│   ├── agent/                 # Agent 核心运行状态（runner.py 业务流编排）
│   ├── tools_mcp/             # MCP 工具集
│   │   ├── base.py            # 工具共享底层 HTTP Core（连接池复用与 Auth 转发）
│   │   ├── server.py          # 极简工具服务器注册中心
│   │   └── modules/           # 16 个工具的模块化业务实现
│   │       ├── system.py      # 系统工具
│   │       ├── community.py   # 社区核心工具
│   │       ├── email.py       # 定时邮件工具
│   │       ├── search.py      # 搜索引擎工具
│   │       └── media.py       # AI 绘图工具
│   ├── utils/                 # 工具类（JWT、Redis、Http 连接池、ContextVars 隔离）
│   └── websocket/             # WebSocket 业务流、JWT 握手及长连接通道管理器
├── tests/                     # 自动化测试套件
│   ├── unit/                  # 单元测试（辅助方法、Redis滑动缓存、MCP 工具流等）
│   └── integration/           # 集成测试（WebSocket 长连接交互、API 身份验证等）
├── main.py                    # 服务入口，统一管理全局 HTTP 资源生命周期 (Lifespan)
├── pytest.ini                 # Pytest 运行配置文件
├── requirements.txt           # 生产运行依赖项
└── requirements-dev.txt       # 开发与测试依赖项
```

---

## 快速开始

### 1. 虚拟环境创建与激活
```bash
# 进入项目根目录
cd communitys-agent-banked-py

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows PowerShell)
.\venv\Scripts\Activate.ps1
```

### 2. 安装项目依赖
```bash
pip install -r requirements-dev.txt
```

### 3. 环境变量配置
复制根目录下的 `.env.example` 并重命名为 `.env`：
```bash
cp .env.example .env
```
根据实际运行环境配置相应的数据库连接、Redis 地址、大模型 API_KEY 以及第三方检索 API 的密钥。

### 4. 运行服务
```bash
python main.py
```
默认服务会运行在本地的 `8081` 端口。

---

## 自动化测试验证

系统具备完备的自动化单元测试与集成测试覆盖，用以保证核心业务流程的回归稳定性。

```bash
# 激活虚拟环境后运行全量测试
.\venv\Scripts\pytest
```

### 测试范围说明
- **单元测试** (`tests/unit/`)：全面验证 JWT Token 解析、`ContextVars` 协程环境隔离、`RedisMemoryManager` 的 LTRIM 滑动窗口队列、单例长连接池的代理机制，以及模块化设计下的 **16** 个 MCP 工具在各种网络状态下的业务响应准确性。
- **集成测试** (`tests/integration/`)：模拟实际客户端长连接生命周期，包含 WebSocket 建连、身份认证授权、多会话并发隔离、流式文本输出以及离线连接清理。