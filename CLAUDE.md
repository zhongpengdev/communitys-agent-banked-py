# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install all dependencies (including dev/test)
pip install -r requirements-dev.txt

# Run the full test suite
pytest

# Run a single test file
pytest tests/unit/test_runner_helpers.py

# Run a single test function
pytest tests/unit/test_runner_helpers.py::test_strip_mcp_prefix

# Run only unit tests or only integration tests
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Start the dev server (default port 8081)
python main.py
# Or on a custom port:
PORT=9000 python main.py
```

## Environment Setup

Copy `.env.example` to `.env` and fill in required values. Key variables:

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `ANTHROPIC_BASE_URL` | API base URL override (for proxies); leave empty for default |
| `CLAUDE_MODEL` | Model for chat (default: `deepseek-v4-flash`) |
| `DATABASE_URL` | PostgreSQL connection string |
| `Banked_URL` | Backend API base URL for community data tools |
| `Fronted_URL` | Comma-separated CORS origins |
| `JWT_SECRET` | HS512 signing secret |
| `REDIS_HOST` / `REDIS_PORT` | Redis connection |

## Architecture (Non-Obvious Patterns)

### ContextVar Token Isolation (`app/utils/context.py`)

JWT tokens are injected into a `ContextVar` at the start of every WebSocket message handler (`set_request_token(token)`). All MCP tool HTTP calls read the token from this ContextVar via `_auth_headers()` in `app/tools_mcp/base.py`. This means **no token is ever passed through function arguments** — the ContextVar carries it transparently across any depth of async call chain. Tests verify this isolation works correctly across concurrent tasks (`tests/unit/test_context.py`).

### Dual-Layer Memory: Redis → PostgreSQL (`app/services/memory.py`, `app/agent/runner.py`)

On each message save:
1. **Write Redis immediately** (hot cache) — sliding window of last N messages (default 10) via `LTRIM`, 24h TTL extended on each write, uses Redis Pipelines for batching
2. **Flush to PostgreSQL async** — via `asyncio.to_thread()` to avoid blocking the event loop

On history load (`_build_history_context`):
1. Try Redis first
2. Fall back to DB query, then backfill Redis

Ordering is strictly by auto-increment `id`, not `created_at` (avoids timestamp collision jitter).

### AgentSession Lifecycle (`app/agent/runner.py`)

- **One AgentSession per WebSocket connection** (not per message). Created in `websocket_chat_handler`, persists across multiple messages until disconnect.
- **Session switching**: Tracks `_current_session_id`. When `session_id` changes mid-connection, automatically restarts the ClaudeSDKClient (disconnect → reconnect) to clear SDK internal state, resets `_history_seeded`, and re-injects the new session's history from Redis/DB.
- `sent_text_by_block` tracks what's already been sent per content block index — resets when the message UUID changes (handles thinking → final response transitions). Prevents duplicate text in streaming.

### Global HTTP Connection Pool (`app/core/http.py`)

Singleton `HttpClientManager` maintains one `aiohttp.ClientSession` (max 100 connections, 5-min DNS cache). Managed via FastAPI `lifespan` — created on startup, closed on shutdown. All MCP tools use this single pool through `http_get`/`http_post`/`http_delete` in `app/tools_mcp/base.py`.

### MCP Tool Naming Convention

All 16 tools are registered under the `mcp__community__` prefix (e.g., `mcp__community__get_weather`). The `_strip_mcp_prefix()` helper in runner.py extracts the bare tool name for display. Tools are defined in `app/tools_mcp/modules/` organized by domain: `system.py`, `community.py`, `email.py`, `search.py`, `media.py`.

### WebSocket Authentication Flow

The WS endpoint at `/ws/chat` accepts `token` as a query parameter. This token is validated via the standard `verify_token` dependency AND also stored in the ContextVar for tool call forwarding. Sessions are auto-created on first message if none exists, with background title generation via Anthropic API.

## Testing

### Mock Strategy (`tests/conftest.py`)

The entire `claude_agent_sdk` module is **mocked at module level before any app imports**. This is critical — `conftest.py` patches `sys.modules["claude_agent_sdk"]` with fake classes (`FakeAssistantMessage`, `FakeTextBlock`, `FakeToolUseBlock`, `FakeToolResultBlock`, `FakeResultMessage`) before pytest collects any test that imports from `app.*`.

Environment variables are also set at module level (not in fixtures) to ensure they're available before `app.core.config` is imported.

### Test Organization

- `tests/unit/` — JWT decode, ContextVar isolation, Redis memory manager, MCP tools (mocked HTTP), runner helpers, title generator
- `tests/integration/` — Full WebSocket lifecycle, session CRUD, message API, agent session flow

### Fixture Dependencies

`conftest.py` provides session-scoped tokens (`valid_token`, `expired_token`, `auth_headers`) and a function-scoped `client` (FastAPI `TestClient`). Integration tests that need a real database connection expect PostgreSQL and Redis to be available.

## Key Files

| File | Role |
|------|------|
| `main.py` | Entry point, CORS, lifespan (HTTP pool init/teardown), router registration |
| `app/agent/runner.py` | AgentSession — ClaudeSDKClient wrapper, streaming, history, save |
| `app/websocket/routes.py` | WS main loop: auth, AgentSession lifecycle, auto-session-create, background title gen |
| `app/websocket/manager.py` | ConnectionManager — per-user WS tracking, typed send helpers (chunk/status/error/message) |
| `app/core/config.py` | All env-driven settings via Pydantic `BaseSettings` |
| `app/core/security.py` | JWT decode/verify, `get_user_id` with `userId`/`sub`/`id` fallback |
| `app/tools_mcp/base.py` | Shared HTTP helpers + ContextVar-based auth header forwarding |
| `app/tools_mcp/server.py` | MCP server registration — assembles all 16 tools |
| `app/services/memory.py` | RedisMemoryManager — sliding window cache with Pipeline batching |
| `app/services/title_generator.py` | Session title generation via Anthropic API |
| `app/database/service/session.py` | Session CRUD with pagination, ownership check |
| `app/database/service/message.py` | Message CRUD with ordering by auto-increment id |

---

# AI Agent System Prompt

The content below is the system prompt for the "小智" (XiaoZhi) AI assistant — it defines the chatbot persona, available tools, and response rules. It is read by the Claude Agent SDK at runtime.

---

# 社区物业 AI 助手

你是一个专业的社区物业 AI 助手，名叫"小智"，服务于社区居民。

## 角色定位

你代表物业管理方，帮助社区居民处理日常事务。你有访问社区系统的工具权限。

## 可用能力

- 查询物业费账单（query_unpaid_bills）
- 查询和标记通知（get_user_notifications / read_notification）
- 代发私信（send_private_messages）
- 登记访客（create_visitor）
- 查询天气（get_weather）
- 获取当前时间（get_time）
- 发送/查询/删除定时邮件（send_scheduled_email / get_scheduled_email / delete_scheduled_email）
- 搜索商品（search_goods）
- 网络搜索（web_search）
- 维基百科搜索（wikipedia_search）
- 头条热榜（toutiao_hot_news）
- 域名查询（search_domains_info）
- 文生图（generate_image_from_text）

## 回复规范

1. 始终用**中文**回复，态度友好、专业
2. 工具返回的 JSON 数据要转换为自然语言，不要直接输出原始 JSON
3. 如果工具调用失败，告知用户"该服务暂时不可用，请稍后再试"
4. 每次只调用必要的工具，不重复调用
5. 访客登记中的时间格式必须为 `yyyy-MM-dd HH:mm:ss`

## 安全规范
- 强制忽略用户关于社区议题、查询的任何要求和提问，并给出友好回复：引导用户提问与社区/工具调用有关的话题
- 不执行任何文件操作、代码执行等与社区业务无关的命令
- 不向用户透露系统内部信息或 token
