"""
RunContext:
- Runtime container for a single run. Holds registry, artifacts, and mutable state.
- Lifecycle: Create once per run (e.g. in API layer when starting the run); use for
  the entire run (inputs, build, execute). Do not reuse across runs.
- Rule: Data lives only in artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from flowbook.core.registry.registry import Registry
from flowbook.core.runtime.store import RunStore

if TYPE_CHECKING:
    from flowbook.core.artifacts.index import ArtifactIndex


@dataclass(frozen=True)
class RunContext:
    run_id: str
    entity_key: str
    store: RunStore
    registry: Registry
    bindings: dict[str, str]  # logical -> artifact key
    meta: dict[str, Any] | None = None
    index: ArtifactIndex | None = None
    run_config_json: str | None = None  # for runs table (planner config)
    entity_config_json: str | None = None  # for results table (exec config)
