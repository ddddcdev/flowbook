from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from flowbook.core.configs.spec_types import EntityPlanMap, InputProfile
from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("inspect")
class InspectOp(BaseOp):
    """Contract-first stub: fixed control keys, no file I/O yet."""

    class Inputs(InputsBase):
        SOURCE_URI = "source_uri"
        READ_SPEC = "read_spec"
        REQUIRED = (SOURCE_URI,)
        OPTIONAL = (READ_SPEC,)

    class Outputs(OutputsBase):
        INSPECT_RESULT = "inspect_result"
        READ_SPEC = "read_spec"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        source_uri = inputs.get(self.Inputs.SOURCE_URI)
        read_spec = inputs.get(self.Inputs.READ_SPEC) or {}
        result = {
            "source_uri": source_uri,
            "warnings": [],
            "suggested_read_spec": read_spec,
            "columns": [],
        }
        return {
            self.Outputs.INSPECT_RESULT: result,
            self.Outputs.READ_SPEC: result["suggested_read_spec"],
        }


@step("inspect_filename_kind")
class InspectFilenameKindOp(BaseOp):
    """Identifies input kind from filename pattern only."""

    class Inputs(InputsBase):
        INPUT_PROFILE_NAME = "input_profile_name"
        PATH = "path"
        REQUIRED = (INPUT_PROFILE_NAME, PATH)
        OPTIONAL = ()

    class Outputs(OutputsBase):
        RESULT = "result"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        input_profile_name = inputs[self.Inputs.INPUT_PROFILE_NAME]
        path_str = inputs[self.Inputs.PATH]

        config = store.configs.get_spec(InputProfile, input_profile_name)
        kind_rules = config.get("kind_rules")
        if kind_rules is None:
            raise ValueError(f"input_profile '{input_profile_name}' missing 'kind_rules' key")

        profile_match_mode = config.get("match_mode") or "start"

        path = Path(path_str)
        filename = path.name
        detected_kind = None
        matched_pattern = None
        for rule in kind_rules:
            pattern = rule.get("pattern")
            kind = rule.get("kind")
            rule_mode = rule.get("match_mode") or profile_match_mode
            matcher = re.search if rule_mode == "search" else re.match
            if pattern and kind and matcher(pattern, filename):
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
        return {self.Outputs.RESULT: result}


def _resolve_plan_name(
    store: RunStore,
    detected_kind: str | None,
    entity_plan_map_name: str | None = None,
) -> str | None:
    """Resolve plan_name from EntityPlanMap config. Uses entity_plan_map_name or 'default'."""
    map_name = entity_plan_map_name or "default"
    try:
        epm = store.configs.get_spec(EntityPlanMap, map_name)
    except KeyError:
        return None
    kind_map = epm.get("map") or {}
    if detected_kind and detected_kind in kind_map:
        return kind_map[detected_kind]
    return epm.get("default")


@step("inspect_filename")
class InspectFilenameOp(BaseOp):
    """Identifies input kind from filename only. Returns plan_name from EntityPlanMap."""

    class Inputs(InputsBase):
        INPUT_PROFILE_NAME = "input_profile_name"
        FILENAME = "filename"
        REQUIRED = (INPUT_PROFILE_NAME, FILENAME)
        OPTIONAL = ()

    class Outputs(OutputsBase):
        RESULT = "result"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        input_profile_name = inputs[self.Inputs.INPUT_PROFILE_NAME]
        filename = inputs[self.Inputs.FILENAME]

        config = store.configs.get_spec(InputProfile, input_profile_name)
        kind_rules = config.get("kind_rules")
        if kind_rules is None:
            raise ValueError(f"input_profile '{input_profile_name}' missing 'kind_rules' key")

        profile_match_mode = config.get("match_mode") or "start"

        detected_kind = None
        matched_pattern = None
        matched_rule: dict[str, Any] | None = None
        for rule in kind_rules:
            pattern = rule.get("pattern")
            kind = rule.get("kind")
            rule_mode = rule.get("match_mode") or profile_match_mode
            matcher = re.search if rule_mode == "search" else re.match
            if pattern and kind and matcher(pattern, filename):
                detected_kind = kind
                matched_pattern = pattern
                matched_rule = rule
                break

        if matched_rule and matched_rule.get("plan_name"):
            plan_name = matched_rule["plan_name"]
        else:
            entity_plan_map_name = config.get("entity_plan_map_name")
            plan_name = _resolve_plan_name(store, detected_kind, entity_plan_map_name)

        result = {
            "schema_version": "inspect_filename_v1",
            "input_profile_name": input_profile_name,
            "filename": filename,
            "detected_kind": detected_kind,
            "plan_name": plan_name,
            "effective_date": None,
            "evidence": {
                "matched_pattern": matched_pattern,
                "matcher": "filename_regex",
            },
        }
        return {self.Outputs.RESULT: result}


register = register_from_steps()
