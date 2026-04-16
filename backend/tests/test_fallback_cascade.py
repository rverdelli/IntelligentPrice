"""
test_fallback_cascade.py

Each of the 7 cascade steps is exercised by a crafted scenario where all
higher-priority pools are empty (or below MIN_POOL).

Steps:
 1. cliente_articolo    — client × article
 2. cliente_sco         — client × SCO
 3. tipo_articolo       — client-type × article
 4. tipo_sco            — client-type × SCO
 5. provincia_sco       — province × SCO
 6. agente_sco          — agent × SCO
 7. sco_globale         — any offer in SCO
"""

from __future__ import annotations

import pytest

from app.domain.pricing import MIN_POOL, recommend_discount

from .conftest import (
    insert_article,
    insert_client,
    insert_offer,
    make_db,
)


def _used_step(result: dict) -> str:
    used = [t for t in result["explanation_trace"] if t["used"]]
    assert len(used) == 1, f"Expected exactly 1 used step, got: {used}"
    return used[0]["step"]


# ── Helpers to add MIN_POOL ACC offers for a given (client, article) set ──────

def _fill(con, clients: list[str], article: str, discounts: list[float]) -> None:
    """Insert one offer per (client, discount) combination."""
    for c in clients:
        for d in discounts:
            insert_offer(con, c, article, d)


# ── Step 1: cliente_articolo ───────────────────────────────────────────────────

def test_step1_uses_client_article():
    """When client has ≥ MIN_POOL ACC offers for the exact article → step 1."""
    con = make_db()
    insert_client(con, "CL1", province="MI", agent="ROSSI")
    insert_article(con, "ART1", "SCO1")
    _fill(con, ["CL1"], "ART1", [0.20, 0.21, 0.22, 0.23, 0.24])

    result = recommend_discount("CL1", "ART1", 10, con)

    assert _used_step(result) == "cliente_articolo"
    assert result["data_sufficiency"] == "high"


# ── Step 2: cliente_sco ────────────────────────────────────────────────────────

def test_step2_uses_client_sco():
    """
    Client has <MIN_POOL offers for ART2, but ≥MIN_POOL for other articles
    in the same SCO (SCO1) → falls to step 2.
    """
    con = make_db()
    insert_client(con, "CL2", province="MI", agent="ROSSI")
    insert_article(con, "ART2", "SCO1")
    insert_article(con, "ART_OTHER", "SCO1")

    # Only 3 offers for the target article
    _fill(con, ["CL2"], "ART2", [0.22, 0.23, 0.24])  # < MIN_POOL
    # But 5 offers for another article in same SCO
    _fill(con, ["CL2"], "ART_OTHER", [0.21, 0.22, 0.23, 0.24, 0.25])  # ≥ MIN_POOL

    result = recommend_discount("CL2", "ART2", 10, con)

    assert _used_step(result) == "cliente_sco"
    assert result["data_sufficiency"] == "high"


# ── Step 3: tipo_articolo ──────────────────────────────────────────────────────

def test_step3_uses_type_article():
    """
    CL3 (Impresa) has <MIN_POOL for (CL3, ART3) and (CL3, SCO1),
    but other Impresa clients have ≥MIN_POOL for ART3 → step 3.
    """
    con = make_db()
    insert_client(con, "CL3", client_type="Impresa", province="MI", agent="ROSSI")
    # Other Impresa clients
    for code in ["CL3B", "CL3C", "CL3D", "CL3E", "CL3F"]:
        insert_client(con, code, client_type="Impresa", province="RM", agent="BIANCHI")
    insert_article(con, "ART3", "SCO1")

    # CL3 has only 2 offers for ART3 and no other SCO1 articles → steps 1+2 fail
    _fill(con, ["CL3"], "ART3", [0.28, 0.29])  # < MIN_POOL

    # Other Impresa clients each have 1 offer → total 5 for Impresa × ART3
    _fill(con, ["CL3B", "CL3C", "CL3D", "CL3E", "CL3F"], "ART3", [0.30])

    result = recommend_discount("CL3", "ART3", 10, con)

    assert _used_step(result) == "tipo_articolo"
    assert result["data_sufficiency"] == "medium"


# ── Step 4: tipo_sco ───────────────────────────────────────────────────────────

def test_step4_uses_type_sco():
    """
    CL4 (OEM) has <MIN_POOL for (CL4, ART4), (CL4, SCO1), (OEM, ART4),
    but OEM clients have ≥MIN_POOL offers for SCO1 in aggregate → step 4.
    """
    con = make_db()
    insert_client(con, "CL4", client_type="OEM", province="MI", agent="ROSSI")
    for code in ["CL4B", "CL4C", "CL4D", "CL4E"]:
        insert_client(con, code, client_type="OEM", province="RM", agent="BIANCHI")

    insert_article(con, "ART4", "SCO1")
    insert_article(con, "ART4B", "SCO1")

    # CL4 has 0 offers → steps 1+2 fail
    # OEM × ART4 has only 2 offers → step 3 fails
    _fill(con, ["CL4B", "CL4C"], "ART4", [0.33])  # only 2 OEM × ART4

    # OEM × SCO1 total: 2 (above) + 4 others on ART4B = 6 ≥ MIN_POOL → step 4
    _fill(con, ["CL4B", "CL4C", "CL4D", "CL4E"], "ART4B", [0.34])  # 4 OEM × SCO1

    result = recommend_discount("CL4", "ART4", 10, con)

    assert _used_step(result) == "tipo_sco"
    assert result["data_sufficiency"] == "medium"


