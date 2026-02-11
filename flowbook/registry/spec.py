"""
Input contract for ops. Each op defines an inner class Inputs(InputsBase) with
key constants and REQUIRED/OPTIONAL. Run uses op.Inputs for preflight.
Future: key constants may use StrEnum for typing/IDE; REQUIRED/OPTIONAL would
reference enum members and .value for string keys.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class InputSpec(Protocol):
    """Protocol for op input contract. Implemented by op.Inputs (InputsBase subclasses)."""

    REQUIRED: tuple[str, ...]
    OPTIONAL: tuple[str, ...]

    def allowed_keys(self) -> frozenset[str]: ...


class InputsBase:
    """
    Base for op input declaration. Subclass as op.Inputs with key constants
    and REQUIRED/OPTIONAL (disjoint validated).
    """

    REQUIRED: tuple[str, ...] = ()
    OPTIONAL: tuple[str, ...] = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        req = cls.REQUIRED
        opt = cls.OPTIONAL
        overlap = set(req) & set(opt)
        if overlap:
            raise ValueError(
                f"Inputs REQUIRED and OPTIONAL must be disjoint; overlap: {sorted(overlap)}"
            )

    @classmethod
    def allowed_keys(cls) -> frozenset[str]:
        return frozenset(cls.REQUIRED) | frozenset(cls.OPTIONAL)
