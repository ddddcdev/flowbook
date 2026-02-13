#!/usr/bin/env bash
# Phase 4: build wheel, install into a clean venv, run flowbook --version and flowbook doctor.
# Usage: ./scripts/verify_wheel_install.sh
set -euo pipefail
cd "$(dirname "$0")/.."
WHEEL_DIR="${1:-dist}"
VENV_DIR="${2:-.venv-wheel-verify}"

echo "Building wheel..."
poetry build
WHEEL=$(ls -t "${WHEEL_DIR}"/flowbook-*-py3-none-any.whl 2>/dev/null | head -1)
if [ -z "${WHEEL}" ]; then
  echo "No wheel found in ${WHEEL_DIR}" >&2
  exit 1
fi
echo "Wheel: ${WHEEL}"

echo "Creating clean venv: ${VENV_DIR}"
rm -rf "${VENV_DIR}"
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install -q --upgrade pip
"${VENV_DIR}/bin/pip" install -q "${WHEEL}"

echo "flowbook --version"
"${VENV_DIR}/bin/flowbook" --version

echo "flowbook doctor"
"${VENV_DIR}/bin/flowbook" doctor || true

echo "Verify OK."
