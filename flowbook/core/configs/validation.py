"""Config spec validation: required keys per kind. Enforced in put_spec."""

from __future__ import annotations

from typing import Any

from flowbook.core.configs.spec_types import KIND_TO_SPEC_TYPE

# Required keys per kind (from TypedDict / usage). Empty = no required keys.
_REQUIRED_KEYS: dict[str, frozenset[str]] = {
    "input_profile": frozenset({"kind_rules"}),
    "mapping": frozenset({"ops"}),
    "plan": frozenset({"plan"}),
    "lookup_table": frozenset({"artifact_key"}),
    "entity_plan_map": frozenset({"map"}),
}


def validate_spec(kind: str, spec: dict[str, Any]) -> None:
    """Validate spec has required keys for the given kind. Raises ValueError on failure."""
    if kind not in KIND_TO_SPEC_TYPE:
        raise ValueError(f"unknown kind '{kind}'")
    required = _REQUIRED_KEYS.get(kind, frozenset())
    missing = required - set(spec.keys())
    if missing:
        raise ValueError(
            f"spec for kind '{kind}' missing required keys: {sorted(missing)}. "
            f"Required: {sorted(required)}"
        )
