"""
test_promo_detection.py

Verifies that active promos are correctly detected and surfaced in the
recommendation response (but NOT automatically applied to the discount).

Scenarios:
 A. Client and article both in the promo  → active_promo is populated
 B. Client in promo but article not       → active_promo is None
 C. Article in promo but client not       → active_promo is None
 D. No promos at all                      → active_promo is None
 E. Promo is detected but discount is NOT auto-applied
"""

from __future__ import annotations

import pytest

from app.domain.pricing import recommend_discount

from .conftest import (
    insert_article,
    insert_client,
    insert_offer,
    insert_promo,
    make_db,
)

SCO = "SCO_PROMO"
CLIENT = "CL_PROMO"
ARTICLE = "ART_PROMO"
PROMO_ID = "P_TEST"
PROMO_TYPE = "Sconto Speciale"


def _base_db() -> object:
    con = make_db()
    insert_client(con, CLIENT)
    insert_article(con, ARTICLE, SCO)
    # Enough offers for a pool (step 1 will succeed)
    for d in [0.20, 0.21, 0.22, 0.23, 0.24]:
        insert_offer(con, CLIENT, ARTICLE, d)
    return con


# ── Scenario A: both client and article in promo ──────────────────────────────

def test_promo_detected_when_client_and_article_match():
    """Client and article both enrolled → active_promo is populated."""
    con = _base_db()
    insert_promo(con, PROMO_ID, PROMO_TYPE, ARTICLE, [CLIENT])

    result = recommend_discount(CLIENT, ARTICLE, 5, con)

    assert result["active_promo"] is not None
    assert result["active_promo"]["promo_id"] == PROMO_ID
    assert result["active_promo"]["promo_type"] == PROMO_TYPE


def test_promo_appears_in_explanation_trace():
    """Active promo step appears in explanation_trace."""
    con = _base_db()
    insert_promo(con, PROMO_ID, PROMO_TYPE, ARTICLE, [CLIENT])

    result = recommend_discount(CLIENT, ARTICLE, 5, con)

    promo_steps = [t for t in result["explanation_trace"] if t["step"] == "promo_attiva"]
    assert len(promo_steps) == 1
    assert "detail" in promo_steps[0]


# ── Scenario B: client in promo but article not ───────────────────────────────

def test_promo_not_detected_when_article_not_in_promo():
    """Client is in the promo but a DIFFERENT article → no promo for our article."""
    con = _base_db()
    insert_article(con, "OTHER_ART", SCO)
    # Promo covers OTHER_ART, not ARTICLE
    insert_promo(con, PROMO_ID, PROMO_TYPE, "OTHER_ART", [CLIENT])

    result = recommend_discount(CLIENT, ARTICLE, 5, con)

    assert result["active_promo"] is None


# ── Scenario C: article in promo but client not ───────────────────────────────

def test_promo_not_detected_when_client_not_enrolled():
    """Article is in the promo but a DIFFERENT client → no promo for our client."""
    con = _base_db()
    insert_client(con, "OTHER_CLIENT")
    # Promo covers ARTICLE but only for OTHER_CLIENT
    insert_promo(con, PROMO_ID, PROMO_TYPE, ARTICLE, ["OTHER_CLIENT"])

    result = recommend_discount(CLIENT, ARTICLE, 5, con)

    assert result["active_promo"] is None


# ── Scenario D: no promos at all ──────────────────────────────────────────────

def test_no_promo_when_tables_empty():
    """No promos in DB → active_promo is None."""
    con = _base_db()
    # promo tables are empty by default in make_db()

    result = recommend_discount(CLIENT, ARTICLE, 5, con)

    assert result["active_promo"] is None
    promo_steps = [t for t in result["explanation_trace"] if t["step"] == "promo_attiva"]
    assert len(promo_steps) == 0


# ── Scenario E: promo does NOT auto-apply discount ────────────────────────────

def test_promo_does_not_change_suggested_discount():
    """
    Discount recommendation must be the same whether or not a promo is active
    (promos are surfaced for the salesperson to decide, not auto-applied).
    """
    # Without promo
    con_no_promo = _base_db()
    result_no = recommend_discount(CLIENT, ARTICLE, 5, con_no_promo)

    # With promo
    con_promo = _base_db()
    insert_promo(con_promo, PROMO_ID, PROMO_TYPE, ARTICLE, [CLIENT])
    result_yes = recommend_discount(CLIENT, ARTICLE, 5, con_promo)

    assert result_no["suggested_discount_pct"] == pytest.approx(
        result_yes["suggested_discount_pct"], abs=1e-9
    )
