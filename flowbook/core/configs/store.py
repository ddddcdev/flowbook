"""
ConfigStore: typed access via get_spec(SpecType, name) / put_spec(...).
Underlying storage uses string kind + name; see _get_spec_by_kind / _put_spec_by_kind.
Spec dict shape per kind: see flowbook.core.configs.spec_types.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, cast

from flowbook.core.configs.spec_types import ConfigSpecKind
from flowbook.core.configs.validation import validate_spec

TSpecKind = TypeVar("TSpecKind", bound=ConfigSpecKind)


class ConfigStore(Protocol):
    # --- internal string-based protocol methods (implementations provide these) ---

    def _get_spec_by_kind(self, kind: str, name: str) -> dict[str, Any]: ...

    def _put_spec_by_kind(
        self, kind: str, name: str, spec: dict[str, Any], *, config_id: str
    ) -> None: ...

    # --- typed public API ---

    def get_spec(self, spec_type: type[TSpecKind], name: str) -> TSpecKind.Spec:  # type: ignore[type-var]
        """Load a spec by Outer type; kind derived from spec_type.KIND."""
        return cast(Any, self._get_spec_by_kind(spec_type.KIND, name))

    def put_spec(
        self,
        spec_type: type[TSpecKind],
        name: str,
        spec: TSpecKind.Spec,  # type: ignore[type-var]
        *,
        config_id: str,
    ) -> None:
        """Store a spec by Outer type; kind derived from spec_type.KIND. Validates before write."""
        kind = spec_type.KIND
        spec_dict = cast(dict[str, Any], spec)
        validate_spec(kind, spec_dict)
        self._put_spec_by_kind(kind, name, spec_dict, config_id=config_id)
