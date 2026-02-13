# flowbook/extensions/excel/mapping/apply.py
from __future__ import annotations

from typing import Any

import pandas as pd


class MappingSpecError(ValueError):
    pass


def apply_mapping_ops(df: pd.DataFrame, ops: list[dict[str, Any]]) -> pd.DataFrame:
    out = df

    for op in ops:
        t = op.get("op")
        if t == "select_cols":
            cols = op.get("cols")
            if not isinstance(cols, list) or not cols:
                raise MappingSpecError("select_cols requires non-empty cols")
            missing = [c for c in cols if c not in out.columns]
            if missing:
                raise MappingSpecError(f"missing columns for select_cols: {missing}")
            out = out.loc[:, cols]

        elif t == "rename":
            m = op.get("map")
            if not isinstance(m, dict) or not m:
                raise MappingSpecError("rename requires non-empty map")
            missing = [c for c in m.keys() if c not in out.columns]
            if missing:
                raise MappingSpecError(f"missing columns for rename: {missing}")

            renamed = out.rename(columns=m)
            if renamed.columns.duplicated().any():
                dups = renamed.columns[renamed.columns.duplicated()].tolist()
                raise MappingSpecError(f"duplicate columns after rename: {dups}")
            out = renamed

        elif t == "filter_rows":
            expr = op.get("expr")
            if not isinstance(expr, str) or not expr.strip():
                raise MappingSpecError("filter_rows requires expr")
            try:
                out = out.query(expr)
            except Exception as e:
                raise MappingSpecError(f"filter_rows expr failed: {expr}") from e

        else:
            raise MappingSpecError(f"unknown op: {t}")

    return out
