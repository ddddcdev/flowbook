"""Update config step: write spec to ConfigStore via store.configs.put_spec."""

from __future__ import annotations

import uuid
from typing import Any

from flowbook.core.configs.spec_types import KIND_TO_SPEC_TYPE
from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("update_config")
class UpdateConfigOp(BaseOp):
    """Write a config spec to ConfigStore. Used by AI edit flow and plan-driven config updates."""

    class Inputs(InputsBase):
        KIND = "kind"
        NAME = "name"
        SPEC = "spec"
        CONFIG_ID = "config_id"
        REQUIRED = (KIND, NAME, SPEC)
        OPTIONAL = (CONFIG_ID,)

    class Outputs(OutputsBase):
        CONFIG_ID = "config_id"
        KIND = "kind"
        NAME = "name"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        kind = inputs[self.Inputs.KIND]
        name = inputs[self.Inputs.NAME]
        spec = inputs[self.Inputs.SPEC]
        config_id = inputs.get(self.Inputs.CONFIG_ID)

        if not isinstance(kind, str):
            raise TypeError(f"kind must be str, got {type(kind).__name__}")
        if not isinstance(name, str):
            raise TypeError(f"name must be str, got {type(name).__name__}")
        if not isinstance(spec, dict):
            raise TypeError(f"spec must be dict, got {type(spec).__name__}")

        try:
            spec_type = KIND_TO_SPEC_TYPE[kind]
        except KeyError:
            raise KeyError(
                f"unknown kind '{kind}'. Known kinds: {sorted(KIND_TO_SPEC_TYPE.keys())}"
            ) from None

        if config_id is None:
            config_id = str(uuid.uuid4())
        elif not isinstance(config_id, str):
            raise TypeError(f"config_id must be str or None, got {type(config_id).__name__}")

        store.configs.put_spec(spec_type, name, spec, config_id=config_id)

        return {
            self.Outputs.CONFIG_ID: config_id,
            self.Outputs.KIND: kind,
            self.Outputs.NAME: name,
        }


register = register_from_steps()
