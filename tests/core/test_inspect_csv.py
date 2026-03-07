"""Tests for inspect_filename step with demo_csv_inspect profile."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from flowbook import (
    Engine,
    InMemoryArtifactsStore,
    InMemoryConfigStore,
    Registry,
    register_steps,
)
from flowbook.core.configs.spec_types import EntityPlanMap, InputProfile

pytestmark = pytest.mark.unit

FIXTURE_CSV = Path(__file__).resolve().parent.parent / "fixtures" / "csv" / "demo_input.csv"


def create_engine_with_csv_profile():
    """Create engine with demo_csv_inspect and EntityPlanMap."""
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    config_store.put_spec(
        InputProfile,
        "demo_csv_inspect",
        {
            "kind_rules": [{"pattern": r".*\.csv$", "kind": "demo/csv"}],
            "inspect_step_name": "inspect_filename",
        },
        config_id=str(uuid4()),
    )
    config_store.put_spec(
        EntityPlanMap,
        "default",
        {"map": {"demo/csv": "import_csv"}, "default": "import_csv"},
        config_id=str(uuid4()),
    )

    registry = Registry()
    register_steps(registry)

    return Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
    )


def test_inspect_filename_demo_csv_detects_kind():
    """Inspect with demo_csv_inspect + demo_input.csv returns detected_kind=demo/csv."""
    engine = create_engine_with_csv_profile()
    with engine.create_run() as session:
        session.put_input("input_profile_name", "demo_csv_inspect")
        session.put_input("filename", "demo_input.csv")

        config = {
            "name": "inspect",
            "steps": [
                {
                    "name": "inspect",
                    "op": "inspect_filename",
                    "inputs": {
                        "input_profile_name": "@input_profile_name",
                        "filename": "@filename",
                    },
                }
            ],
        }

        info = session.exec_plan(plan_config=config)
        assert info.status == "succeeded", info.errors

        result_key = info.steps[0].outputs["result"]
        result = session.get_dict(result_key)

        assert result["detected_kind"] == "demo/csv"
        assert result["plan_name"] == "import_csv"
        assert result["filename"] == "demo_input.csv"


def test_inspect_csv_fixture_exists():
    """Ensure demo_input.csv fixture exists for Streamlit / hands-on."""
    assert FIXTURE_CSV.exists(), (
        "Run: flowbook fixture generate -o tests/fixtures/excel --csv-dir tests/fixtures/csv"
    )
    content = FIXTURE_CSV.read_text(encoding="utf-8")
    assert "LineNo" in content
    assert "Item" in content
