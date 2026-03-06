"""Tests for config CRUD API: POST, PUT, activate, deactivate."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from flowbook.extensions.api.app import app
from flowbook.extensions.api.deps import get_engine

pytestmark = pytest.mark.smoke


@pytest.fixture(autouse=True)
def _reset_engine():
    get_engine.cache_clear()
    yield
    get_engine.cache_clear()


@pytest.fixture
def client_in_memory(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Force InMemoryConfigStore (no DB)."""
    monkeypatch.delenv("FLOWBOOK_DATABASE_URL", raising=False)
    get_engine.cache_clear()
    return TestClient(app)


def test_post_configs_create(client_in_memory: TestClient) -> None:
    """POST /configs creates config; GET returns it."""
    resp = client_in_memory.post(
        "/configs",
        json={
            "kind": "plan",
            "name": "test_plan",
            "spec": {"plan": {"steps": []}},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["kind"] == "plan"
    assert data["name"] == "test_plan"
    assert data["spec"]["plan"]["steps"] == []

    get_resp = client_in_memory.get("/configs/plan/test_plan")
    assert get_resp.status_code == 200
    assert get_resp.json()["spec"]["plan"]["steps"] == []


def test_put_configs_upsert(client_in_memory: TestClient) -> None:
    """PUT /configs/{kind}/{name} creates or updates."""
    # Create via PUT
    resp = client_in_memory.put(
        "/configs/plan/upsert_plan",
        json={"spec": {"plan": {"steps": [{"name": "a", "op": "add", "inputs": {}}]}}},
    )
    assert resp.status_code == 200
    assert len(resp.json()["spec"]["plan"]["steps"]) == 1

    # Update via PUT
    resp2 = client_in_memory.put(
        "/configs/plan/upsert_plan",
        json={"spec": {"plan": {"steps": []}}},
    )
    assert resp2.status_code == 200
    assert resp2.json()["spec"]["plan"]["steps"] == []


def test_post_configs_invalid_spec_returns_400(client_in_memory: TestClient) -> None:
    """POST /configs with missing required keys returns 400."""
    resp = client_in_memory.post(
        "/configs",
        json={"kind": "plan", "name": "bad", "spec": {}},
    )
    assert resp.status_code == 400
    assert "missing" in resp.json()["detail"]["reason"].lower()


def test_post_configs_unknown_kind_returns_400(client_in_memory: TestClient) -> None:
    """POST /configs with unknown kind returns 400."""
    resp = client_in_memory.post(
        "/configs",
        json={"kind": "unknown", "name": "x", "spec": {}},
    )
    assert resp.status_code == 400


def test_chat_returns_response(client_in_memory: TestClient) -> None:
    """POST /chat/ returns response from chat_completion."""
    import os
    from unittest.mock import MagicMock, patch

    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        with patch("openai.OpenAI") as mock_cls:
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock()]
            mock_resp.choices[0].message.content = "Hello back!"
            mock_cls.return_value.chat.completions.create.return_value = mock_resp

            resp = client_in_memory.post(
                "/chat/",
                json={
                    "prompt": "Say hello",
                    "messages": [
                        {"role": "user", "content": "hi"},
                        {"role": "assistant", "content": "Hi there!"},
                    ],
                },
            )

    assert resp.status_code == 200
    assert resp.json()["response"] == "Hello back!"


def test_activate_deactivate_in_memory_returns_501(client_in_memory: TestClient) -> None:
    """activate/deactivate with InMemory returns 501."""
    client_in_memory.post(
        "/configs",
        json={"kind": "plan", "name": "p", "spec": {"plan": {"steps": []}}},
    )
    resp_a = client_in_memory.post("/configs/plan/p/activate")
    assert resp_a.status_code == 501
    resp_d = client_in_memory.post("/configs/plan/p/deactivate")
    assert resp_d.status_code == 501
