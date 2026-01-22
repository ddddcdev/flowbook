from __future__ import annotations


def add_op(inputs: dict, store_):
    return {"sum": inputs["x"] + inputs["y"]}


def register(registry) -> None:
    registry.register("add", add_op)
