from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowbook.artifacts.scoped import RunScopedStore
from flowbook.engine.session import RunSession
from flowbook.runtime.run_id import new_run_id


@dataclass(frozen=True)
class Engine:
    store: Any
    registry: Any
    meta: dict[str, Any] | None = None

    def prepare(self, run_id: str | None = None) -> RunSession:
        rid = run_id or new_run_id()
        scoped = RunScopedStore(self.store, rid)
        return RunSession(
            run_id=rid,
            store=scoped,
            registry=self.registry,
            meta=self.meta or {},
        )
