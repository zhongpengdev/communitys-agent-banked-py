"""Integration tests for /message/get-all-messages endpoint."""

import pytest
from unittest.mock import patch, MagicMock


def test_get_messages_requires_auth(client):
    response = client.get("/message/get-all-messages?session_id=1")
    assert response.status_code == 401


def test_get_messages_forbidden_for_other_user(client, auth_headers):
    with patch("app.api.message.check_session_owner", return_value=False):
        response = client.get("/message/get-all-messages?session_id=99", headers=auth_headers)

    body = response.json()
    assert body["code"] == 403


def test_get_messages_returns_messages(client, auth_headers):
    mock_result = MagicMock()
    mock_result.data = [
        {"id": 1, "role": "user", "content": "你好"},
        {"id": 2, "role": "assistant", "content": "你好！"},
    ]

    with patch("app.api.message.check_session_owner", return_value=True), \
         patch("app.api.message.get_messages", return_value=mock_result):
        response = client.get("/message/get-all-messages?session_id=1", headers=auth_headers)

    body = response.json()
    assert body["code"] == "200"
    assert len(body["data"]) == 2
    assert body["data"][0]["role"] == "user"
    assert body["data"][1]["role"] == "assistant"


def test_get_messages_empty_session(client, auth_headers):
    mock_result = MagicMock()
    mock_result.data = []

    with patch("app.api.message.check_session_owner", return_value=True), \
         patch("app.api.message.get_messages", return_value=mock_result):
        response = client.get("/message/get-all-messages?session_id=1", headers=auth_headers)

    body = response.json()
    assert body["code"] == "200"
    assert body["data"] == []


def test_get_messages_handles_exception(client, auth_headers):
    with patch("app.api.message.check_session_owner", return_value=True), \
         patch("app.api.message.get_messages", side_effect=Exception("DB error")):
        response = client.get("/message/get-all-messages?session_id=1", headers=auth_headers)

    body = response.json()
    assert body["code"] == "500"


def test_get_messages_missing_session_id(client, auth_headers):
    response = client.get("/message/get-all-messages", headers=auth_headers)
    assert response.status_code == 422
