"""Unit tests for app/utils/context.py"""

import pytest
import asyncio
from app.utils.context import set_request_token, get_request_token, request_token


def test_set_and_get_token():
    set_request_token("my-token-123")
    assert get_request_token() == "my-token-123"


def test_default_is_none():
    # Reset by setting a fresh token variable to None via context reset
    token = request_token.set(None)
    try:
        assert get_request_token() is None
    finally:
        request_token.reset(token)


def test_overwrite_token():
    set_request_token("first-token")
    set_request_token("second-token")
    assert get_request_token() == "second-token"


async def test_token_isolation_across_tasks():
    """Tokens set in one task should not leak into another."""
    results = {}

    async def task_a():
        set_request_token("token-a")
        await asyncio.sleep(0)
        results["a"] = get_request_token()

    async def task_b():
        set_request_token("token-b")
        await asyncio.sleep(0)
        results["b"] = get_request_token()

    await asyncio.gather(task_a(), task_b())

    assert results["a"] == "token-a"
    assert results["b"] == "token-b"


def test_empty_string_token():
    set_request_token("")
    assert get_request_token() == ""


def test_token_with_bearer_prefix():
    set_request_token("Bearer eyJhbGciOiJIUzUxMiJ9.test")
    assert get_request_token() == "Bearer eyJhbGciOiJIUzUxMiJ9.test"
