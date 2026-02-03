from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pandas as pd

from flowbook.artifacts.keys import PLAN
from flowbook.artifacts.store import JsonValue
from flowbook.runtime.build import build
from flowbook.runtime.context import RunContext
from flowbook.runtime.run import run
from flowbook.runtime.store import RunStore


@dataclass
class RunSession:
    run_id: str
    store: RunStore
    registry: Any
    meta: dict[str, Any]

    _bindings: dict[str, str] = field(default_factory=dict)
    _executed: bool = False  # 1 session = 1 run を強制したいなら使う

    # ---- inputs ----
    def put_input(self, name: str, value: JsonValue) -> str:
        key = f"artifact:input/{name}"
        self.store.put(key, value)
        self._bindings[name] = key
        return key

    def put_input_df(self, name: str, df: pd.DataFrame) -> str:
        key = f"artifact:input/{name}"
        self.store.put_df(key, df)
        self._bindings[name] = key
        return key

    # ---- artifacts access ----
    def get(self, key: str) -> Any:
        return self.store.get(key)

    def list(self, prefix: str | None = None) -> list[str]:
        return self.store.list(prefix=prefix)

    # ---- execution ----
    def exec(self, *, config: dict[str, Any]) -> Any:
        if self._executed:
            raise RuntimeError("RunSession already executed; create a new session")
        self._executed = True

        pipeline = build(config)
        ctx = RunContext(
            run_id=self.run_id,
            store=self.store,
            registry=self.registry,
            meta=self.meta,
            bindings=self._bindings,
        )
        return run(pipeline, ctx)

    def exec_with_plan_once(self, *, planner_config: dict[str, Any]) -> tuple[Any, Any]:
        info1 = self.exec(config=planner_config)
        if info1.status != "succeeded":
            raise RuntimeError(f"planner run failed (run_id={self.run_id}): {info1.errors}")

        plan_config_raw = self.store.get(PLAN)
        if not isinstance(plan_config_raw, dict):
            raise TypeError(f"PLAN must be a dict config: got {type(plan_config_raw).__name__}")

        plan_config = cast(dict[str, Any], plan_config_raw)
        # 2nd exec は同一session内で許可するので例外扱い（フラグ制御を分ける）
        self._executed = False
        info2 = self.exec(config=plan_config)
        if info2.status != "succeeded":
            raise RuntimeError(f"plan execution failed (run_id={self.run_id}): {info2.errors}")

        return info1, info2
