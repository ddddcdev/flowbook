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

from flowbook.artifacts.store import InMemoryArtifactsStore
from flowbook.registry.registry import Registry


"""
RunContext:
- Runtime container
- Holds registry, artifacts, and mutable state
Rule:
- Data lives only in artifacts
"""


@dataclass(frozen=True)
class RunContext:
    run_id: str
    store: InMemoryArtifactsStore
    registry: Registry
    meta: dict[str, Any] | None = None
