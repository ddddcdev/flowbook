from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from flowbook.configs.store import ConfigStore


@dataclass
class InMemoryConfigStore(ConfigStore):
    _specs: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)

    def _get_spec_by_kind(self, kind: str, name: str) -> dict[str, Any]:
        k = (kind, name)
        if k not in self._specs:
            raise KeyError(f"config not found: kind={kind} name={name}")
        return self._specs[k]

    def _put_spec_by_kind(
        self, kind: str, name: str, spec: dict[str, Any], *, config_id: str
    ) -> None:
        self._specs[(kind, name)] = spec
