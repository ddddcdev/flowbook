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
                out = out.query(expr, engine="python")
            except Exception as e:
                raise MappingSpecError(f"filter_rows expr failed: {expr}") from e

        elif t == "expr_df":
            columns = op.get("columns")
            if not isinstance(columns, list) or not columns:
                raise MappingSpecError("expr_df requires non-empty columns list")
            for col_spec in columns:
                if not isinstance(col_spec, dict):
                    raise MappingSpecError("expr_df columns entries must be dict with name, expr")
                name = col_spec.get("name")
                expr = col_spec.get("expr")
                if not isinstance(name, str) or not name.strip():
                    raise MappingSpecError("expr_df column requires name")
                if not isinstance(expr, str) or not expr.strip():
                    raise MappingSpecError("expr_df column requires expr")
                try:
                    out[name] = out.eval(expr, engine="python")
                except Exception as e:
                    raise MappingSpecError(f"expr_df expr failed: {name!r} {expr!r}") from e

        else:
            raise MappingSpecError(f"unknown op: {t}")

    return out
