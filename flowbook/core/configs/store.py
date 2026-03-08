"""
ConfigStore: typed access via get_spec(SpecType, name) / put_spec(...).
Storage uses config_type + config_name; see _get_spec_by_config_type, _put_spec_by_config_type.
Spec dict shape per config_type: see flowbook.core.configs.spec_types.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, cast

from flowbook.core.configs.spec_types import ConfigSpecKind
from flowbook.core.configs.validation import validate_spec

TSpecKind = TypeVar("TSpecKind", bound=ConfigSpecKind)


class ConfigStore(Protocol):
    # --- internal string-based protocol methods (implementations provide these) ---

    def _get_spec_by_config_type(self, config_type: str, config_name: str) -> dict[str, Any]: ...

    def _put_spec_by_config_type(
        self,
        config_type: str,
        config_name: str,
        spec: dict[str, Any],
        *,
        config_id: str,
        spec_text: str = "",
    ) -> None: ...

    def get_config_document(self, config_type: str, config_name: str) -> dict[str, Any]:
        """Return full config document: spec and spec_text."""
        ...

    # --- typed public API ---

    def get_spec(self, spec_type: type[TSpecKind], config_name: str) -> TSpecKind.Spec:  # type: ignore[type-var]
        """Load a spec by Outer type; config_type derived from spec_type.CONFIG_TYPE."""
        return cast(
            Any,
            self._get_spec_by_config_type(spec_type.CONFIG_TYPE, config_name),
        )

    def put_spec(
        self,
        spec_type: type[TSpecKind],
        config_name: str,
        spec: TSpecKind.Spec,  # type: ignore[type-var]
        *,
        config_id: str,
        spec_text: str = "",
    ) -> None:
        """Store a spec by Outer type; config_type from spec_type.CONFIG_TYPE. Validates."""
        config_type = spec_type.CONFIG_TYPE
        spec_dict = cast(dict[str, Any], spec)
        validate_spec(config_type, spec_dict)
        self._put_spec_by_config_type(
            config_type,
            config_name,
            spec_dict,
            config_id=config_id,
            spec_text=spec_text,
        )
