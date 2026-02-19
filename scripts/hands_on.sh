#!/usr/bin/env bash
# Step-by-step hands-on: run each step and pause so you can confirm the change.
# Usage: ./scripts/hands_on.sh   (API must be running on BASE_URL)
# Requires: FLOWBOOK_DATABASE_URL, FLOWBOOK_DB_RESET=1 for init, fixture xlsx

set -e
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
FIXTURE="${FIXTURE:-tests/fixtures/excel/test_detect_region_input.xlsx}"
TMP_JSON=$(mktemp)
trap 'rm -f "$TMP_JSON"' EXIT

_curl_json() {
  curl -sS -o "$TMP_JSON" "$@"
  python3 -m json.tool < "$TMP_JSON" || {
    echo "--- Response (not JSON) ---"
    cat "$TMP_JSON"
    exit 1
  }
}

if [[ ! -f "$FIXTURE" ]]; then
  echo "Fixture not found: $FIXTURE"
  echo "Create tests/fixtures/excel/ or set FIXTURE=path/to/input.xlsx"
  exit 1
fi

read -p "Full init DB (clear artifacts + configs, then seed)? [Y/n] " INIT
if [[ "${INIT:-Y}" =~ ^[nN]$ ]]; then
  echo "Skipping init."
else
  FLOWBOOK_DB_RESET=1 poetry run python scripts/reset_db.py
fi
echo ""

echo "=== Step 1: Health ==="
_curl_json "$BASE_URL/health"
echo ""
read -p "Press Enter for Step 2..."

echo "=== Step 2: Inspect ==="
_curl_json -F "file=@$FIXTURE" -F "input_profile_name=source" "$BASE_URL/inspect"
echo ""
read -p "Press Enter for Step 3..."

echo "=== Step 3: Import (table extract) ==="
_curl_json -F "file=@$FIXTURE" \
  -F "template_name=import_excel_region" \
  -F "sheet_name=data" \
  -F "region_profile_name=detail_region" \
  "$BASE_URL/import"
IMPORT_JSON=$(cat "$TMP_JSON")

RUN_ID=$(echo "$IMPORT_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('run_id',''))" 2>/dev/null || true)
READ_DF_KEY=$(echo "$IMPORT_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for k in d.get('artifacts_written', []):
    if k.endswith('/read/df'):
        print(k)
        break
" 2>/dev/null || true)
echo ""
echo "run_id: $RUN_ID"
echo "read/df key (imported): $READ_DF_KEY"
read -p "Press Enter for Step 4..."

echo "=== Step 4: List artifacts ==="
_curl_json "$BASE_URL/artifacts"
echo ""
read -p "Press Enter for Step 5..."

echo "=== Step 5: Export (filter/map from import) ==="
BYTES_KEY=""
if [[ -z "$READ_DF_KEY" ]]; then
  echo "No read/df key from Step 3. Export skipped."
else
  _curl_json -F "source_artifact_key=$READ_DF_KEY" \
    -F "mapping_name=detect_region_test" \
    "$BASE_URL/export/from_artifact"
  EXPORT_JSON=$(cat "$TMP_JSON")
  BYTES_KEY=$(echo "$EXPORT_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for k in d.get('artifacts_written', []):
    if k.endswith('/write/bytes'):
        print(k)
        break
" 2>/dev/null || true)
  echo ""
  echo "write/bytes key (exported): $BYTES_KEY"
fi
read -p "Press Enter for Step 6..."

echo "=== Step 6: Download ==="
IMPORTED_FILE="demo_imported.xlsx"
EXPORTED_FILE="demo_exported.xlsx"
if [[ -n "$READ_DF_KEY" ]]; then
  curl -sS -o "$IMPORTED_FILE" "$BASE_URL/artifacts/${READ_DF_KEY}/as_excel"
  echo "Saved imported: $IMPORTED_FILE"
fi
if [[ -n "$BYTES_KEY" ]]; then
  curl -sS -o "$EXPORTED_FILE" "$BASE_URL/artifacts/${BYTES_KEY}/raw"
  echo "Saved exported: $EXPORTED_FILE"
fi
if [[ -z "$READ_DF_KEY" && -z "$BYTES_KEY" ]]; then
  echo "Could not determine keys. Download manually."
fi
echo ""
echo "Done."
