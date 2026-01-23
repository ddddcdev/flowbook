"""
Engine policy:
- Engine orchestrates build+run only.
- Planning is expressed as steps that write control artifacts (PLAN, INSPECT_RESULT, ...).
- Engine may execute a plan after planning, but does not interpret domain semantics.
"""

from __future__ import annotations

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

    def execute(
        self,
        *,
        config: dict[str, Any],
        bindings: dict[str, str],
        run_id: str | None = None,
    ):
        rid = run_id or str(uuid.uuid4())

        pipeline = build(config)
        ctx = RunContext(
            run_id=rid,
            store=self.store,
            registry=self.registry,
            meta=self.meta or {},
            bindings=bindings,
        )
        info = run(pipeline, ctx)
        return rid, info

    def execute_with_plan_once(
        self,
        *,
        planner_config: dict[str, Any],
        bindings: dict[str, str],
        run_id: str | None = None,
    ):
        rid, info1 = self.execute(
            config=planner_config, bindings=bindings, run_id=run_id
        )

        plan_config = self.store.get(PLAN)  # planは論理名のみ
        _, info2 = self.execute(config=plan_config, bindings=bindings, run_id=rid)

        return rid, info1, info2
