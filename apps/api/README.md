# flowbook-api

Thin FastAPI surface for flowbook. Reference implementation — copy and
extend for project-specific APIs.

## Quick start

### With Postgres (production / field use)

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
