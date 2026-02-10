from __future__ import annotations

from typing import Any

from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.runtime.store import RunStore


class AddOp(BaseOp):
    required_inputs = ("x", "y")
    optional_inputs = ()

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        return {"sum": inputs["x"] + inputs["y"]}


def register(registry: Registry) -> None:
    registry.register("add", AddOp())
