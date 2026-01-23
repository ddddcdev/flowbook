from __future__ import annotations

from flowbook.artifacts.keys import INSPECT_RESULT, READ_SPEC, SOURCE_URI


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

    # 今日の段階では“読む”はしない。契約だけ固定する
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


def register(registry) -> None:
    registry.register("inspect", inspect_op)
