from __future__ import annotations

from flowbook.mapping.apply import apply_mapping_ops


def apply_mapping_op(inputs: dict, store_):
    in_key = inputs["in_key"]
    out_key = inputs["out_key"]
    mapping_name = inputs["mapping_name"]

    spec = store_.configs.get_spec("mapping", mapping_name)
    ops = spec.get("ops")
    if not isinstance(ops, list):
        raise ValueError("mapping spec must have ops: list")

    df = store_.get_df(in_key)
    out = apply_mapping_ops(df, ops)
    store_.put_df(out_key, out)

    return {"df": out}


def register(registry) -> None:
    registry.register(
        "apply_mapping",
        apply_mapping_op,
        required_inputs=("in_key", "out_key", "mapping_name"),
    )
