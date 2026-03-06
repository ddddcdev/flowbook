# About this demo

Use this app to try the full flow: **Inspect → Import → Export → Results → Download**.

## Fixtures (generate if missing)

- Excel: `tests/fixtures/excel/test_detect_region_input.xlsx` (profile `demo_excel_inspect`)
- CSV: `tests/fixtures/csv/demo_input.csv` (profile `demo_csv_inspect`)

→ `flowbook fixture generate -o tests/fixtures/excel --csv-dir tests/fixtures/csv`

## Sequence

1. **Inspect** — Upload the file above, entity_key `demo/excel`, profile `demo_excel_inspect`
2. **Import** — Same file, plan `import_excel_simple`, creates read/df artifact
3. **Export** — From Import's read/df, mapping `detect_region_test`, creates write/bytes
4. **Results** — Select the row with read/df or write/bytes
5. **Download** — Use the selected result's artifact (as Excel or raw)

Connects to the flowbook API (FastAPI). Use Health tab to verify API is running.
