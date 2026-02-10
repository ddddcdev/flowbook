from __future__ import annotations

import re
from datetime import date, datetime
from io import BytesIO
from typing import Any

import openpyxl


def _normalize_date(value: Any) -> str | None:
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


def _get_cell_value(ws, cell_ref: str) -> object | None:
    cell_obj = ws[cell_ref]
    if isinstance(cell_obj, tuple):
        if cell_obj and isinstance(cell_obj[0], tuple):
            cell_obj = cell_obj[0][0] if cell_obj[0] else None
        else:
            cell_obj = cell_obj[0] if cell_obj else None
    if cell_obj is None:
        return None
    return getattr(cell_obj, "value", None)


def inspect_excel_bytes_v2_op(inputs: dict[str, Any], store_) -> dict[str, Any]:
    input_profile_name = inputs.get("input_profile_name")
    if not input_profile_name:
        raise ValueError("input_profile_name is required")

    bytes_key = inputs.get("src_excel_bytes_key")
    if not bytes_key:
        raise ValueError("src_excel_bytes_key is required")

    filename = inputs.get("src_excel_filename")
    if not filename:
        raise ValueError("src_excel_filename is required")

    try:
        config = store_.configs.get_spec("input_profile", input_profile_name)
    except KeyError as e:
        raise ValueError(f"input_profile '{input_profile_name}' not found in configs") from e

    kind_rules = config.get("kind_rules")
    if kind_rules is None:
        raise ValueError(f"input_profile '{input_profile_name}' missing 'kind_rules' key")

    detected_kind = None
    matched_pattern = None
    for rule in kind_rules:
        pattern = rule.get("pattern")
        kind = rule.get("kind")
        if pattern and kind and re.match(pattern, filename):
            detected_kind = kind
            matched_pattern = pattern
            break

    date_rule = config.get("date_rule") or {}
    sheet_name = date_rule.get("sheet")
    cell = date_rule.get("cell")

    raw_value: Any = None
    effective_date: str | None = None

    if sheet_name and cell:
        src = store_.get_bytes(bytes_key)
        wb = openpyxl.load_workbook(BytesIO(src), data_only=True)
        try:
            ws = wb[sheet_name]
        except KeyError:
            ws = None
        if ws is not None:
            raw_value = _get_cell_value(ws, cell)
            effective_date = _normalize_date(raw_value)

    result = {
        "schema_version": "inspect_result_v2",
        "input_profile_name": input_profile_name,
        "filename": filename,
        "detected_kind": detected_kind,
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

    return {"result": result}


def register(registry) -> None:
    registry.register(
        "inspect_excel_bytes_v2",
        inspect_excel_bytes_v2_op,
        required_inputs=(
            "input_profile_name",
            "src_excel_bytes_key",
            "src_excel_filename",
        ),
    )
