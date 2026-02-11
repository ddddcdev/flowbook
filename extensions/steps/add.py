from __future__ import annotations

from typing import Any

from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.registry.spec import InputsBase
from flowbook.runtime.store import RunStore


class AddOp(BaseOp):
    class Inputs(InputsBase):
        X = "x"
        Y = "y"
        REQUIRED = (X, Y)
        OPTIONAL = ()

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        return {"sum": inputs[self.Inputs.X] + inputs[self.Inputs.Y]}


def register(registry: Registry) -> None:
    registry.register("add", AddOp())
