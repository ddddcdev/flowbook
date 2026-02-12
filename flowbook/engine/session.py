"""
RunSession: high-level API for a single run.

Scoping strategy (full-path):
- All artifact keys stored in the base store include {run_id}/ prefix.
- Session methods (put_input*, bind) construct or accept full keys.
- No store wrapper (RunScopedStore) — the store is always the base store.
- Config writers never see artifact keys; they only use logical names.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from flowbook.artifacts.store import JsonValue
from flowbook.registry.registry import Registry
from flowbook.runtime.build import build
from flowbook.runtime.context import RunContext
from flowbook.runtime.run import run
from flowbook.runtime.store import RunStore
from flowbook.runtime.types import RunInfo


@dataclass
class RunSession:
    run_id: str
    store: RunStore
    registry: Registry
    meta: dict[str, Any]

    _bindings: dict[str, str] = field(default_factory=dict)
    _executed: bool = False

    # ---- key helpers ----

    def _scoped_key(self, path: str) -> str:
        """Build a full artifact key scoped to this run."""
        return f"{self.run_id}/{path}"

    # ---- inputs ----

    def put_input(self, name: str, value: JsonValue) -> str:
        key = self._scoped_key(f"input/{name}")
        self.store.put(key, value)
        self._bindings[name] = key
        return key

    def put_input_bytes(self, name: str, data: bytes) -> str:
        key = self._scoped_key(f"input/{name}")
        self.store.put_bytes(key, data)
        self._bindings[name] = key
        return key

    def put_input_df(self, name: str, df: pd.DataFrame) -> str:
        key = self._scoped_key(f"input/{name}")
        self.store.put_df(key, df)
        self._bindings[name] = key
        return key

    def bind(self, name: str, artifact_key: str) -> None:
        """Register an existing full artifact key as a named binding."""
        self._bindings[name] = artifact_key

    # ---- artifacts access ----

    def get(self, key: str) -> JsonValue:
        return self.store.get(key)

    def get_dict(self, key: str) -> dict[str, Any]:
        return self.store.get_dict(key)

    def get_bytes(self, key: str) -> bytes:
        return self.store.get_bytes(key)

    def get_df(self, key: str) -> pd.DataFrame:
        return self.store.get_df(key)

    def list(self, prefix: str | None = None) -> list[str]:
        if prefix is None:
            return self.store.list(prefix=self._scoped_key(""))
        return self.store.list(prefix=prefix)

    # ---- execution ----

    def exec(self, *, pipeline_config: dict[str, Any]) -> RunInfo:
        if self._executed:
            raise RuntimeError("RunSession already executed; create a new session")
        self._executed = True

        pipeline = build(pipeline_config)
        run_ctx = RunContext(
            run_id=self.run_id,
            store=self.store,
            registry=self.registry,
            meta=self.meta,
            bindings=self._bindings,
        )
        return run(pipeline, run_ctx)

    def exec_with_plan_once(
        self, *, planner_config: dict[str, Any]
    ) -> tuple[RunInfo, RunInfo]:
        planner_info = self.exec(pipeline_config=planner_config)
        if planner_info.status != "succeeded":
            raise RuntimeError(
                f"planner run failed (run_id={self.run_id}): {planner_info.errors}"
            )

        planner_step = None
        for step in planner_info.steps:
            if step.name == "planner":
                planner_step = step
                break

        if not planner_step:
            raise RuntimeError("No step named 'planner' found in planner_config execution")

        if "plan" not in planner_step.outputs:
            raise KeyError(
                f"planner step did not produce 'plan' output. "
                f"Available outputs: {list(planner_step.outputs.keys())}"
            )

        plan_key = planner_step.outputs["plan"]
        plan_config = self.store.get_dict(plan_key)
        self._executed = False
        exec_info = self.exec(pipeline_config=plan_config)
        if exec_info.status != "succeeded":
            raise RuntimeError(
                f"plan execution failed (run_id={self.run_id}): {exec_info.errors}"
            )

        return planner_info, exec_info
