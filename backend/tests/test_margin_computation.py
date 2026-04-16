"""
test_margin_computation.py

Verifies that margin arithmetic is correct to ≥ 2 decimal places.

Formulas:
  net_price_suggested   = list_price_used × (1 − suggested_discount_pct)
  expected_margin_pct   = (net_price_suggested − unit_cost_used) / net_price_suggested
  expected_margin_eur   = (net_price_suggested − unit_cost_used) × qty
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

SCO = "SCO_MARGIN"
CLIENT = "CL_MARGIN"
ARTICLE = "ART_MARGIN"

# Controlled prices — easy to verify by hand
LIST_PRICE = 10.0
UNIT_COST  = 6.0
DISCOUNT   = 0.20   # median will be exactly this when all 5 offers share it


def _base_db() -> object:
    con = make_db()
    insert_client(con, CLIENT)
    insert_article(con, ARTICLE, SCO)
    # Five identical offers so median = DISCOUNT exactly
    for _ in range(5):
        insert_offer(
            con, CLIENT, ARTICLE, DISCOUNT,
            list_price=LIST_PRICE, unit_cost=UNIT_COST,
        )
    return con


# ── Margin percentage ─────────────────────────────────────────────────────────

def test_expected_margin_pct_correct():
    """
    net_price = 10 × (1 - 0.20) = 8.00
    expected_margin_pct = (8.00 - 6.00) / 8.00 = 0.25
    """
    con = _base_db()
    result = recommend_discount(CLIENT, ARTICLE, 1, con)

    expected = (LIST_PRICE * (1 - DISCOUNT) - UNIT_COST) / (LIST_PRICE * (1 - DISCOUNT))
    assert result["expected_margin_pct"] == pytest.approx(expected, abs=0.01)


# ── Margin EUR — qty = 1 ──────────────────────────────────────────────────────

def test_expected_margin_eur_qty_1():
    """
    net_price = 8.00, unit_cost = 6.00 → margin = 2.00 EUR per unit
    qty = 1 → expected_margin_eur = 2.00
    """
    con = _base_db()
    result = recommend_discount(CLIENT, ARTICLE, 1, con)

    expected_eur = (LIST_PRICE * (1 - DISCOUNT) - UNIT_COST) * 1
    assert result["expected_margin_eur"] == pytest.approx(expected_eur, abs=0.01)


# ── Margin EUR — qty = 100 ────────────────────────────────────────────────────

def test_expected_margin_eur_qty_100():
    """
    margin per unit = 2.00 EUR → qty = 100 → expected_margin_eur = 200.00
    """
    con = _base_db()
    result = recommend_discount(CLIENT, ARTICLE, 100, con)

    expected_eur = (LIST_PRICE * (1 - DISCOUNT) - UNIT_COST) * 100
    assert result["expected_margin_eur"] == pytest.approx(expected_eur, abs=0.01)


# ── unit_cost_used and list_price_used correctness ────────────────────────────

def test_unit_cost_and_list_price_used():
    """
    unit_cost_used and list_price_used should be the medians of
    the offers' unit_cost and list_price respectively.
    """
    con = _base_db()
    result = recommend_discount(CLIENT, ARTICLE, 1, con)

    assert result["unit_cost_used"]  == pytest.approx(UNIT_COST,  abs=1e-4)
    assert result["list_price_used"] == pytest.approx(LIST_PRICE, abs=1e-4)


# ── Zero-margin edge case ─────────────────────────────────────────────────────

def test_margin_zero_when_cost_equals_net():
    """
    When unit_cost == net_price → expected_margin_pct = 0.0, eur = 0.0.
    """
    con = make_db()
    insert_client(con, "CL_ZM")
    insert_article(con, "ART_ZM", "SCO_ZM")
    lp = 10.0
    uc = 8.0
    disc = 0.20  # net = 8.0 = unit_cost → zero margin
    for _ in range(5):
        insert_offer(con, "CL_ZM", "ART_ZM", disc, list_price=lp, unit_cost=uc)

    result = recommend_discount("CL_ZM", "ART_ZM", 10, con)

    assert result["expected_margin_pct"] == pytest.approx(0.0, abs=0.01)
    assert result["expected_margin_eur"] == pytest.approx(0.0, abs=0.01)


# ── Varying prices: median is used, not mean ─────────────────────────────────

def test_uses_median_not_mean_for_prices():
    """
    Insert offers with varying list prices: [8, 9, 10, 11, 100].
    Median = 10.0, mean = 27.6. list_price_used should be 10.0.
    """
    con = make_db()
    insert_client(con, "CL_MED")
    insert_article(con, "ART_MED", "SCO_MED")
    prices = [8.0, 9.0, 10.0, 11.0, 100.0]
    for p in prices:
        insert_offer(con, "CL_MED", "ART_MED", 0.20, list_price=p, unit_cost=5.0)

    result = recommend_discount("CL_MED", "ART_MED", 1, con)

    assert result["list_price_used"] == pytest.approx(10.0, abs=1e-4)
