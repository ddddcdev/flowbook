"""Release verification: PyPI install, wheel install."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def verify_pypi(version: str, full: bool) -> int:
    """Install flowbook from PyPI into temp venv, run --version and doctor. Returns exit code."""
    import flowbook

    default_ver = getattr(flowbook, "__version__", "0.1.0a1")
    ver = version or default_ver
    venv_dir = Path.cwd() / ".venv-pypi-verify"
    if venv_dir.exists():
        import shutil

        shutil.rmtree(venv_dir)

    python = sys.executable
    pip = (
        str(venv_dir / "bin" / "pip")
        if os.name != "nt"
        else str(venv_dir / "Scripts" / "pip.exe")
    )
    flowbook_exe = (
        str(venv_dir / "bin" / "flowbook")
        if os.name != "nt"
        else str(venv_dir / "Scripts" / "flowbook.exe")
    )

    def run(cmd: list[str]) -> int:
        return subprocess.run(cmd, check=False).returncode

    print(f"Creating temporary venv: {venv_dir}")
    if run([python, "-m", "venv", str(venv_dir)]) != 0:
        return 1
    if run([pip, "install", "-q", "--upgrade", "pip"]) != 0:
        return 1

    print(f"=== Core: flowbook=={ver} ===")
    if run([pip, "install", "-q", f"flowbook=={ver}"]) != 0:
        return 1
    print("flowbook --version")
    if run([flowbook_exe, "--version"]) != 0:
        return 1
    print("flowbook doctor")
    run([flowbook_exe, "doctor"])

    if full:
        print(f"\n=== [full] extras: flowbook[full]=={ver} ===")
        if run([pip, "install", "-q", f"flowbook[full]=={ver}"]) != 0:
            return 1
        print("flowbook --version")
        if run([flowbook_exe, "--version"]) != 0:
            return 1
        print("flowbook doctor")
        run([flowbook_exe, "doctor"])

    import shutil

    shutil.rmtree(venv_dir)
    print(f"\nVerify OK (flowbook=={ver}" + (", core + [full]" if full else "") + ").")
    return 0


def verify_wheel(wheel_dir: str | Path, venv_dir: str | Path) -> int:
    """Build wheel, install into temp venv, run --version and doctor. Returns exit code."""
    wdir = Path(wheel_dir) if wheel_dir else Path.cwd() / "dist"
    wheels = sorted(
        wdir.glob("flowbook-*-py3-none-any.whl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not wheels:
        print("Building wheel...")
        subprocess.run([sys.executable, "-m", "poetry", "build"], check=False, cwd=Path.cwd())
        wheels = sorted(
            wdir.glob("flowbook-*-py3-none-any.whl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    if not wheels:
        print(f"No wheel found in {wdir}", file=sys.stderr)
        return 1
    wheel = wheels[0]
    print(f"Wheel: {wheel}")

    vdir = Path(venv_dir) if venv_dir else Path.cwd() / ".venv-wheel-verify"
    if vdir.exists():
        import shutil

        shutil.rmtree(vdir)

    python = sys.executable
    pip = (
        str(vdir / "bin" / "pip")
        if os.name != "nt"
        else str(vdir / "Scripts" / "pip.exe")
    )
    flowbook_exe = (
        str(vdir / "bin" / "flowbook")
        if os.name != "nt"
        else str(vdir / "Scripts" / "flowbook.exe")
    )

    def run(cmd: list[str]) -> int:
        return subprocess.run(cmd, check=False).returncode

    print(f"Creating clean venv: {vdir}")
    if run([python, "-m", "venv", str(vdir)]) != 0:
        return 1
    if run([pip, "install", "-q", "--upgrade", "pip"]) != 0:
        return 1
    if run([pip, "install", "-q", str(wheel)]) != 0:
        return 1

    print("flowbook --version")
    if run([flowbook_exe, "--version"]) != 0:
        return 1
    print("flowbook doctor")
    run([flowbook_exe, "doctor"])

    import shutil

    shutil.rmtree(vdir)
    print("\nVerify OK.")
    return 0
