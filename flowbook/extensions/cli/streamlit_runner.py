"""Streamlit UI runner with venv handling (separate venv for pandas<3 compatibility)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _find_repo_root() -> Path:
    """Find repo root (where pyproject.toml or flowbook package lives).

    Prefer pyproject.toml; flowbook/extensions/ui alone matches site-packages when
    installed, so we require pyproject.toml for that path too (avoids .venv-ui in
    site-packages and WSL/Windows 260-char path limits).
    """
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "pyproject.toml").exists():
            return parent
        if (
            (parent / "flowbook").is_dir()
            and (parent / "flowbook" / "extensions" / "ui").exists()
            and (parent / "pyproject.toml").exists()
        ):
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
            # Two-stage install: pip install -e . + pkgs in one call can cause
            # KeyError: '__version__' during editable build. Install deps first.
            subprocess.run([str(pip), "install"] + pkgs, check=True, cwd=repo)
            subprocess.run([str(pip), "install", "-e", str(repo)], check=True, cwd=repo)
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
        # Installed case: avoid importing flowbook.extensions.ui.app (pulls streamlit/
        # requests which may not be in main venv). Use flowbook.__file__ instead.
        import flowbook

        app_path = Path(flowbook.__file__).resolve().parent / "extensions" / "ui" / "app.py"
    args = [str(streamlit_exe), "run", str(app_path)]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(args, cwd=repo).returncode
