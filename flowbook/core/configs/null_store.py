from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowbook.core.configs.store import ConfigStore


@dataclass
class NullConfigStore(ConfigStore):
    def _get_spec_by_config_type(self, config_type: str, config_name: str) -> dict[str, Any]:
        raise RuntimeError(
            f"ConfigStore is not configured "
            f"(requested config_type={config_type} config_name={config_name})"
        )

    def get_config_document(self, config_type: str, config_name: str) -> dict[str, Any]:
        raise RuntimeError(
            f"ConfigStore is not configured "
            f"(requested config_type={config_type} config_name={config_name})"
        )

    def _put_spec_by_config_type(
        self,
        config_type: str,
        config_name: str,
        spec: dict[str, Any],
        *,
        config_id: str,
        spec_text: str = "",
    ) -> None:
        raise RuntimeError("ConfigStore is not configured (put_spec called)")
