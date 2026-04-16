"""
Shared test fixtures and helpers.

All tests use in-memory SQLite databases with controlled, deterministic data
so they never depend on the real marchiol.db file.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

import pytest

# ── Schema DDL ─────────────────────────────────────────────────────────────────
_DDL = """
CREATE TABLE clients (
    client_code   TEXT PRIMARY KEY,
    client_type   TEXT,
    branch        TEXT,
    client_name   TEXT,
    potential     TEXT,
    num_employees REAL,
    city          TEXT,
    province      TEXT,
    agent         TEXT
);

CREATE TABLE articles (
    article_code TEXT,
    sco_code     TEXT,
    sco_desc     TEXT,
    article_desc TEXT
);

CREATE TABLE offers (
    offer_num    TEXT,
    offer_row    TEXT,
    client_code  TEXT,
    article_code TEXT,
    offer_date   TEXT,
    qty          REAL,
    list_price   REAL,
    net_price    REAL,
    unit_cost    REAL,
    row_status   TEXT,
    discount_pct REAL,
    margin_pct   REAL
);

CREATE TABLE cartellini (
    client_code          TEXT,
    sco_code             TEXT,
    contract_discount_pct REAL
);

CREATE TABLE promo_articles (
    promo_id    TEXT,
    promo_type  TEXT,
    article_code TEXT,
    amount      REAL,
    currency    TEXT,
    multiplier  REAL,
    unit        TEXT
);

CREATE TABLE promo_clients (
    promo_id    TEXT,
    client_code TEXT
);
"""

_COUNTER = 0


def _uid() -> str:
    global _COUNTER
    _COUNTER += 1
    return f"O{_COUNTER:06d}"


def make_db() -> sqlite3.Connection:
    """Return a fresh in-memory SQLite connection with the marchiol schema."""
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(_DDL)
    return con


def insert_client(
    con: sqlite3.Connection,
    client_code: str,
    client_type: str = "Installatore",
    province: Optional[str] = "MI",
    agent: Optional[str] = "ROSSI",
    city: str = "Milano",
) -> None:
    con.execute(
        """INSERT INTO clients
           (client_code, client_type, branch, client_name, potential,
            num_employees, city, province, agent)
           VALUES (?, ?, 'Filiale Test', ?, NULL, NULL, ?, ?, ?)""",
        (client_code, client_type, f"Cliente {client_code}", city, province, agent),
    )


def insert_article(
    con: sqlite3.Connection,
    article_code: str,
    sco_code: str = "SCO_T",
    sco_desc: str = "Categoria Test",
    article_desc: Optional[str] = None,
) -> None:
    con.execute(
        "INSERT INTO articles VALUES (?, ?, ?, ?)",
        (article_code, sco_code, sco_desc, article_desc or f"Articolo {article_code}"),
    )


def insert_offer(
    con: sqlite3.Connection,
    client_code: str,
    article_code: str,
    discount: float,
    status: str = "ACC",
    list_price: float = 10.0,
    unit_cost: float = 6.0,
    offer_date: str = "2025-10-01",
) -> None:
    net = round(list_price * (1.0 - discount), 6)
    margin = round((net - unit_cost) / net, 6) if net > 0 else 0.0
    con.execute(
        """INSERT INTO offers
           (offer_num, offer_row, client_code, article_code,
            offer_date, qty, list_price, net_price, unit_cost,
            row_status, discount_pct, margin_pct)
           VALUES (?, 1, ?, ?, ?, 10, ?, ?, ?, ?, ?, ?)""",
        (_uid(), client_code, article_code, offer_date,
         list_price, net, unit_cost, status,
         round(discount, 6), round(margin, 6)),
    )


def insert_cartellino(
    con: sqlite3.Connection,
    client_code: str,
    sco_code: str,
    floor_pct: float,
) -> None:
    con.execute(
        "INSERT INTO cartellini VALUES (?, ?, ?)",
        (client_code, sco_code, floor_pct),
    )


def insert_promo(
    con: sqlite3.Connection,
    promo_id: str,
    promo_type: str,
    article_code: str,
    client_codes: list[str],
) -> None:
    con.execute(
        "INSERT INTO promo_articles VALUES (?, ?, ?, 10.0, 'EUR', 1.0, 'PZ')",
        (promo_id, promo_type, article_code),
    )
    for cc in client_codes:
        con.execute("INSERT INTO promo_clients VALUES (?, ?)", (promo_id, cc))
