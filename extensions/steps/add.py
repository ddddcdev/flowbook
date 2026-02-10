from __future__ import annotations

from flowbook.registry.base_op import BaseOp


class AddOp(BaseOp):
    required_inputs = ("x", "y")
    optional_inputs = ()

    def __call__(self, inputs: dict, store_) -> dict:
        return {"sum": inputs["x"] + inputs["y"]}


def register(registry) -> None:
    registry.register("add", AddOp())
