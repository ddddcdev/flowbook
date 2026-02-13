from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowbook.core.artifacts.store import ArtifactsStore
from flowbook.core.configs.null_store import NullConfigStore
from flowbook.core.configs.store import ConfigStore
from flowbook.core.engine.session import RunSession
from flowbook.core.registry.registry import Registry
from flowbook.core.runtime.default_store import DefaultRunStore
from flowbook.core.runtime.run_id import new_run_id


@dataclass(frozen=True)
class Engine:
    store: ArtifactsStore
    registry: Registry
    config_store: ConfigStore | None = None
    meta: dict[str, Any] | None = None

    def prepare(self, run_id: str | None = None) -> RunSession:
        run_id = run_id or new_run_id()
        config_store = self.config_store or NullConfigStore()
        run_store = DefaultRunStore(artifacts=self.store, configs=config_store)
        return RunSession(
            run_id=run_id,
            store=run_store,
            registry=self.registry,
            meta=self.meta or {},
        )
