"""
test_snapshot.py

Verifies determinism: same input always produces the same output.
Also smoke-tests a real (client, article) pair from the real marchiol.db.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.domain.pricing import recommend_discount

from .conftest import (
    insert_article,
    insert_client,
    insert_offer,
    make_db,
)

# ── Determinism (in-memory DB) ────────────────────────────────────────────────

def test_recommend_is_deterministic():
    """
    Calling recommend_discount twice with the same in-memory DB and the
    same arguments must return bitwise-identical dicts.
    """
    con = make_db()
    insert_client(con, "CL_DET")
    insert_article(con, "ART_DET", "SCO_DET")
    for d in [0.20, 0.21, 0.22, 0.23, 0.24]:
        insert_offer(con, "CL_DET", "ART_DET", d)

    result1 = recommend_discount("CL_DET", "ART_DET", 10, con)
    result2 = recommend_discount("CL_DET", "ART_DET", 10, con)

    assert result1 == result2


def test_recommend_deterministic_across_fresh_connections():
    """
    Two fresh in-memory DBs with identical data must produce identical results.
    """
    def _make() -> sqlite3.Connection:
        con = make_db()
        insert_client(con, "CL_X")
        insert_article(con, "ART_X", "SCO_X")
        for d in [0.25, 0.26, 0.27, 0.28, 0.29]:
            insert_offer(con, "CL_X", "ART_X", d, list_price=50.0, unit_cost=30.0)
        return con

    r1 = recommend_discount("CL_X", "ART_X", 5, _make())
    r2 = recommend_discount("CL_X", "ART_X", 5, _make())

    assert r1 == r2


# ── Snapshot values (in-memory DB) ────────────────────────────────────────────

def test_snapshot_known_values():
    """
    Controlled dataset with known-exact output — acts as a regression snapshot.

    Setup:
      - Client CL_SNAP (Installatore, MI, agent SNAP)
      - Article ART_SNAP (SCO_SNAP), list=10.0, cost=6.0
      - 5 ACC offers with discounts [0.20, 0.21, 0.22, 0.23, 0.24], qty=10
      - Cartellino floor 0.15 (below pool median → no clamping)

    Expected:
      suggested_discount_pct = median([0.20, 0.21, 0.22, 0.23, 0.24]) = 0.22
      net_price = 10.0 × (1 - 0.22) = 7.80
      expected_margin_pct = (7.80 - 6.00) / 7.80 = 0.2308 (rounded to 4dp)
      expected_margin_eur = (7.80 - 6.00) × 10 = 18.00
    """
    from .conftest import insert_cartellino

    con = make_db()
    insert_client(con, "CL_SNAP")
    insert_article(con, "ART_SNAP", "SCO_SNAP")
    insert_cartellino(con, "CL_SNAP", "SCO_SNAP", 0.15)
    for d in [0.20, 0.21, 0.22, 0.23, 0.24]:
        insert_offer(con, "CL_SNAP", "ART_SNAP", d, list_price=10.0, unit_cost=6.0)

    result = recommend_discount("CL_SNAP", "ART_SNAP", 10, con)

    assert result["suggested_discount_pct"] == pytest.approx(0.22, abs=1e-4)
    assert result["contract_floor_pct"] == pytest.approx(0.15, abs=1e-4)
    assert result["requires_deroga"] is False
    assert result["expected_margin_pct"] == pytest.approx(0.2308, abs=0.001)
    assert result["expected_margin_eur"] == pytest.approx(18.0, abs=0.01)
    assert result["data_sufficiency"] == "high"
    assert result["active_promo"] is None


# ── Real-DB smoke test ────────────────────────────────────────────────────────

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "marchiol.db"


@pytest.mark.skipif(not _DB_PATH.exists(), reason="marchiol.db not found — run make ingest first")
def test_real_db_smoke_c001_a001():
    """
    C001 / A001 from the real ingested DB — must return a valid recommendation.
    This is the integration smoke test required by M1.3.
    """
    con = sqlite3.connect(str(_DB_PATH))
    con.row_factory = sqlite3.Row

    result = recommend_discount("C001", "A001", 10, con)
    con.close()

    assert isinstance(result["suggested_discount_pct"], float)
    assert 0.0 < result["suggested_discount_pct"] < 1.0
    assert result["data_sufficiency"] in ("high", "medium", "low", "insufficient")
    assert isinstance(result["explanation_trace"], list)
    assert len(result["explanation_trace"]) > 0
    assert result["list_price_used"] > 0
    assert result["unit_cost_used"] > 0
