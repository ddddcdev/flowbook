"""Update config step: write spec to ConfigStore via store.configs.put_spec."""

from __future__ import annotations

import uuid
from typing import Any

from flowbook.core.configs.spec_types import KIND_TO_SPEC_TYPE
from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("update_config")
class UpdateConfigOp(BaseOp):
    """Write config spec to ConfigStore. Used by AI edit flow."""

    class Inputs(BaseInputs):
        kind: str
        name: str
        spec: dict[str, Any]
        config_id: str | None = None

    class Outputs(BaseOutputs):
        config_id: str
        kind: str
        name: str

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)

        try:
            spec_type = KIND_TO_SPEC_TYPE[inp.kind]
        except KeyError:
            raise KeyError(
                f"unknown kind '{inp.kind}'. Known kinds: {sorted(KIND_TO_SPEC_TYPE.keys())}"
            ) from None

        config_id = inp.config_id if inp.config_id is not None else str(uuid.uuid4())
        store.configs.put_spec(spec_type, inp.name, inp.spec, config_id=config_id)

        return self.Outputs(config_id=config_id, kind=inp.kind, name=inp.name).model_dump(
            mode="python"
        )


register = register_from_steps()
