"""
Database connection management.
DB_PATH is resolved relative to the project root; tests override get_db().
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Generator

# Project root is two levels above this file (backend/app/db.py → marchiol-pricing/)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = _PROJECT_ROOT / "data" / "marchiol.db"


def _make_connection(path: str | Path = DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    # Enable WAL for better concurrent read performance
    con.execute("PRAGMA journal_mode=WAL")
    return con


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency — yields one SQLite connection per request."""
    from fastapi import HTTPException

    if not DB_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Database non trovato ({DB_PATH}). Esegui: python scripts/ingest.py",
        )

    con = _make_connection()

    # Verify the schema exists (ingest might have failed mid-run)
    try:
        con.execute("SELECT 1 FROM clients LIMIT 1")
    except sqlite3.OperationalError:
        con.close()
        raise HTTPException(
            status_code=503,
            detail="Database vuoto o corrotto. Esegui: python scripts/ingest.py",
        )

    try:
        yield con
    finally:
        con.close()
