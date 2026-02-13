"""
Minimal CLI (stdlib argparse only): --version and doctor.
"""

from __future__ import annotations

import argparse
import sys


def _flowbook_version() -> str:
    import flowbook
    return flowbook.__version__


def _python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _run_doctor() -> int:
    import platform

    print(f"Python:  {_python_version()}")
    print(f"OS:     {platform.system()} {platform.release()}")
    print(f"flowbook: {_flowbook_version()}")
    print()

    missing: list[str] = []
    hints: list[str] = []

    # excel
    try:
        __import__("pandas")
        __import__("openpyxl")
        print("excel:   ok (pandas, openpyxl)")
    except ImportError:
        print("excel:   missing (pandas, openpyxl)")
        missing.append("excel")
        hints.append('pip install "flowbook[excel]"')

    # postgres
    try:
        __import__("psycopg")
        print("postgres: ok (psycopg)")
    except ImportError:
        print("postgres: missing (psycopg)")
        missing.append("postgres")
        hints.append('pip install "flowbook[postgres]"')

    # fastapi
    try:
        __import__("fastapi")
        __import__("uvicorn")
        print("fastapi: ok (fastapi, uvicorn)")
    except ImportError:
        print("fastapi: missing (fastapi, uvicorn)")
        missing.append("fastapi")
        hints.append('pip install "flowbook[fastapi]"')

    if missing:
        print()
        print("To install missing extras:")
        for h in hints:
            print(f"  {h}")
        print('  pip install "flowbook[full]"  # all extras')
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="flowbook")
    parser.add_argument(
        "--version",
        action="version",
        version=_flowbook_version(),
    )
    subparsers = parser.add_subparsers(dest="command", help="commands")

    doctor_parser = subparsers.add_parser("doctor", help="check env and suggest missing extras")
    doctor_parser.set_defaults(func=lambda _: _run_doctor())

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
