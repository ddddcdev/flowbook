"""Tests for chat_completion step."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from flowbook import (
    Engine,
    InMemoryArtifactsStore,
    InMemoryConfigStore,
    Registry,
    register_steps,
)
from flowbook.extensions.steps.chat_completion import ChatCompletionOp

pytestmark = pytest.mark.e2e


def test_chat_completion_returns_response() -> None:
    """chat_completion with mocked OpenAI returns response."""
    mock_content = "Hello from AI!"

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock()]
            mock_resp.choices[0].message.content = mock_content
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_resp
            mock_openai_cls.return_value = mock_client

            artifacts_store = InMemoryArtifactsStore()
            config_store = InMemoryConfigStore()
            registry = Registry()
            register_steps(registry)
            engine = Engine(
                store=artifacts_store,
                registry=registry,
                config_store=config_store,
            )

            with engine.create_run() as run:
                info = run.exec_plan(
                    plan_config={
                        "steps": [
                            {
                                "name": "ai",
                                "op": "chat_completion",
                                "inputs": {ChatCompletionOp.Inputs.PROMPT: "Say hello"},
                            }
                        ]
                    }
                )

    assert info.status == "succeeded"
    step_info = info.steps[0]
    response_key = step_info.outputs[ChatCompletionOp.Outputs.RESPONSE]
    response = run.get(response_key)
    assert response == mock_content


def test_chat_completion_missing_api_key_raises() -> None:
    """chat_completion without OPENAI_API_KEY raises RuntimeError."""
    with patch.dict("os.environ", {}, clear=True):
        artifacts_store = InMemoryArtifactsStore()
        config_store = InMemoryConfigStore()
        registry = Registry()
        register_steps(registry)
        engine = Engine(
            store=artifacts_store,
            registry=registry,
            config_store=config_store,
        )

        with engine.create_run() as run:
            info = run.exec_plan(
                plan_config={
                    "steps": [
                        {
                            "name": "ai",
                            "op": "chat_completion",
                            "inputs": {ChatCompletionOp.Inputs.PROMPT: "Hi"},
                        }
                    ]
                }
            )

    assert info.status == "failed"
    assert "OPENAI_API_KEY" in info.errors[0]


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set; real API test skipped",
)
def test_chat_completion_real_api() -> None:
    """chat_completion with real OpenAI API (runs when OPENAI_API_KEY is set)."""
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()
    registry = Registry()
    register_steps(registry)
    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
    )

    with engine.create_run() as run:
        info = run.exec_plan(
            plan_config={
                "steps": [
                    {
                        "name": "ai",
                        "op": "chat_completion",
                        "inputs": {ChatCompletionOp.Inputs.PROMPT: "Reply with exactly: OK"},
                    }
                ]
            }
        )

    assert info.status == "succeeded"
    step_info = info.steps[0]
    response_key = step_info.outputs[ChatCompletionOp.Outputs.RESPONSE]
    response = run.get(response_key)
    assert isinstance(response, str)
    assert len(response) > 0
