"""
Marchiol Pricing Cockpit — FastAPI application.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api import catalog, clients, pricing


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db import DB_PATH
    import logging
    if not DB_PATH.exists():
        logging.warning(
            "DATABASE NON TROVATO: %s — esegui scripts/ingest.py", DB_PATH
        )
    yield


app = FastAPI(
    title="Marchiol Pricing Cockpit",
    description="API per la raccomandazione sconti — prototipo",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog.router)
app.include_router(clients.router)
app.include_router(pricing.router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Sistema"])
def health() -> dict:
    from app.db import DB_PATH
    return {
        "status": "ok",
        "db": str(DB_PATH),
        "db_found": DB_PATH.exists(),
    }

