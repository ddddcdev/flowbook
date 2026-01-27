"""
Dependencies:
- Create and provide RunContext, Registry, and Artifacts
Rule:
- RunContext must be created here only
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from flowbook.artifacts.store import InMemoryArtifactsStore
from flowbook.registry.registry import Registry
from flowbook.runtime.context import RunContext
from flowbook.runtime.types import Pipeline

"""
Dependencies:
- Create and provide RunContext, Registry, and Artifacts
Rule:
- RunContext must be created here only
"""


@dataclass
class AppState:
    store: InMemoryArtifactsStore
    registry: Registry
    pipelines: dict[str, Pipeline]


STATE = AppState(
    store=InMemoryArtifactsStore(),
    registry=Registry(),
    pipelines={},
)

_init_done = False


def ensure_initialized() -> None:
    global _init_done
    if _init_done:
        return
    init_state_for_demo()
    _init_done = True


def init_state_for_demo() -> None:
    # Seed artifacts for smoke test / MTG demo
    STATE.store.put("artifact:input/x", 2)
    STATE.store.put("artifact:input/y", 3)

    # Register ops
    def add_op(inputs: dict[str, Any], store: Any) -> dict[str, Any]:
        return {"sum": inputs["x"] + inputs["y"]}

    STATE.registry.register("add", add_op)


def new_pipeline_id() -> str:
    return str(uuid.uuid4())


def new_run_id() -> str:
    return str(uuid.uuid4())


def create_run_context(run_id: str | None, meta: dict[str, Any] | None) -> RunContext:
    rid = run_id or new_run_id()
    return RunContext(
        run_id=rid,
        store=STATE.store,
        registry=STATE.registry,
        bindings={},
        meta=meta or {},
    )
