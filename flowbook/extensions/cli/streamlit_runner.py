"""Streamlit UI runner with venv handling (separate venv for pandas<3 compatibility)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _find_repo_root() -> Path:
    """Find repo root (where pyproject.toml or flowbook package lives)."""
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "pyproject.toml").exists():
            return parent
        if (parent / "flowbook").is_dir() and (parent / "flowbook" / "extensions" / "ui").exists():
            return parent
    return Path.cwd()


def run(venv_dir: str | Path = ".venv-ui", extra_args: list[str] | None = None) -> int:
    """Create .venv-ui if needed, install flowbook+streamlit, run Streamlit. Returns exit code."""
    repo = _find_repo_root()
    venv = Path(venv_dir)
    if not venv.is_absolute():
        venv = repo / venv

    def _ensure_deps() -> None:
        pip = venv / "bin" / "pip" if os.name != "nt" else venv / "Scripts" / "pip.exe"
        pkgs = ["streamlit", "requests", "altair>=4,<5", "-q"]
        if sys.version_info >= (3, 13):
            pkgs.insert(-1, "standard-imghdr")  # imghdr removed in 3.13
        if (repo / "pyproject.toml").exists():
            subprocess.run([str(pip), "install", "-e", str(repo)] + pkgs, check=True, cwd=repo)
        else:
            subprocess.run([str(pip), "install", "flowbook[full]"] + pkgs, check=True)

    if not venv.exists():
        print(f"Creating {venv} (streamlit + requests)...")
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, cwd=repo)
        _ensure_deps()
    else:
        streamlit_exe = (
            venv / "bin" / "streamlit" if os.name != "nt" else venv / "Scripts" / "streamlit.exe"
        )
        if not streamlit_exe.exists():
            print(f"Installing streamlit into {venv}...")
            _ensure_deps()

    streamlit_exe = (
        venv / "bin" / "streamlit" if os.name != "nt" else venv / "Scripts" / "streamlit.exe"
    )
    app_path = repo / "flowbook" / "extensions" / "ui" / "app.py"
    if not app_path.exists():
        import flowbook.extensions.ui.app as mod

        app_path = Path(mod.__file__)
    args = [str(streamlit_exe), "run", str(app_path)]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(args, cwd=repo).returncode
