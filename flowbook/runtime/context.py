"""
RunContext:
- Runtime container
- Holds registry, artifacts, and mutable state
Rule:
- Data lives only in artifacts
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
