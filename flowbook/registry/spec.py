"""
PortSpec: minimal contract for op inputs (required / optional param names).
Op owns and produces its PortSpec; this module is the shared type only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortSpec:
    """Allowed input param names. Strict: no surplus. required/optional must be disjoint."""

    required: tuple[str, ...]
    optional: tuple[str, ...]

    def __post_init__(self) -> None:
        overlap = set(self.required) & set(self.optional)
        if overlap:
            raise ValueError(
                f"PortSpec: required and optional must be disjoint; overlap: {sorted(overlap)}"
            )

    def allowed_keys(self) -> frozenset[str]:
        return frozenset(self.required) | frozenset(self.optional)
