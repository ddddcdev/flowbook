"""
Smoke tests for flowbook-dev CLI: version, doctor, artifacts --help and list error path.
"""

from __future__ import annotations

import re
import subprocess
import sys

import pytest

pytestmark = pytest.mark.smoke


def test_dev_cli_version_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "flowbook.extensions.dev_cli", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert re.match(r"^\d+(\.\d+){0,2}([a-z]+\d+)?\s*$", result.stdout.strip())


def test_dev_cli_doctor_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "flowbook.extensions.dev_cli", "doctor"],
        capture_output=True,
        text=True,
    )
    assert result.returncode in (0, 1)
    assert "Python:" in result.stdout
    assert "flowbook:" in result.stdout


def test_dev_cli_artifacts_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "flowbook.extensions.dev_cli", "artifacts", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "list" in result.stdout
    assert "get" in result.stdout
    assert "head" in result.stdout


def test_dev_cli_artifacts_list_unreachable_exits_nonzero() -> None:
    # No server on this port; CLI should exit 1 and print error
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "flowbook.extensions.dev_cli",
            "artifacts",
            "list",
            "--base-url",
            "http://127.0.0.1:19999",
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode != 0
    assert "Error" in result.stderr or "error" in result.stderr.lower()
