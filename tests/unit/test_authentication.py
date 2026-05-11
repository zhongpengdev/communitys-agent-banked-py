"""Unit tests for app/utils/JWTutils/authentication.py"""

import pytest
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from app.utils.JWTutils.authentication import verify_token

SECRET = "test-secret-for-testing-only"


def _make_token(payload: dict) -> str:
    return jwt.encode(payload, SECRET, algorithm="HS512")


def _valid_token():
    return _make_token({"userId": "123", "exp": datetime.now(timezone.utc) + timedelta(hours=1)})


def test_verify_token_returns_user_id():
    token = _valid_token()
    user_id = verify_token(authorization=f"Bearer {token}")
    assert user_id == "123"


def test_verify_token_strips_bearer_prefix():
    token = _valid_token()
    user_id = verify_token(authorization=f"Bearer {token}")
    assert user_id is not None


def test_verify_token_missing_header_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        verify_token(authorization=None)
    assert exc_info.value.status_code == 401
    assert "缺少" in exc_info.value.detail["message"]


def test_verify_token_expired_raises_401():
    token = _make_token({"userId": "1", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)})
    with pytest.raises(HTTPException) as exc_info:
        verify_token(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 401
    assert "过期" in exc_info.value.detail["message"]


def test_verify_token_invalid_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        verify_token(authorization="Bearer invalid.jwt.token")
    assert exc_info.value.status_code == 401
    assert "无效" in exc_info.value.detail["message"]


def test_verify_token_wrong_secret_raises_401():
    bad_token = jwt.encode(
        {"userId": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "wrong-secret",
        algorithm="HS512",
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_token(authorization=f"Bearer {bad_token}")
    assert exc_info.value.status_code == 401


def test_verify_token_empty_string_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        verify_token(authorization="")
    assert exc_info.value.status_code == 401
