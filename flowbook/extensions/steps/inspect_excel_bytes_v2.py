from __future__ import annotations

import re
from datetime import date, datetime
from io import BytesIO
from typing import Any

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import Field

from flowbook.core.configs.spec_types import EntityPlanMap, InputProfile
from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


def _normalize_date(value: object) -> str | None:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return datetime.fromisoformat(s).date().strftime("%Y-%m-%d")
        except ValueError:
            try:
                return date.fromisoformat(s).strftime("%Y-%m-%d")
            except ValueError:
                pass
        if re.search(r"\d{4}-\d{2}-\d{2}", s):
            return s
        return None
    return None


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


def _get_cell_value(ws: Worksheet, cell_ref: str) -> object | None:
    cell_obj = ws[cell_ref]
    if isinstance(cell_obj, tuple):
        if cell_obj and isinstance(cell_obj[0], tuple):
            cell_obj = cell_obj[0][0] if cell_obj[0] else None
        else:
            cell_obj = cell_obj[0] if cell_obj else None
    if cell_obj is None:
        return None
    return getattr(cell_obj, "value", None)


@step("inspect_excel_bytes_v2")
class InspectExcelBytesV2Op(BaseOp):
    class Inputs(BaseInputs):
        input_profile_name: str = Field(json_schema_extra={"x-config-kind": InputProfile.KIND})
        src_excel_bytes: bytes = Field(description="Excel file bytes")
        src_excel_filename: str = Field(description="Filename for kind matching")

    class Outputs(BaseOutputs):
        result: dict[str, Any]

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)

        try:
            input_profile = store.configs.get_spec(InputProfile, inp.input_profile_name)
        except KeyError as e:
            raise ValueError(
                f"input_profile '{inp.input_profile_name}' not found in configs"
            ) from e

        kind_rules = input_profile.get("kind_rules")
        if kind_rules is None:
            raise ValueError(f"input_profile '{inp.input_profile_name}' missing 'kind_rules' key")

        profile_match_mode = input_profile.get("match_mode") or "start"

        detected_kind = None
        matched_pattern = None
        matched_rule: dict[str, Any] | None = None
        for rule in kind_rules:
            pattern = rule.get("pattern")
            kind = rule.get("kind")
            rule_mode = rule.get("match_mode") or profile_match_mode
            matcher = re.search if rule_mode == "search" else re.match
            if pattern and kind and matcher(pattern, inp.src_excel_filename):
                detected_kind = kind
                matched_pattern = pattern
                matched_rule = rule
                break

        date_rule = input_profile.get("date_rule") or {}
        sheet_name = date_rule.get("sheet")
        cell = date_rule.get("cell")

        raw_value: object | None = None
        effective_date: str | None = None

        if sheet_name and cell:
            wb = openpyxl.load_workbook(BytesIO(inp.src_excel_bytes), data_only=True)
            try:
                ws = wb[sheet_name]
            except KeyError:
                ws = None
            if ws is not None:
                raw_value = _get_cell_value(ws, cell)
                effective_date = _normalize_date(raw_value)

        if matched_rule and matched_rule.get("plan_name"):
            plan_name = matched_rule["plan_name"]
        else:
            entity_plan_map_name = input_profile.get("entity_plan_map_name")
            plan_name = _resolve_plan_name(store, detected_kind, entity_plan_map_name)

        result = {
            "schema_version": "inspect_result_v2",
            "input_profile_name": inp.input_profile_name,
            "filename": inp.src_excel_filename,
            "detected_kind": detected_kind,
            "plan_name": plan_name,
            "effective_date": effective_date,
            "evidence": {
                "matcher": "filename_regex",
                "matched_pattern": matched_pattern,
                "date": {
                    "sheet": sheet_name,
                    "cell": cell,
                    "raw_value": raw_value,
                },
            },
        }
        return self.Outputs(result=result).model_dump(mode="python")


register = register_from_steps()
