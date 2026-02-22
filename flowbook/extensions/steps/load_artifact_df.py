"""
Load an artifact by key and expose it as a DataFrame output.

Used by export plans to run map+write on an existing import (read/df) without
passing a DataFrame into session.put_input (which may not support non-primitive types).
"""

from __future__ import annotations

from typing import Any

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("load_artifact_df")
class LoadArtifactDfOp(BaseOp):
    """
    Load an artifact by key from the store and return it as df.
    The artifact must be a DataFrame (e.g. run_id/read/df from an import).
    """

    class Inputs(InputsBase):
        ARTIFACT_KEY = "artifact_key"
        REQUIRED = (ARTIFACT_KEY,)
        OPTIONAL = ()

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        key = inputs[self.Inputs.ARTIFACT_KEY]
        if not key or not isinstance(key, str):
            raise ValueError("artifact_key must be a non-empty string")
        val = store.get_any(key)
        if type(val).__name__ != "DataFrame":
            raise ValueError(f"Artifact {key!r} is not a DataFrame")
        return {self.Outputs.DF: val}


register = register_from_steps()
