"""
FastAPI sample app for flowbook.

Thin HTTP surface that delegates to flowbook.engine.
This is a reference implementation; project-specific APIs should
copy and extend this app.
"""

from __future__ import annotations

from fastapi import FastAPI

from flowbook.extensions.api.routes.artifacts import router as artifacts_router
from flowbook.extensions.api.routes.configs import router as configs_router
from flowbook.extensions.api.routes.export import router as export_router
from flowbook.extensions.api.routes.import_ import router as import_router
from flowbook.extensions.api.routes.inspect import router as inspect_router

app = FastAPI(title="flowbook-api", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(inspect_router)
app.include_router(import_router)
app.include_router(export_router)
app.include_router(artifacts_router)
app.include_router(configs_router)
