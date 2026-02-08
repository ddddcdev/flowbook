from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from flowbook.artifacts.keys import INSPECT_RESULT, READ_SPEC


def inspect_op(inputs: dict, store_):
    """
    Policy:
    - inspect = facts extraction (observation), not planning.
    - Output is control artifacts with stable schema; keep it usable across runs.
    - No file I/O yet; contract-first stub. Later: read/scan/fingerprint/schema inference.
    - Writes to fixed control keys to stabilize downstream integration early.
      (May evolve to keyed-by-source when multi-source is introduced.)
    """

    # inputs: {"source_uri": "...", "read_spec": {...}} を想定
    source_uri = inputs.get("source_uri")
    read_spec = inputs.get("read_spec") or {}

    # 今日の段階では"読む"はしない。契約だけ固定する
    result = {
        "source_uri": source_uri,
        "warnings": [],
        "suggested_read_spec": read_spec,
        "columns": [],  # 将来: [{"name": "...", "dtype": "..."}]
    }

    # control artifacts を固定キーに保存
    store_.put(INSPECT_RESULT, result)
    store_.put(READ_SPEC, result["suggested_read_spec"])

    # runtimeのoutputsを使わない（契約揺れ回避）
    return {}


def inspect_filename_kind_op(inputs: dict[str, Any], store_) -> dict[str, Any]:
    """
    Inspect step: Identifies input "kind" from filename pattern only.

    Inputs:
    - input_profile_name: str (profile name to load kind_rules from)
    - path: str (file path to inspect)

    Returns:
    - {"result": {...}} where result is a dict with:
      - schema_version: "inspect_result_v1"
      - input_profile_name: str
      - resolved_path: str
      - filename: str
      - detected_kind: str | None
      - evidence: dict with matched_pattern, matcher
    """
    input_profile_name = inputs.get("input_profile_name")
    if not input_profile_name:
        raise ValueError("input_profile_name is required")

    path_str = inputs.get("path")
    if not path_str:
        raise ValueError("path is required")

    # Load profile config to get kind_rules
    try:
        config = store_.configs.get_spec("input_profile", input_profile_name)
    except KeyError as e:
        raise ValueError(f"input_profile '{input_profile_name}' not found in configs") from e

    kind_rules = config.get("kind_rules")
    if kind_rules is None:
        raise ValueError(f"input_profile '{input_profile_name}' missing 'kind_rules' key")

    # Extract basename from path
    path = Path(path_str)
    filename = path.name

    # Match filename against rules (in order)
    detected_kind = None
    matched_pattern = None

    for rule in kind_rules:
        pattern = rule.get("pattern")
        kind = rule.get("kind")
        if pattern and kind:
            if re.match(pattern, filename):
                detected_kind = kind
                matched_pattern = pattern
                break

    # Build result
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


def register(registry) -> None:
    registry.register("inspect", inspect_op)
    registry.register("inspect_filename_kind", inspect_filename_kind_op)
