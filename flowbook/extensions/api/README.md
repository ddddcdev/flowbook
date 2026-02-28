# flowbook-api

Thin FastAPI surface for flowbook. Reference implementation — copy and
extend for project-specific APIs.

## Quick start

### With Postgres (production / field use)

Option A — use a `.env` file (recommended). Pass `--env-file` or set `UV_ENV_FILE=.env`:

```bash
cp .env.example .env
uv run --env-file .env uvicorn flowbook.extensions.api.app:app --reload --port 8000
# Or: export UV_ENV_FILE=.env  (then uv run picks it up)
```

Option B — set in the shell:

```bash
# Requires: docker compose -f infra/compose.postgres.yml up -d
FLOWBOOK_DATABASE_URL=postgresql://flowbook:flowbook@localhost:5432/flowbook \
  uv run uvicorn flowbook.extensions.api.app:app --reload --port 8000
```

### Without Postgres (development / smoke test)

```bash
uv run uvicorn flowbook.extensions.api.app:app --reload --port 8000
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
     flowbook db seed-artifact
   # Seeded artifact: seed/demo/excel/result
   ```

2. **Start the API** with the same URL (in another terminal):

   ```bash
   FLOWBOOK_DATABASE_URL=postgresql://flowbook:flowbook@localhost:5432/flowbook \
     uv run uvicorn flowbook.extensions.api.app:app --reload --port 8000
   ```

3. **List artifacts**:

   ```bash
   flowbook artifacts list
   # Should show a table with seed/demo/excel/result
   ```
