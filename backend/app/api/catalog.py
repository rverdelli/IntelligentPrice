"""
GET /catalog/clients  — search clients
GET /catalog/articles — search articles
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.db import get_db
from app.schemas import ArticleBrief, ClientBrief

router = APIRouter(prefix="/catalog", tags=["Catalogo"])


def _client_name_expr(db: sqlite3.Connection) -> str:
    """Return the SQL expression to use for the client name column.

    If the ``client_name`` column is absent (database ingested with an older
    version of ingest.py), fall back to ``client_code`` so queries don't crash.
    """
    cols = {r[1] for r in db.execute("PRAGMA table_info(clients)").fetchall()}
    return "client_name" if "client_name" in cols else "client_code"


@router.get("/clients", response_model=list[ClientBrief])
def list_clients(
    search: Optional[str] = Query(default=None, description="Cerca per codice, nome, città o provincia"),
    limit: int = Query(default=20, ge=1, le=200),
    db: sqlite3.Connection = Depends(get_db),
) -> list[ClientBrief]:
    """Ricerca clienti — restituisce codice, nome, tipo, provincia."""
    name_col = _client_name_expr(db)

    if search:
        like = f"%{search.strip()}%"
        name_filter = f"OR   {name_col} LIKE ?" if name_col != "client_code" else ""
        rows = db.execute(
            f"""
            SELECT client_code, {name_col} AS client_name, client_type, branch, city, province
            FROM   clients
            WHERE  client_code LIKE ?
              {name_filter}
              OR   city        LIKE ?
              OR   province    LIKE ?
            ORDER BY client_code
            LIMIT ?
            """,
            (like, like, like, like, limit) if name_col != "client_code" else (like, like, like, limit),
        ).fetchall()
    else:
        rows = db.execute(
            f"""
            SELECT client_code, {name_col} AS client_name, client_type, branch, city, province
            FROM   clients
            ORDER BY client_code
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        ClientBrief(
            client_code=r["client_code"],
            client_name=r["client_name"] or None,
            client_type=r["client_type"] or None,
            branch=r["branch"] or None,
            city=r["city"] or None,
            province=r["province"] or None,
        )
        for r in rows
    ]


@router.get("/articles", response_model=list[ArticleBrief])
def list_articles(
    search: Optional[str] = Query(default=None, description="Cerca per codice, descrizione o SCO"),
    limit: int = Query(default=20, ge=1, le=200),
    db: sqlite3.Connection = Depends(get_db),
) -> list[ArticleBrief]:
    """Ricerca articoli — restituisce codice, descrizione, SCO."""
    if search:
        like = f"%{search.strip()}%"
        rows = db.execute(
            """
            SELECT article_code, article_desc, sco_code, sco_desc
            FROM   articles
            WHERE  article_code  LIKE ?
              OR   article_desc  LIKE ?
              OR   sco_code      LIKE ?
              OR   sco_desc      LIKE ?
            ORDER BY article_code
            LIMIT ?
            """,
            (like, like, like, like, limit),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT article_code, article_desc, sco_code, sco_desc
            FROM   articles
            ORDER BY article_code
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        ArticleBrief(
            article_code=r["article_code"],
            article_desc=r["article_desc"] or None,
            sco_code=r["sco_code"],
            sco_desc=r["sco_desc"] or None,
        )
        for r in rows
    ]
