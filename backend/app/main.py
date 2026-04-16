"""
Marchiol Pricing Cockpit — FastAPI application.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api import catalog, clients, pricing

app = FastAPI(
    title="Marchiol Pricing Cockpit",
    description="API per la raccomandazione sconti — prototipo M1",
    version="0.1.0",
)

# Allow all origins for the workshop prototype
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
    return {"status": "ok"}
