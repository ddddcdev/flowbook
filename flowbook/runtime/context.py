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

from flowbook.artifacts.store import ArtifactsStore
from flowbook.registry.registry import Registry


@dataclass(frozen=True)
class RunContext:
    run_id: str
    store: ArtifactsStore
    registry: Registry
    bindings: dict[str, str]  # logical -> artifact key
    meta: dict[str, Any] | None = None
