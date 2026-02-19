# Config directory (dev/demo)

Goal: add JSON configs (column names, mapping rules, templates) and load them into Postgres via seed script.

Conventions:
- File name (stem) becomes the config name.
- One file = one spec (InputProfile / Mapping / PlanTemplate / Routing).
- JSON body is the spec dict passed to flowbook config store.

Directory layout:
- configs/input_profiles/*.json
- configs/mappings/*.json
- configs/templates/*.json
- configs/routing/*.json

Seed with: `FLOWBOOK_DATABASE_URL=... flowbook db seed --config-dir configs`
