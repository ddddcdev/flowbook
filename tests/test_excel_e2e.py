from __future__ import annotations

from uuid import uuid4

import pandas as pd
import pytest

from extensions.steps.apply_mapping import ApplyMappingOp
from extensions.steps.read_excel import ReadExcelOp
from extensions.steps.write_excel import WriteExcelOp
from flowbook.artifacts.memory_store import InMemoryArtifactsStore
from flowbook.configs.memory_store import InMemoryConfigStore
from flowbook.configs.spec_types import Mapping
from flowbook.engine.engine import Engine
from flowbook.registry.extensions import register_steps
from flowbook.registry.registry import Registry

pytestmark = pytest.mark.e2e


def test_excel_read_apply_mapping_write_e2e(tmp_path) -> None:
    """
    E2E: Excel → df → apply_mapping → df → Excel(bytes)
    Using InMemoryArtifactsStore + InMemoryConfigStore
    """
    # Setup stores
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()
    registry = Registry()
    register_steps(registry)

    # 1) Prepare input Excel
    df_in = pd.DataFrame({"a": [1, -1, 2], "b": [10, 20, 30], "x": [9, 9, 9]})
    in_excel_path = tmp_path / "in.xlsx"
    with pd.ExcelWriter(in_excel_path, engine="openpyxl") as writer:
        df_in.to_excel(writer, sheet_name="in", index=False)

    # 2) Setup mapping spec in config store
    mapping_name = "test_mvp"
    mapping_spec = {
        "ops": [
            {"op": "select_cols", "cols": ["a", "b"]},
            {"op": "rename", "map": {"a": "A"}},
            {"op": "filter_rows", "expr": "A > 0"},
        ]
    }
    config_store.put_spec(Mapping, mapping_name, mapping_spec, config_id=str(uuid4()))

    # 3) Setup pipeline config (no planner, direct execution)
    pipeline_config = {
        "steps": [
            {
                "name": "read",
                "op": "read_excel",
                "inputs": {
                    ReadExcelOp.Inputs.PATH: "excel_path",
                    ReadExcelOp.Inputs.SHEET: "sheet_name",
                    ReadExcelOp.Inputs.HEADER: "header_row",
                },
            },
            {
                "name": "map",
                "op": "apply_mapping",
                "inputs": {
                    ApplyMappingOp.Inputs.DF: "read/df",
                    ApplyMappingOp.Inputs.MAPPING_NAME: "mapping_name_val",
                },
            },
            {
                "name": "write",
                "op": "write_excel",
                "inputs": {
                    WriteExcelOp.Inputs.DF: "map/df",
                },
            },
        ]
    }

    # 4) Execute via Engine
    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
        meta={"env": "test"},
    )
    run = engine.prepare()

    # Put input parameters as artifacts (path, sheet, header for read_excel)
    run.put_input("excel_path", str(in_excel_path))
    run.put_input("sheet_name", "in")
    run.put_input("header_row", 0)
    run.put_input("mapping_name_val", mapping_name)
    info = run.exec(pipeline_config=pipeline_config)

    # 5) Verify execution succeeded
    assert info.status == "succeeded"
    assert len(info.steps) == 3

    # 6) Verify output bytes and content
    out_bytes_key = info.steps[2].outputs[WriteExcelOp.Outputs.BYTES]
    out_bytes = run.get_bytes(out_bytes_key)
    out_excel_path = tmp_path / "out.xlsx"
    out_excel_path.write_bytes(out_bytes)

    df_out = pd.read_excel(out_excel_path, sheet_name="out", engine="openpyxl")

    # Verify mapping was applied: columns are ["A", "b"], rows match filtered data
    assert list(df_out.columns) == ["A", "b"]
    assert len(df_out) == 2
    assert df_out["A"].tolist() == [1, 2]
    assert df_out["b"].tolist() == [10, 30]
