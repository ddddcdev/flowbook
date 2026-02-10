from __future__ import annotations

from typing import Any

from flowbook.mapping.apply import apply_mapping_ops
from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.runtime.store import RunStore

KEY_IN_KEY = "in_key"
KEY_OUT_KEY = "out_key"
KEY_MAPPING_NAME = "mapping_name"


class ApplyMappingOp(BaseOp):
    required_inputs = (KEY_IN_KEY, KEY_OUT_KEY, KEY_MAPPING_NAME)
    optional_inputs = ()

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        in_key = inputs[KEY_IN_KEY]
        out_key = inputs[KEY_OUT_KEY]
        mapping_name = inputs[KEY_MAPPING_NAME]

        mapping_spec = store.configs.get_spec("mapping", mapping_name)
        ops = mapping_spec.get("ops")
        if not isinstance(ops, list):
            raise ValueError("mapping spec must have ops: list")

        df = store.get_df(in_key)
        out = apply_mapping_ops(df, ops)
        store.put_df(out_key, out)
        return {"df": out}


# Singleton instance: backward compat for direct call, and for registry
apply_mapping_op = ApplyMappingOp()


def register(registry: Registry) -> None:
    registry.register("apply_mapping", apply_mapping_op)
