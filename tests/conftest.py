"""
Test configuration and shared fixtures.

IMPORTANT: env vars and sys.modules mocks must be applied at module level,
before any app code is imported.
"""

import sys
import os
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta

# ── 1. Environment variables ────────────────────────────────────────────────
os.environ["JWT_SECRET"] = "test-secret-for-testing-only"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
os.environ["ANTHROPIC_BASE_URL"] = ""
os.environ["CLAUDE_MODEL"] = "claude-sonnet-4-6"
os.environ["CLAUDE_TITLE_MODEL"] = "claude-haiku-4-5-20251001"
os.environ["Banked_URL"] = "http://test-banked:8080"
os.environ["Fronted_URL"] = "http://localhost:3000"
os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5432/test_db"
os.environ["SERP_KEY"] = "test-serp-key"
os.environ["DOMAINSDB_KEY"] = "test-domains-key"
os.environ["API_KEY"] = "test-api-key"
os.environ["QWEN_CREATE_TEXT_URL"] = "http://test-qwen/create"
os.environ["QWEN_GET_RESULT_URL"] = "http://test-qwen/result"

# ── 2. Mock SDK before any app import ──────────────────────────────
def _tool_pass_through(name, description, params=None):
    """Pass-through so original async functions are preserved."""
    def decorator(func):
        return func
    return decorator


class FakeAssistantMessage:
    def __init__(self, content=None):
        self.content = content or []


class FakeTextBlock:
    def __init__(self, text=""):
        self.text = text


class FakeToolUseBlock:
    def __init__(self, name="", input=None):
        self.name = name
        self.input = input or {}


class FakeToolResultBlock:
    def __init__(self, tool_use_id="", content=None):
        self.tool_use_id = tool_use_id
        self.content = content or []


class FakeResultMessage:
    def __init__(self):
        self.stop_reason = "end_turn"


_mock_sdk = MagicMock()
_mock_sdk.tool = _tool_pass_through
_mock_sdk.create_sdk_mcp_server = MagicMock(return_value=MagicMock(name="community_server"))
_mock_sdk.ClaudeSDKClient = MagicMock()
_mock_sdk.ClaudeAgentOptions = MagicMock()
_mock_sdk.AssistantMessage = FakeAssistantMessage
_mock_sdk.TextBlock = FakeTextBlock
_mock_sdk.ToolUseBlock = FakeToolUseBlock
_mock_sdk.ToolResultBlock = FakeToolResultBlock
_mock_sdk.ResultMessage = FakeResultMessage
sys.modules["claude_agent_sdk"] = _mock_sdk

# ── 4. Pytest fixtures ───────────────────────────────────────────────────────
import pytest
import jwt
from fastapi.testclient import TestClient


TEST_SECRET = "test-secret-for-testing-only"
TEST_USER_ID = "test-user-123"


@pytest.fixture(scope="session")
def valid_token():
    payload = {
        "userId": TEST_USER_ID,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS512")


@pytest.fixture(scope="session")
def expired_token():
    payload = {
        "userId": TEST_USER_ID,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS512")


@pytest.fixture(scope="session")
def auth_headers(valid_token):
    return {"Authorization": f"Bearer {valid_token}"}


@pytest.fixture
def client():
    from main import app
    return TestClient(app)
