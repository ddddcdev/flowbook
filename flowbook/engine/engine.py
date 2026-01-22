from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from typing import Any

from flowbook.artifacts.keys import PLAN
from flowbook.runtime.build import build
from flowbook.runtime.context import RunContext
from flowbook.runtime.run import run


@dataclass(frozen=True)
class Engine:
    store: Any
    registry: Any
    meta: dict[str, Any] | None = None
    profile: Any | None = None  # 追加（DI）

    def execute(
        self,
        *,
        config: dict[str, Any],
        run_id: str | None = None,
    ):
        rid = run_id or str(uuid.uuid4())

        pipeline = build(config)

        ctx = RunContext(
            run_id=rid,
            store=self.store,
            registry=self.registry,
            meta=self.meta or {},
        )
        info = run(pipeline, ctx)
        return rid, info

    def execute_with_plan_once(
        self, *, planner_config: dict, run_id: str | None = None
    ):
        rid, info1 = self.execute(config=planner_config, run_id=run_id)

        plan_config = self.store.get(PLAN)

        # plannerに渡したのと同じ input bindings を抽出（artifact参照）
        planner_steps = planner_config.get("steps", [])
        if not planner_steps:
            raise ValueError("planner_config.steps is empty")
        bindings = dict(planner_steps[0].get("inputs", {}))

        # planへ注入（inputs未指定のstepのみ）
        exec_config = copy.deepcopy(plan_config)
        for s in exec_config.get("steps", []):
            if "inputs" not in s or s["inputs"] is None:
                s["inputs"] = bindings

        _, info2 = self.execute(config=exec_config, run_id=rid)
        return rid, info1, info2
