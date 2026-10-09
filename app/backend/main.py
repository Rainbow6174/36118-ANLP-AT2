"""CrisisLens FastAPI entrypoint (Member 4).

Run locally with:
    uvicorn app.backend.main:app --reload

Step 2 uses SQLite persistence via app/schema.sql. DB path is
CRISISLENS_DB_PATH (default: app/backend/crisislens.db). The schema is
auto-applied on startup if missing.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db, services
from .api import analyse, reports, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.bootstrap()
    services.configure()
    yield


app = FastAPI(title="CrisisLens API", version="1.0.0-integrated", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyse.router, prefix="/api", tags=["analyse"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(search.router, prefix="/api", tags=["search"])


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": app.version,
        "runtime": services.runtime_status(),
    }
