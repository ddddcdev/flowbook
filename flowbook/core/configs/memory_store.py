from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from flowbook.core.configs.store import ConfigStore


@dataclass
class InMemoryConfigStore(ConfigStore):
    _specs: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    _spec_texts: dict[tuple[str, str], str] = field(default_factory=dict)

    def _get_spec_by_config_type(self, config_type: str, config_name: str) -> dict[str, Any]:
        k = (config_type, config_name)
        if k not in self._specs:
            raise KeyError(f"config not found: config_type={config_type} config_name={config_name}")
        return self._specs[k]

    def get_config_document(self, config_type: str, config_name: str) -> dict[str, Any]:
        k = (config_type, config_name)
        if k not in self._specs:
            raise KeyError(f"config not found: config_type={config_type} config_name={config_name}")
        return {
            "spec": self._specs[k],
            "spec_text": self._spec_texts.get(k, ""),
        }

    def _put_spec_by_config_type(
        self,
        config_type: str,
        config_name: str,
        spec: dict[str, Any],
        *,
        config_id: str,
        spec_text: str = "",
    ) -> None:
        k = (config_type, config_name)
        self._specs[k] = spec
        self._spec_texts[k] = spec_text or ""
