from __future__ import annotations

from typing import Any

from flowbook.mapping.apply import apply_mapping_ops
from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.registry.spec import InputsBase
from flowbook.runtime.store import RunStore


class ApplyMappingOp(BaseOp):
    class Inputs(InputsBase):
        IN_KEY = "in_key"
        OUT_KEY = "out_key"
        MAPPING_NAME = "mapping_name"
        REQUIRED = (IN_KEY, OUT_KEY, MAPPING_NAME)
        OPTIONAL = ()

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        in_key = inputs[self.Inputs.IN_KEY]
        out_key = inputs[self.Inputs.OUT_KEY]
        mapping_name = inputs[self.Inputs.MAPPING_NAME]

        mapping_spec = store.configs.get_spec("mapping", mapping_name)
        ops = mapping_spec.get("ops")
        if not isinstance(ops, list):
            raise ValueError("mapping spec must have ops: list")

        df = store.get_df(in_key)
        out = apply_mapping_ops(df, ops)
        store.put_df(out_key, out)
        return {"df": out}


apply_mapping_op = ApplyMappingOp()


def register(registry: Registry) -> None:
    registry.register("apply_mapping", apply_mapping_op)
