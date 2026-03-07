from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field

from flowbook.core.configs.spec_types import Mapping
from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.excel.mapping.apply import apply_mapping_ops
from flowbook.extensions.steps._types import DataFrame


@step("apply_mapping")
class ApplyMappingOp(BaseOp):
    """Apply mapping config (rename, map, etc.) to DataFrame."""
    class Inputs(BaseInputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame = Field(description="DataFrame")
        mapping_name: str = Field(json_schema_extra={"x-config-kind": Mapping.KIND})

    class Outputs(BaseOutputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)
        mapping_spec = store.configs.get_spec(Mapping, inp.mapping_name)
        ops = mapping_spec.get("ops")
        if not isinstance(ops, list):
            raise ValueError("mapping spec must have ops: list")
        out = apply_mapping_ops(inp.df, ops)
        return self.Outputs(df=out).model_dump(mode="python")


apply_mapping_op = ApplyMappingOp()
register = register_from_steps()
