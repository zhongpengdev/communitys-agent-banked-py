"""Unit tests for app/utils/JWTutils/jwt_helper.py"""

import pytest
import jwt
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from app.utils.JWTutils.jwt_helper import decode_token, get_user_id

SECRET = "test-secret-for-testing-only"
ALGORITHM = "HS512"


def _make_token(payload: dict) -> str:
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def test_decode_valid_token():
    payload = {"userId": "42", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = _make_token(payload)
    decoded = decode_token(token)
    assert decoded["userId"] == "42"


def test_decode_expired_token_raises():
    payload = {"userId": "42", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}
    token = _make_token(payload)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_decode_invalid_token_raises():
    with pytest.raises(jwt.InvalidTokenError):
        decode_token("not.a.valid.token")


def test_get_user_id_from_userId_field():
    payload = {"userId": "99", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = _make_token(payload)
    assert get_user_id(token) == "99"


def test_get_user_id_falls_back_to_sub():
    payload = {"sub": "sub-user-55", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = _make_token(payload)
    assert get_user_id(token) == "sub-user-55"


def test_get_user_id_falls_back_to_id():
    payload = {"id": "id-user-77", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = _make_token(payload)
    assert get_user_id(token) == "id-user-77"


def test_get_user_id_expired_raises():
    payload = {"userId": "1", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}
    token = _make_token(payload)
    with pytest.raises(jwt.ExpiredSignatureError):
        get_user_id(token)


def test_get_user_id_returns_string():
    payload = {"userId": 42, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = _make_token(payload)
    result = get_user_id(token)
    assert isinstance(result, str)
    assert result == "42"
