"""Integration tests for /api/tools/metadata endpoint (no auth required)."""

import pytest
from fastapi.testclient import TestClient


def test_get_tools_metadata_returns_200(client):
    response = client.get("/api/tools/metadata")
    assert response.status_code == 200


def test_get_tools_metadata_structure(client):
    response = client.get("/api/tools/metadata")
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], dict)


def test_get_tools_metadata_contains_known_tools(client):
    response = client.get("/api/tools/metadata")
    data = response.json()["data"]
    assert "get_weather" in data
    assert "get_time" in data
    assert "web_search" in data
    assert "generate_image_from_text" in data


def test_get_tools_metadata_entries_have_display_name(client):
    response = client.get("/api/tools/metadata")
    data = response.json()["data"]
    for tool_name, meta in data.items():
        assert "display_name" in meta, f"{tool_name} missing display_name"
        assert len(meta["display_name"]) > 0


def test_get_tools_metadata_entries_have_icon(client):
    response = client.get("/api/tools/metadata")
    data = response.json()["data"]
    for tool_name, meta in data.items():
        assert "icon" in meta, f"{tool_name} missing icon"


def test_get_tools_metadata_entries_have_category(client):
    response = client.get("/api/tools/metadata")
    data = response.json()["data"]
    for tool_name, meta in data.items():
        assert "category" in meta, f"{tool_name} missing category"
