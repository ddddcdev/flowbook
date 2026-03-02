# flowbook infra

Docker Compose and Dockerfiles for flowbook development and cloud deploy.

## Usage from flowbook repo

Run from the **flowbook repo root**:

```sh
flowbook db up
flowbook api up
flowbook streamlit up
```

Or directly (pass env file to avoid variable warnings):

```sh
docker compose -f infra/compose.postgres.yml --env-file infra/.env.postgres up -d
docker compose -f infra/compose.api.yml --env-file infra/.env.api up -d
docker compose -f infra/compose.streamlit.yml --env-file infra/.env.streamlit up -d
```

For fresh DB (remove volume and recreate):

```sh
docker compose -f infra/compose.postgres.yml --env-file infra/.env.postgres down -v
docker compose -f infra/compose.postgres.yml --env-file infra/.env.postgres up -d
```

Build context is `..` (repo root). The Dockerfiles expect `pyproject.toml`, `uv.lock`, and `flowbook/` at context root. Dependencies via `uv pip install -e ".[full]" --no-sources` (lock file pins versions).

## Usage from another project (flowbook-demo, watt-pmr-api-demo, etc.)

If you use flowbook as a dependency in your own project:

1. **Copy `infra/`** to your project (or use as reference).
2. **Use your own Dockerfile** that matches your project layout:
   - `COPY` your project (e.g. `COPY . ./project`)
   - `pip install -e .` or `pip install flowbook[full]`
   - For Streamlit: get app path via `flowbook.__file__` → `extensions/ui/app.py`
3. **Context**: Use `context: ..` so the build context is your project root.
4. **env files**: Create `.env.api`, `.env.streamlit`, `.env.postgres` in your `infra/` from `.env.example`.

The flowbook Dockerfiles assume the flowbook **source tree** (pyproject.toml + flowbook/). For projects that install flowbook from PyPI or as a dep, adapt the Dockerfile to your structure.
