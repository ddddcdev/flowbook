"""
Input/output contracts for ops. Inputs(InputsBase): key constants + REQUIRED/OPTIONAL.
Outputs(OutputsBase): key constants + KEYS (returned keys). Run uses op.Inputs for
preflight and op.Outputs for postflight when non-empty.
Future: key constants may use StrEnum for typing/IDE.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class InputSpec(Protocol):
    """Protocol for op input contract. Implemented by op.Inputs (InputsBase subclasses)."""

    REQUIRED: tuple[str, ...]
    OPTIONAL: tuple[str, ...]

    def allowed_keys(self) -> frozenset[str]: ...


@runtime_checkable
class OutputSpec(Protocol):
    """Protocol for op output contract. Implemented by op.Outputs (OutputsBase subclasses)."""

    KEYS: tuple[str, ...]

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


class OutputsBase:
    """
    Base for op output declaration. Subclass as op.Outputs with key constants only
    (e.g. RESULT = "result"). KEYS is derived from all uppercase str attributes.
    When non-empty, run validates return dict keys.
    """

    KEYS: tuple[str, ...] = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        keys = tuple(
            sorted(
                v
                for k, v in cls.__dict__.items()
                if k != "KEYS" and k.isupper() and isinstance(v, str)
            )
        )
        cls.KEYS = keys

    @classmethod
    def allowed_keys(cls) -> frozenset[str]:
        return frozenset(cls.KEYS)
