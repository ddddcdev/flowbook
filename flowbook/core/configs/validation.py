"""Config spec validation: required keys per config_type. Enforced in put_spec."""

from __future__ import annotations

from typing import Any

from flowbook.core.configs.spec_types import CONFIG_TYPE_TO_SPEC_TYPE

# Required keys per config_type (from TypedDict / usage). Empty = no required keys.
_REQUIRED_KEYS: dict[str, frozenset[str]] = {
    "input_profile": frozenset({"kind_rules"}),
    "mapping": frozenset({"ops"}),
    "plan": frozenset({"plan"}),
    "lookup_table": frozenset({"artifact_key"}),
    "entity_plan_map": frozenset({"map"}),
}


def validate_spec(config_type: str, spec: dict[str, Any]) -> None:
    """Validate spec has required keys for the given config_type. Raises ValueError on failure."""
    if config_type not in CONFIG_TYPE_TO_SPEC_TYPE:
        raise ValueError(f"unknown config_type '{config_type}'")
    required = _REQUIRED_KEYS.get(config_type, frozenset())
    missing = required - set(spec.keys())
    if missing:
        raise ValueError(
            f"spec for config_type '{config_type}' missing required keys: {sorted(missing)}. "
            f"Required: {sorted(required)}"
        )
