"""
Tests for the inspect_filename_kind step.

MVP behavior:
- Identify file "kind" from filename pattern (regex matching only)
- input_profile_name loads kind_rules from config
- path is the file to inspect
- Return inspect result dict as artifact
"""

from __future__ import annotations

import uuid

import pytest

from flowbook.artifacts.memory_store import InMemoryArtifactsStore
from flowbook.configs.memory_store import InMemoryConfigStore
from flowbook.engine.engine import Engine
from flowbook.registry.extensions import register_steps
from flowbook.registry.registry import Registry

# Test configuration: single input profile with kind_rules
PROFILE_CONFIG = {
    "kind_rules": [
        {"pattern": r"^fileA_.*\.xlsx$", "kind": "fileA"},
        {"pattern": r"^fileB_.*\.xlsx$", "kind": "fileB"},
        {"pattern": r"^fileC_.*\.xlsx$", "kind": "fileC"},
    ]
}


def create_engine_and_session():
    """Helper to create engine and session with test config."""
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    # Preload single input profile with kind_rules
    config_store.put_spec(
        kind="input_profile",
        name="source",
        spec=PROFILE_CONFIG,
        config_id="test-source",
    )

    registry = Registry()
    register_steps(registry)

    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
        meta={"env": "test"},
    )

    run_session = engine.prepare(run_id=str(uuid.uuid4()))
    return run_session


@pytest.mark.parametrize(
    "filename,expected_kind,expected_pattern",
    [
        ("fileA_sample.xlsx", "fileA", r"^fileA_.*\.xlsx$"),
        ("fileA_data.xlsx", "fileA", r"^fileA_.*\.xlsx$"),
        ("fileB_report.xlsx", "fileB", r"^fileB_.*\.xlsx$"),
        ("fileB_metrics.xlsx", "fileB", r"^fileB_.*\.xlsx$"),
        ("fileC_analysis.xlsx", "fileC", r"^fileC_.*\.xlsx$"),
        ("fileC_export.xlsx", "fileC", r"^fileC_.*\.xlsx$"),
    ],
)
def test_inspect_matches_filename_to_kind(filename, expected_kind, expected_pattern):
    """Test inspect step correctly identifies kind from filename pattern."""
    # --- Arrange
    run_session = create_engine_and_session()

    # Provide path for inspection
    path = f"/data/{filename}"
    run_session.put_input("input_profile_name", "source")
    run_session.put_input("path", path)

    # Pipeline config
    config = {
        "steps": [
            {
                "name": "inspect",
                "op": "inspect_filename_kind",
                "inputs": {
                    "input_profile_name": "input_profile_name",
                    "path": "path",
                },
            }
        ]
    }

    # --- Act
    info = run_session.exec(config=config)

    # --- Assert
    assert info.status == "succeeded", f"Run failed: {info.errors}"
    step_info = info.steps[0]
    assert step_info.status == "succeeded"

    result_key = step_info.outputs["result"]
    result = run_session.get(result_key)

    # Validate result schema
    assert result["schema_version"] == "inspect_result_v1"
    assert result["input_profile_name"] == "source"
    assert result["resolved_path"] == path
    assert result["filename"] == filename
    assert result["detected_kind"] == expected_kind
    assert result["evidence"]["matcher"] == "filename_regex"
    assert result["evidence"]["matched_pattern"] == expected_pattern


def test_inspect_unknown_filename_no_error():
    """Test inspect step returns None for unknown filename (no error raised)."""
    # --- Arrange
    run_session = create_engine_and_session()

    # Provide unknown filename
    path = "/data/unknown_file.txt"
    run_session.put_input("input_profile_name", "source")
    run_session.put_input("path", path)

    # Pipeline config
    config = {
        "steps": [
            {
                "name": "inspect",
                "op": "inspect_filename_kind",
                "inputs": {
                    "input_profile_name": "input_profile_name",
                    "path": "path",
                },
            }
        ]
    }

    # --- Act
    info = run_session.exec(config=config)

    # --- Assert (should succeed, but detected_kind is None)
    assert info.status == "succeeded", f"Run failed: {info.errors}"
    step_info = info.steps[0]

    result_key = step_info.outputs["result"]
    result = run_session.get(result_key)

    # Key assertion: detected_kind is None for unknown kind
    assert result["detected_kind"] is None
    # matched_pattern should also be None (no match)
    assert result["evidence"]["matched_pattern"] is None
    assert result["filename"] == "unknown_file.txt"
    assert result["evidence"]["matcher"] == "filename_regex"


def test_inspect_missing_config_raises_error():
    """Test inspect step raises error when input_profile config not found."""
    # --- Arrange
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    # Do NOT preload any config for "missing_profile"

    registry = Registry()
    register_steps(registry)

    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
        meta={"env": "test"},
    )

    run_session = engine.prepare(run_id=str(uuid.uuid4()))
    run_session.put_input("input_profile_name", "missing_profile")
    run_session.put_input("path", "/data/fileA_test.xlsx")

    # Pipeline config
    config = {
        "steps": [
            {
                "name": "inspect",
                "op": "inspect_filename_kind",
                "inputs": {
                    "input_profile_name": "input_profile_name",
                    "path": "path",
                },
            }
        ]
    }

    # --- Act
    info = run_session.exec(config=config)

    # --- Assert: run should fail
    assert info.status == "failed"
    assert len(info.errors) > 0
    assert "not found" in info.errors[0]


def test_inspect_missing_kind_rules_raises_error():
    """Test inspect step raises error when kind_rules missing from config."""
    # --- Arrange
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    # Preload config without kind_rules
    config_store.put_spec(
        kind="input_profile",
        name="incomplete",
        spec={"some_other_field": "value"},
        config_id="test-incomplete",
    )

    registry = Registry()
    register_steps(registry)

    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
        meta={"env": "test"},
    )

    run_session = engine.prepare(run_id=str(uuid.uuid4()))
    run_session.put_input("input_profile_name", "incomplete")
    run_session.put_input("path", "/data/fileA_test.xlsx")

    # Pipeline config
    config = {
        "steps": [
            {
                "name": "inspect",
                "op": "inspect_filename_kind",
                "inputs": {
                    "input_profile_name": "input_profile_name",
                    "path": "path",
                },
            }
        ]
    }

    # --- Act
    info = run_session.exec(config=config)

    # --- Assert: run should fail
    assert info.status == "failed"
    assert len(info.errors) > 0
    assert "kind_rules" in info.errors[0]


def test_inspect_missing_path_input_raises_error():
    """Test inspect step raises error when path input is missing."""
    # --- Arrange
    run_session = create_engine_and_session()

    # Only provide input_profile_name, NOT path
    run_session.put_input("input_profile_name", "source")

    # Pipeline config
    config = {
        "steps": [
            {
                "name": "inspect",
                "op": "inspect_filename_kind",
                "inputs": {
                    "input_profile_name": "input_profile_name",
                    # Note: path binding missing/unresolved
                },
            }
        ]
    }

    # --- Act
    info = run_session.exec(config=config)

    # --- Assert: run should fail
    assert info.status == "failed"
    assert len(info.errors) > 0
