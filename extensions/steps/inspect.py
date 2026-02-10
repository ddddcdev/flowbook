from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.runtime.store import RunStore

KEY_SOURCE_URI = "source_uri"
KEY_READ_SPEC = "read_spec"


class InspectOp(BaseOp):
    """Contract-first stub: fixed control keys, no file I/O yet."""

    required_inputs = (KEY_SOURCE_URI,)
    optional_inputs = (KEY_READ_SPEC,)

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        source_uri = inputs.get(KEY_SOURCE_URI)
        read_spec = inputs.get(KEY_READ_SPEC) or {}
        result = {
            "source_uri": source_uri,
            "warnings": [],
            "suggested_read_spec": read_spec,
            "columns": [],
        }
        return {
            "inspect_result": result,
            "read_spec": result["suggested_read_spec"],
        }


KEY_INPUT_PROFILE_NAME = "input_profile_name"
KEY_PATH = "path"


class InspectFilenameKindOp(BaseOp):
    """Identifies input kind from filename pattern only."""

    required_inputs = (KEY_INPUT_PROFILE_NAME, KEY_PATH)
    optional_inputs = ()

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        input_profile_name = inputs[KEY_INPUT_PROFILE_NAME]
        path_str = inputs[KEY_PATH]

        config = store.configs.get_spec("input_profile", input_profile_name)
        kind_rules = config.get("kind_rules")
        if kind_rules is None:
            raise ValueError(f"input_profile '{input_profile_name}' missing 'kind_rules' key")

        path = Path(path_str)
        filename = path.name
        detected_kind = None
        matched_pattern = None
        for rule in kind_rules:
            pattern = rule.get("pattern")
            kind = rule.get("kind")
            if pattern and kind and re.match(pattern, filename):
                detected_kind = kind
                matched_pattern = pattern
                break

        result = {
            "schema_version": "inspect_result_v1",
            "input_profile_name": input_profile_name,
            "resolved_path": path_str,
            "filename": filename,
            "detected_kind": detected_kind,
            "evidence": {
                "matched_pattern": matched_pattern,
                "matcher": "filename_regex",
            },
        }
        return {"result": result}


def register(registry: Registry) -> None:
    registry.register("inspect", InspectOp())
    registry.register("inspect_filename_kind", InspectFilenameKindOp())