# ── Step 5: provincia_sco ──────────────────────────────────────────────────────

def test_step5_uses_province_sco():
    """
    CL5 (Installatore, province=VE) — no prior offers; type-level pools are
    empty; but 5 other VE clients have offers in SCO2 → step 5.
    """
    con = make_db()
    insert_client(con, "CL5", client_type="Installatore", province="VE", agent="VERDI")
    for code in ["CL5B", "CL5C", "CL5D", "CL5E", "CL5F"]:
        insert_client(con, code, client_type="Rivenditore", province="VE", agent="BIANCHI")

    insert_article(con, "ART5", "SCO2")
    insert_article(con, "ART5B", "SCO2")

    # No Installatore offers at all → steps 1–4 fail
    # VE province × SCO2: 5 offers from different types → step 5
    _fill(con, ["CL5B", "CL5C", "CL5D", "CL5E", "CL5F"], "ART5", [0.27])

    result = recommend_discount("CL5", "ART5", 10, con)

    assert _used_step(result) == "provincia_sco"
    assert result["data_sufficiency"] == "low"


# ── Step 6: agente_sco ─────────────────────────────────────────────────────────

def test_step6_uses_agent_sco():
    """
    CL6 (agent=GIALLI, province=ZZ — no province matches) — province pool
    has < MIN_POOL; but agent GIALLI has ≥ MIN_POOL offers in SCO3 → step 6.
    """
    con = make_db()
    insert_client(con, "CL6", client_type="Installatore", province="ZZ", agent="GIALLI")
    for code in ["CL6B", "CL6C", "CL6D", "CL6E", "CL6F"]:
        insert_client(con, code, client_type="Rivenditore", province="WW", agent="GIALLI")

    insert_article(con, "ART6", "SCO3")

    # No offers for any Installatore or province ZZ → steps 1–5 fail
    # Agent GIALLI × SCO3: 5 offers → step 6
    _fill(con, ["CL6B", "CL6C", "CL6D", "CL6E", "CL6F"], "ART6", [0.29])

    result = recommend_discount("CL6", "ART6", 10, con)

    assert _used_step(result) == "agente_sco"
    assert result["data_sufficiency"] == "low"


# ── Step 7: sco_globale ────────────────────────────────────────────────────────

def test_step7_uses_sco_global():
    """
    All targeted pools fail; but SCO4 has ≥ MIN_POOL offers globally → step 7.
    """
    con = make_db()
    insert_client(con, "CL7", client_type="Quadrista", province="QQ", agent="ZETA")
    # Other clients with different type, province, agent
    for code in ["CL7B", "CL7C", "CL7D", "CL7E", "CL7F"]:
        insert_client(con, code, client_type="OEM", province="XX", agent="ALFA")

    insert_article(con, "ART7", "SCO4")

    # SCO4 global: 5 offers from different clients → step 7
    _fill(con, ["CL7B", "CL7C", "CL7D", "CL7E", "CL7F"], "ART7", [0.31])

    result = recommend_discount("CL7", "ART7", 10, con)

    assert _used_step(result) == "sco_globale"
    assert result["data_sufficiency"] == "low"


# ── Last resort: insufficient ──────────────────────────────────────────────────

def test_step7_insufficient_falls_to_global_mean():
    """
    All cascade pools (incl. SCO global) have < MIN_POOL → data_sufficiency='insufficient',
    result is still returned (not a 422) with the global mean.

    We insert exactly 4 ACC offers in SCO5 (< MIN_POOL=5) from a client
    that shares none of CL8's type/province/agent, so every cascade step
    stays below MIN_POOL and the engine falls through to the last resort.
    """
    con = make_db()
    insert_client(con, "CL8", client_type="Installatore", province="FF", agent="GAMMA")
    insert_client(con, "CL8B", client_type="OEM", province="GG", agent="DELTA")
    insert_article(con, "ART8", "SCO5")
    insert_article(con, "ART8B", "SCO6")  # different SCO — padding the global mean

    # Only 4 offers in SCO5 → strictly below MIN_POOL for step 7
    for d in [0.25, 0.26, 0.27, 0.28]:
        insert_offer(con, "CL8B", "ART8", d)

    # Some offers in a different SCO to give the global mean something to work with
    for d in [0.30, 0.31, 0.32, 0.33, 0.34]:
        insert_offer(con, "CL8B", "ART8B", d)

    result = recommend_discount("CL8", "ART8", 10, con)

    assert result["data_sufficiency"] == "insufficient"
    assert isinstance(result["suggested_discount_pct"], float)
    assert 0.0 <= result["suggested_discount_pct"] <= 1.0
