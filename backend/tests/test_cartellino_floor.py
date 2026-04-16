"""
test_cartellino_floor.py

Verifies that the recommendation always respects the contractual floor
(cartellino) for the (client, SCO) combination.

Scenarios:
 A. Raw pool median < floor  → suggested = floor, requires_deroga = False
 B. Raw pool median = floor  → suggested = floor, requires_deroga = False
 C. Raw pool median > floor  → suggested = median (unclamped), requires_deroga = False
 D. No cartellino exists      → requires_deroga = False, no clamping
"""

from __future__ import annotations

import pytest

from app.domain.pricing import recommend_discount

from .conftest import (
    insert_article,
    insert_cartellino,
    insert_client,
    insert_offer,
    make_db,
)

SCO = "SCO_FL"
CLIENT = "CL_FL"
ARTICLE = "ART_FL"


def _base_db(floor_pct: float | None = None) -> object:
    con = make_db()
    insert_client(con, CLIENT)
    insert_article(con, ARTICLE, SCO)
    if floor_pct is not None:
        insert_cartellino(con, CLIENT, SCO, floor_pct)
    return con


def _fill_pool(con, client: str, article: str, discounts: list[float]) -> None:
    for d in discounts:
        insert_offer(con, client, article, d)


# ── Scenario A: pool median BELOW floor ───────────────────────────────────────

def test_floor_bumps_below_median():
    """
    Pool median = 0.15 (< floor 0.25) → suggested is clamped to 0.25.
    """
    floor = 0.25
    con = _base_db(floor_pct=floor)
    _fill_pool(con, CLIENT, ARTICLE, [0.13, 0.14, 0.15, 0.16, 0.17])  # median = 0.15

    result = recommend_discount(CLIENT, ARTICLE, 10, con)

    assert result["contract_floor_pct"] == pytest.approx(floor)
    assert result["suggested_discount_pct"] == pytest.approx(floor)
    assert result["requires_deroga"] is False


# ── Scenario B: pool median EQUAL to floor ────────────────────────────────────

def test_floor_equal_to_median():
    """Pool median = floor → suggested = floor."""
    floor = 0.22
    con = _base_db(floor_pct=floor)
    _fill_pool(con, CLIENT, ARTICLE, [0.20, 0.21, 0.22, 0.23, 0.24])  # median = 0.22

    result = recommend_discount(CLIENT, ARTICLE, 10, con)

    assert result["suggested_discount_pct"] == pytest.approx(floor, abs=1e-4)
    assert result["requires_deroga"] is False


# ── Scenario C: pool median ABOVE floor ───────────────────────────────────────

def test_floor_does_not_clamp_higher_median():
    """
    Pool median = 0.35 (> floor 0.25) → suggested stays at 0.35,
    floor is surfaced but does not lower the recommendation.
    """
    floor = 0.25
    con = _base_db(floor_pct=floor)
    _fill_pool(con, CLIENT, ARTICLE, [0.33, 0.34, 0.35, 0.36, 0.37])  # median = 0.35

    result = recommend_discount(CLIENT, ARTICLE, 10, con)

    assert result["contract_floor_pct"] == pytest.approx(floor)
    assert result["suggested_discount_pct"] == pytest.approx(0.35, abs=1e-4)
    assert result["requires_deroga"] is False


# ── Scenario D: no cartellino ─────────────────────────────────────────────────

def test_no_cartellino_no_floor():
    """When no cartellino exists, contract_floor_pct is None and no clamping."""
    con = _base_db(floor_pct=None)
    _fill_pool(con, CLIENT, ARTICLE, [0.18, 0.19, 0.20, 0.21, 0.22])  # median = 0.20

    result = recommend_discount(CLIENT, ARTICLE, 10, con)

    assert result["contract_floor_pct"] is None
    assert result["requires_deroga"] is False
    assert result["suggested_discount_pct"] == pytest.approx(0.20, abs=1e-4)
