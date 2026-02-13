"""
Smoke test for flowbook CLI: --version and doctor run without error.
"""

from __future__ import annotations

import re
import subprocess
import sys

import pytest

pytestmark = pytest.mark.smoke


def test_cli_version_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "flowbook.cli", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # PEP 440–style: 0.1.0a1, 0.1.0, 0.1
    assert re.match(r"^\d+(\.\d+){0,2}([a-z]+\d+)?\s*$", result.stdout.strip())


def test_cli_doctor_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "flowbook.cli", "doctor"],
        capture_output=True,
        text=True,
    )
    assert result.returncode in (0, 1)
    assert "Python:" in result.stdout
    assert "flowbook:" in result.stdout
    assert "excel:" in result.stdout
