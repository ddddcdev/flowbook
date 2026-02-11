"""
RunContext:
- Runtime container for a single run. Holds registry, artifacts, and mutable state.
- Lifecycle: Create once per run (e.g. in API layer when starting the run); use for
  the entire run (inputs, build, execute). Do not reuse across runs.
- Rule: Data lives only in artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowbook.registry.registry import Registry
from flowbook.runtime.store import RunStore


@dataclass(frozen=True)
class RunContext:
    run_id: str
    store: RunStore
    registry: Registry
    bindings: dict[str, str]  # logical -> artifact key
    meta: dict[str, Any] | None = None
