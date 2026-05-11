"""Integration tests for session-related REST API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


# ── GET /sessions ─────────────────────────────────────────────────────────────

def test_get_sessions_requires_auth(client):
    response = client.get("/sessions")
    assert response.status_code == 401


def test_get_sessions_returns_200(client, auth_headers):
    mock_result = MagicMock()
    mock_result.data = [{"id": 1, "title": "测试会话"}]
    mock_result.count = 1

    with patch("app.api.session.get_sessions_paginated", return_value=mock_result):
        response = client.get("/sessions", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200


def test_get_sessions_returns_paginated_data(client, auth_headers):
    mock_result = MagicMock()
    mock_result.data = [{"id": 1, "title": "会话1"}, {"id": 2, "title": "会话2"}]
    mock_result.count = 5

    with patch("app.api.session.get_sessions_paginated", return_value=mock_result):
        response = client.get("/sessions?page=1&page_size=2", headers=auth_headers)

    body = response.json()
    assert body["data"]["total"] == 5
    assert body["data"]["page"] == 1
    assert body["data"]["page_size"] == 2
    assert len(body["data"]["items"]) == 2


def test_get_sessions_handles_db_error(client, auth_headers):
    with patch("app.api.session.get_sessions_paginated", side_effect=Exception("DB error")):
        response = client.get("/sessions", headers=auth_headers)

    body = response.json()
    assert body["code"] == 500


# ── POST /create_new_session ──────────────────────────────────────────────────

def test_create_session_requires_auth(client):
    response = client.post("/create_new_session", json={"content": "你好"})
    assert response.status_code == 401


def test_create_session_returns_session_id(client, auth_headers):
    mock_session_result = MagicMock()
    mock_session_result.data = [{"id": 42}]

    with patch("app.api.session.generate_title", new_callable=AsyncMock, return_value="测试标题"), \
         patch("app.api.session.create_session", return_value=mock_session_result):
        response = client.post(
            "/create_new_session",
            json={"content": "今天天气怎么样？"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["sessionId"] == 42
    assert body["data"]["title"] == "测试标题"


def test_create_session_handles_create_failure(client, auth_headers):
    mock_result = MagicMock()
    mock_result.data = []  # empty → create failed

    with patch("app.api.session.generate_title", new_callable=AsyncMock, return_value="标题"), \
         patch("app.api.session.create_session", return_value=mock_result):
        response = client.post(
            "/create_new_session",
            json={"content": "test"},
            headers=auth_headers,
        )

    body = response.json()
    assert body["code"] == 500


def test_create_session_handles_exception(client, auth_headers):
    with patch("app.api.session.generate_title", new_callable=AsyncMock, side_effect=Exception("API down")):
        response = client.post(
            "/create_new_session",
            json={"content": "test"},
            headers=auth_headers,
        )

    body = response.json()
    assert body["code"] == 500


# ── DELETE /delete-session ────────────────────────────────────────────────────

def test_delete_session_requires_auth(client):
    response = client.delete("/delete-session?session_id=1")
    assert response.status_code == 401


def test_delete_session_forbidden_for_other_user(client, auth_headers):
    with patch("app.api.session.check_session_owner", return_value=False):
        response = client.delete("/delete-session?session_id=99", headers=auth_headers)

    body = response.json()
    assert body["code"] == 403


def test_delete_session_success(client, auth_headers):
    mock_messages_result = MagicMock()
    mock_messages_result.data = [{"id": 1}]

    with patch("app.api.session.check_session_owner", return_value=True), \
         patch("app.api.session.delete_session_service", return_value=True), \
         patch("app.api.session.delete_messages", return_value=mock_messages_result):
        response = client.delete("/delete-session?session_id=1", headers=auth_headers)

    body = response.json()
    assert body["code"] == 200


def test_delete_session_handles_exception(client, auth_headers):
    with patch("app.api.session.check_session_owner", side_effect=Exception("DB error")):
        response = client.delete("/delete-session?session_id=1", headers=auth_headers)

    body = response.json()
    assert body["code"] == 500
