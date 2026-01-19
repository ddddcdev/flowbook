"""
FastAPI entrypoint:
- Thin HTTP adapter for inspect / build / run
Rule:
- No auth, persistence, or async jobs
- adapters are the only integration point
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.api.app.deps import init_state_for_demo
from apps.api.app.routes.artifacts import router as artifacts_router
from apps.api.app.routes.build import router as build_router
from apps.api.app.routes.inspect import router as inspect_router
from apps.api.app.routes.run import router as run_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_state_for_demo()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(inspect_router)
app.include_router(build_router)
app.include_router(run_router)
app.include_router(artifacts_router)
