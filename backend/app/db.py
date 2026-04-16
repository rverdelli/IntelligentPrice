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
    con = _make_connection()
    try:
        yield con
    finally:
        con.close()
