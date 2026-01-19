"""
Artifacts:
- Single source of truth for data products and intermediates
- Minimal contract: save / load / list
Rule:
- Never put real data into run_info
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ArtifactNotFound(KeyError):
    """Raised when an artifact key does not exist in store."""


@dataclass
class InMemoryArtifactsStore:
    """
    Artifacts (in-memory):
    - Single source of truth for data products and intermediates
    - Minimal contract: save / load / list
    Rule:
    - Never put real data into run_info
    """
    _data: dict[str, Any] = field(default_factory=dict)

    def put(self, key: str, value: Any) -> str:
        self._data[key] = value
        return key

    def get(self, key: str) -> Any:
        if key not in self._data:
            raise ArtifactNotFound(key)
        return self._data[key]

    def list(self, prefix: str | None = None) -> list[str]:
        keys = sorted(self._data.keys())
        if prefix is None:
            return keys
        return [k for k in keys if k.startswith(prefix)]
