"""
test_insufficient_data.py

Verifies HTTP 422 behaviour when an article has no offer history in the
last 12 months (the pricing engine cannot compute unit_cost / list_price).
"""

from __future__ import annotations

import pytest

from app.domain.pricing import recommend_discount

from .conftest import (
    insert_article,
    insert_client,
    insert_offer,
    make_db,
)

# ── No offers at all for the article ──────────────────────────────────────────

def test_article_with_zero_offers_raises():
    """Article exists in catalogue but has no offers → ValueError."""
    con = make_db()
    insert_client(con, "CL_INSUF")
    insert_article(con, "ART_NEW", "SCO_X")

    with pytest.raises(ValueError, match="Dati insufficienti per l'articolo ART_NEW"):
        recommend_discount("CL_INSUF", "ART_NEW", 5, con)


# ── Article not in catalogue at all ───────────────────────────────────────────

def test_article_not_in_catalogue_raises():
    """Article code not found in articles table → ValueError."""
    con = make_db()
    insert_client(con, "CL_INSUF2")
    # No article inserted

    with pytest.raises(ValueError, match="Dati insufficienti per l'articolo GHOST"):
        recommend_discount("CL_INSUF2", "GHOST", 1, con)


# ── Client not found ──────────────────────────────────────────────────────────

def test_unknown_client_raises():
    """Client code not in clients table → ValueError about cliente."""
    con = make_db()
    insert_article(con, "ART_OK", "SCO_Y")
    insert_offer(con, "SOMEONE", "ART_OK", 0.20, offer_date="2025-10-01")
    # Insert SOMEONE as a client so the offer's article has history
    insert_client(con, "SOMEONE")

    with pytest.raises(ValueError, match="Cliente non trovato: NOBODY"):
        recommend_discount("NOBODY", "ART_OK", 1, con)


# ── Offers exist but are all older than 12 months ─────────────────────────────

def test_article_with_only_old_offers_raises():
    """
    Article has offers but ALL are from more than 12 months ago
    (offer_date 2020-01-01) → unit_cost_used cannot be computed → ValueError.
    """
    con = make_db()
    insert_client(con, "CL_OLD")
    insert_article(con, "ART_OLD", "SCO_Z")
    # Insert 5 offers with old dates (well outside the 12-month window)
    for _ in range(5):
        insert_offer(con, "CL_OLD", "ART_OLD", 0.20, offer_date="2020-01-15")

    with pytest.raises(ValueError, match="Dati insufficienti per l'articolo ART_OLD"):
        recommend_discount("CL_OLD", "ART_OLD", 5, con)
