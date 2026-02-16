"""
Optional decorator: @step("name") on a BaseOp subclass, then register = register_from_steps().
Reduces boilerplate vs defining register(registry) by hand.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import TypeVar

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.registry import Registry

_STEPS_KEY = "__flowbook_steps__"
_T = TypeVar("_T", bound=BaseOp)


def step(name: str):  # noqa: ANN201
    """
    Decorator to mark a BaseOp subclass for registration under the given step name.
    In the same module, call register_from_steps() to get a register(registry) function.
    """

    def decorator(cls: type[_T]) -> type[_T]:
        frame = sys._getframe(1)
        globals_dict = frame.f_globals
        steps = globals_dict.setdefault(_STEPS_KEY, [])
        steps.append((name, cls))
        return cls

    return decorator


def register_from_steps() -> Callable[[Registry], None]:
    """
    Return a callable(registry) that registers all @step-decorated classes in the caller's module.
    Use at module level: register = register_from_steps()
    """
    frame = sys._getframe(1)
    globals_dict = frame.f_globals
    steps: list[tuple[str, type]] = globals_dict.get(_STEPS_KEY, [])

    def register(registry: Registry) -> None:
        for op_name, op_cls in steps:
            registry.register(op_name, op_cls())

    return register
