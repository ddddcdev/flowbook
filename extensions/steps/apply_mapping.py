from __future__ import annotations

from typing import Any

from flowbook.configs.spec_types import Mapping
from flowbook.mapping.apply import apply_mapping_ops
from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.registry.spec import InputsBase, OutputsBase
from flowbook.runtime.store import RunStore


class ApplyMappingOp(BaseOp):
    class Inputs(InputsBase):
        DF = "df"
        MAPPING_NAME = "mapping_name"
        REQUIRED = (DF, MAPPING_NAME)
        OPTIONAL = ()

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        df = inputs[self.Inputs.DF]
        mapping_name = inputs[self.Inputs.MAPPING_NAME]

        mapping_spec = store.configs.get_spec(Mapping, mapping_name)
        ops = mapping_spec.get("ops")
        if not isinstance(ops, list):
            raise ValueError("mapping spec must have ops: list")

        out = apply_mapping_ops(df, ops)
        return {self.Outputs.DF: out}


apply_mapping_op = ApplyMappingOp()


def register(registry: Registry) -> None:
    registry.register("apply_mapping", apply_mapping_op)
