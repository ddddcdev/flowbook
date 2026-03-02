"""
FastAPI sample app for flowbook.

Thin HTTP surface that delegates to flowbook.engine.
This is a reference implementation; project-specific APIs should
copy and extend this app.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from flowbook.core.logging import configure_logging
from flowbook.extensions.api.extensions import discover_api_extensions
from flowbook.extensions.api.routes.artifacts import router as artifacts_router
from flowbook.extensions.api.routes.configs import router as configs_router
from flowbook.extensions.api.routes.entities import router as entities_router
from flowbook.extensions.api.routes.export import router as export_router
from flowbook.extensions.api.routes.import_ import router as import_router
from flowbook.extensions.api.routes.inspect import router as inspect_router
from flowbook.extensions.api.routes.results import router as results_router
from flowbook.extensions.api.routes.runs import router as runs_router
from flowbook.extensions.api.routes.steps import router as steps_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


app = FastAPI(title="flowbook-api", version="0.1.0a6", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(inspect_router)
app.include_router(import_router)
app.include_router(export_router)
app.include_router(artifacts_router)
app.include_router(configs_router)
app.include_router(entities_router)
app.include_router(results_router)
app.include_router(runs_router)
app.include_router(steps_router)

discover_api_extensions(app)
