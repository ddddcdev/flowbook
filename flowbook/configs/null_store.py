from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowbook.configs.store import ConfigStore


@dataclass
class NullConfigStore(ConfigStore):
    def _get_spec_by_kind(self, kind: str, name: str) -> dict[str, Any]:
        raise RuntimeError(f"ConfigStore is not configured (requested kind={kind} name={name})")

    def _put_spec_by_kind(
        self, kind: str, name: str, spec: dict[str, Any], *, config_id: str
    ) -> None:
        raise RuntimeError("ConfigStore is not configured (put_spec called)")
