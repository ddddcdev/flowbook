from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowbook.artifacts.scoped import RunScopedStore
from flowbook.artifacts.store import ArtifactsStore
from flowbook.configs.null_store import NullConfigStore
from flowbook.configs.store import ConfigStore
from flowbook.engine.session import RunSession
from flowbook.registry.registry import Registry
from flowbook.runtime.default_store import DefaultRunStore
from flowbook.runtime.run_id import new_run_id


@dataclass(frozen=True)
class Engine:
    store: ArtifactsStore
    registry: Registry
    config_store: ConfigStore | None = None
    meta: dict[str, Any] | None = None

    def prepare(self, run_id: str | None = None) -> RunSession:
        rid = run_id or new_run_id()
        scoped_artifacts = RunScopedStore(self.store, rid)
        cfg = self.config_store or NullConfigStore()
        run_store = DefaultRunStore(artifacts=scoped_artifacts, configs=cfg)
        return RunSession(
            run_id=rid,
            store=run_store,
            registry=self.registry,
            meta=self.meta or {},
        )
