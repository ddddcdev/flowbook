# flowbook-api

Thin FastAPI surface for flowbook. Reference implementation — copy and
extend for project-specific APIs.

## Quick start

### With Postgres (production / field use)

Option A — use a `.env` file (recommended). Install the plugin once, then `.env` is loaded for every `poetry run`:

```bash
poetry self add poetry-dotenv-plugin
cp .env.example .env
# Then start (plugin loads .env automatically)
poetry run uvicorn apps.api.app.main:app --reload --port 8000
```

Option B — set in the shell:

```bash
# Requires: docker compose -f infra/compose.postgres.yml up -d
FLOWBOOK_DATABASE_URL=postgresql://flowbook:flowbook@localhost:5432/flowbook \
  poetry run uvicorn apps.api.app.main:app --reload --port 8000
```

### Without Postgres (development / smoke test)

```bash
poetry run uvicorn apps.api.app.main:app --reload --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

API docs (auto-generated): <http://localhost:8000/docs>

### Verify dev CLI `artifacts list` (with Postgres)

1. **Seed one artifact** (same DB the API will use):

   ```bash
   FLOWBOOK_DATABASE_URL=postgresql://flowbook:flowbook@localhost:5432/flowbook \
     poetry run python scripts/seed_one_artifact.py
   # Seeded artifact: smoke-test/artifact
   ```

2. **Start the API** with the same URL (in another terminal):

   ```bash
   FLOWBOOK_DATABASE_URL=postgresql://flowbook:flowbook@localhost:5432/flowbook \
     poetry run uvicorn apps.api.app.main:app --reload --port 8000
   ```

3. **List artifacts**:

   ```bash
   poetry run flowbook-dev artifacts list
   # Should show a table with smoke-test/artifact
   ```
