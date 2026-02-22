"""
RunSession: high-level API for a single run.

Scoping strategy (full-path):
- Artifact keys: {run_id}/{entity_key}/{path}. Inputs use entity_key="" (run-level).
- Session methods (put_input*, bind) construct or accept full keys.
- The store is always the base store (no wrapper).
- Config writers never see artifact keys; they only use logical names.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from flowbook.core.artifacts.key_utils import build_artifact_key
from flowbook.core.artifacts.store import JsonValue
from flowbook.core.registry.registry import Registry
from flowbook.core.runtime.build import build
from flowbook.core.runtime.context import RunContext
from flowbook.core.runtime.run import run
from flowbook.core.runtime.store import RunStore
from flowbook.core.runtime.types import RunInfo


@dataclass
class RunSession:
    run_id: str
    entity_key: str
    store: RunStore
    registry: Registry
    meta: dict[str, Any]

    _bindings: dict[str, str] = field(default_factory=dict)
    _executed: bool = False

    # ---- key helpers ----

    def _input_key(self, name: str) -> str:
        """Build artifact key for run-level input (entity_key='')."""
        return build_artifact_key(self.run_id, "", f"input/{name}")

    def _scoped_prefix(self) -> str:
        """Prefix for listing all artifacts in this run."""
        return f"{self.run_id}/"

    # ---- inputs ----

    def put_input(self, name: str, value: JsonValue) -> str:
        key = self._input_key(name)
        self.store.put(key, value)
        self._bindings[name] = key
        return key

    def put_input_bytes(self, name: str, data: bytes) -> str:
        key = self._input_key(name)
        self.store.put_bytes(key, data)
        self._bindings[name] = key
        return key

    def put_input_df(self, name: str, df: Any) -> str:
        key = self._input_key(name)
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

    def get_df(self, key: str) -> Any:
        return self.store.get_df(key)

    def list(self, prefix: str | None = None) -> list[str]:
        if prefix is None:
            return self.store.list(prefix=self._scoped_prefix())
        return self.store.list(prefix=prefix)

    # ---- execution ----

    def _exec_entity(
        self,
        pipeline_config: dict[str, Any],
        entity_key: str,
    ) -> RunInfo:
        """Execute pipeline, record config to entity_runs only. Internal."""
        if self._executed:
            raise RuntimeError("RunSession already executed; create a new session")
        self._executed = True

        entity_config_json = json.dumps(pipeline_config) if pipeline_config else None
        pipeline = build(pipeline_config)
        run_ctx = RunContext(
            run_id=self.run_id,
            entity_key=entity_key,
            store=self.store,
            registry=self.registry,
            meta=self.meta,
            bindings=self._bindings,
            run_config_json=None,
            entity_config_json=entity_config_json,
        )
        return run(pipeline, run_ctx)

    def exec(self, *, pipeline_config: dict[str, Any]) -> RunInfo:
        """Execute pipeline. Records config to runs (entry) and entity_runs (executed)."""
        self._record_run_config(pipeline_config)
        return self._exec_entity(
            pipeline_config=pipeline_config, entity_key=self.entity_key
        )

    def exec_with_plan_once(
        self, *, planner_config: dict[str, Any]
    ) -> tuple[RunInfo, RunInfo]:
        """Run planner then plan. Records planner_config to runs; each exec to entity_runs."""
        self._record_run_config(planner_config)
        planner_info = self._exec_entity(
            pipeline_config=planner_config, entity_key=self.entity_key
        )
        if planner_info.status != "succeeded":
            raise RuntimeError(f"planner run failed (run_id={self.run_id}): {planner_info.errors}")

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
        name = planner_config.get("name")
        if name and "name" not in plan_config:
            plan_config = {**plan_config, "name": name}
        self._executed = False
        exec_info = self._exec_entity(
            pipeline_config=plan_config, entity_key=self.entity_key
        )
        if exec_info.status != "succeeded":
            raise RuntimeError(f"plan execution failed (run_id={self.run_id}): {exec_info.errors}")

        return planner_info, exec_info

    def _record_run_config(self, config: dict[str, Any]) -> None:
        """Record config to runs table (planner/entry). Called by exec and exec_with_plan_once."""
        artifacts = getattr(self.store, "artifacts", self.store)
        upsert_run = getattr(artifacts, "upsert_run", None)
        if not callable(upsert_run):
            return
        config_json = json.dumps(config) if config else None
        upsert_run(self.run_id, "running", config_json=config_json)
