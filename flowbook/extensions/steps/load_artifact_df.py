"""
Load an artifact by key and expose it as a DataFrame output.

Used by export plans to run map+write on an existing import (read/df) without
passing a DataFrame into session.put_input (which may not support non-primitive types).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import ConfigDict

from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.steps._types import DataFrame


@step("load_artifact_df")
class LoadArtifactDfOp(BaseOp):
    """Load DataFrame from artifact store by key. Used by export plans."""

    class Inputs(BaseInputs):
        artifact_key: str

    class Outputs(BaseOutputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)
        val = store.get_any(inp.artifact_key)
        if not isinstance(val, pd.DataFrame):
            raise ValueError(f"Artifact {inp.artifact_key!r} is not a DataFrame")
        return self.Outputs(df=val).model_dump(mode="python")


register = register_from_steps()
