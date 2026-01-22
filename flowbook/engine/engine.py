from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from flowbook.runtime.build import build
from flowbook.runtime.context import RunContext
from flowbook.runtime.inspect import inspect
from flowbook.runtime.run import run


@dataclass(frozen=True)
class Engine:
    store: Any
    registry: Any
    meta: dict[str, Any] | None = None

    def execute(
        self,
        *,
        profile_spec: dict[str, Any],
        config: dict[str, Any],
        run_id: str | None = None,
    ):
        rid = run_id or str(uuid.uuid4())

        profile = inspect(profile_spec)
        pipeline = build(profile, config)

        ctx = RunContext(
            run_id=rid,
            store=self.store,
            registry=self.registry,
            meta=self.meta or {},
        )
        info = run(pipeline, ctx)
        return rid, info
