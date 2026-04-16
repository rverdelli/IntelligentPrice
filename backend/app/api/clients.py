"""
GET /clients/{client_code}/context
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_db
from app.schemas import CartelliniItem, ClientContext, OfferBrief

router = APIRouter(prefix="/clients", tags=["Clienti"])


@router.get("/{client_code}/context", response_model=ClientContext)
def client_context(
    client_code: str,
    db: sqlite3.Connection = Depends(get_db),
) -> ClientContext:
    """
    Dettaglio cliente: anagrafica + cartellini attivi + ultime 10 offerte.
    """
    client_row = db.execute(
        "SELECT * FROM clients WHERE client_code = ?",
        (client_code,),
    ).fetchone()

    if client_row is None:
        raise HTTPException(status_code=404, detail=f"Cliente non trovato: {client_code}")

    # Detect optional article columns once (may be absent on old ingest)
    _art_cols = {r[1] for r in db.execute("PRAGMA table_info(articles)").fetchall()}
    _sco_desc_inner = "sco_desc"    if "sco_desc"    in _art_cols else "NULL"
    _art_desc       = "a.article_desc" if "article_desc" in _art_cols else "NULL"

    # ── Cartellini ──────────────────────────────────────────────────────────
    cart_rows = db.execute(
        f"""
        SELECT c.client_code, c.sco_code, c.contract_discount_pct, a.sco_desc
        FROM   cartellini c
        LEFT JOIN (
            SELECT DISTINCT sco_code, {_sco_desc_inner} AS sco_desc FROM articles
        ) a ON c.sco_code = a.sco_code
        WHERE  c.client_code = ?
        ORDER BY c.sco_code
        """,
        (client_code,),
    ).fetchall()

    cartellini = [
        CartelliniItem(
            sco_code=r["sco_code"],
            sco_desc=r["sco_desc"] or None,
            contract_discount_pct=float(r["contract_discount_pct"]),
        )
        for r in cart_rows
    ]

    # ── Last 10 offers ──────────────────────────────────────────────────────

    offer_rows = db.execute(
        f"""
        SELECT
            o.offer_num, o.offer_row, o.article_code,
            {_art_desc} AS article_desc,
            o.offer_date, o.qty,
            o.list_price, o.net_price,
            o.discount_pct, o.row_status
        FROM   offers   o
        LEFT JOIN articles a ON o.article_code = a.article_code
        WHERE  o.client_code = ?
        ORDER BY o.offer_date DESC
        LIMIT 10
        """,
        (client_code,),
    ).fetchall()

    recent_offers = [
        OfferBrief(
            offer_num=r["offer_num"],
            offer_row=r["offer_row"],
            article_code=r["article_code"],
            article_desc=r["article_desc"] or None,
            offer_date=r["offer_date"],
            qty=r["qty"],
            list_price=r["list_price"],
            net_price=r["net_price"],
            discount_pct=r["discount_pct"],
            row_status=r["row_status"],
        )
        for r in offer_rows
    ]

    # Convert Row to dict for safe .get() access (client_name may be absent
    # in databases ingested with an older version of ingest.py).
    client_dict = dict(client_row)
    return ClientContext(
        client_code=client_dict["client_code"],
        client_name=client_dict.get("client_name") or None,
        client_type=client_dict.get("client_type") or None,
        branch=client_dict.get("branch") or None,
        city=client_dict.get("city") or None,
        province=client_dict.get("province") or None,
        agent=client_dict.get("agent") or None,
        potential=client_dict.get("potential") or None,
        num_employees=client_dict.get("num_employees"),
        cartellini=cartellini,
        recent_offers=recent_offers,
    )
