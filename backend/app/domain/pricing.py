"""
M1 — Pure pricing domain logic.
No FastAPI, no HTTP concerns — only SQL + pandas + arithmetic.

Main entry point: recommend_discount(client_code, article_code, qty, con)
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd

# ── Constants ─────────────────────────────────────────────────────────────────
MIN_POOL = 5
LOOKBACK_DAYS = 1095  # 3-year window for unit_cost / list_price medians

# Cascade step names → data sufficiency levels
_STEP_SUFFICIENCY: dict[str, str] = {
    "cliente_articolo": "high",
    "cliente_sco":       "high",
    "tipo_articolo":     "medium",
    "tipo_sco":          "medium",
    "provincia_sco":     "low",
    "agente_sco":        "low",
    "sco_globale":       "low",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _nanmedian(series: pd.Series) -> Optional[float]:
    """Return median of non-null values, or None if no values."""
    clean = series.dropna()
    if clean.empty:
        return None
    return float(np.nanmedian(clean.values))


def _safe_get(row: pd.Series, col: str) -> Optional[str]:
    """Return value from Series as str, or None if NaN/empty."""
    val = row.get(col)
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    s = str(val).strip()
    return s if s else None


# ── Core function ─────────────────────────────────────────────────────────────

def recommend_discount(
    client_code: str,
    article_code: str,
    qty: float,
    con: sqlite3.Connection,
) -> dict:
    """
    Compute a pricing recommendation for (client, article, qty).

    Args:
        client_code: Codice cliente
        article_code: Codice articolo
        qty: Quantità richiesta (per expected_margin_eur)
        con: SQLite connection (must have normalised marchiol schema)

    Returns:
        Recommendation dict matching RecommendResponse schema.

    Raises:
        ValueError: "Dati insufficienti per l'articolo X" when the article
                    has zero offer history in the last 12 months.
        ValueError: "Cliente non trovato: X" when the client does not exist.
    """

    # ── 1. Resolve article → SCO ───────────────────────────────────────────
    art_df = pd.read_sql_query(
        "SELECT article_code, sco_code FROM articles WHERE article_code = ?",
        con, params=[article_code],
    )
    if art_df.empty:
        raise ValueError(f"Dati insufficienti per l'articolo {article_code}")
    sco_code = str(art_df.iloc[0]["sco_code"]).strip()

    # ── 2. Resolve client metadata ─────────────────────────────────────────
    cli_df = pd.read_sql_query(
        "SELECT * FROM clients WHERE client_code = ?",
        con, params=[client_code],
    )
    if cli_df.empty:
        raise ValueError(f"Cliente non trovato: {client_code}")
    cli = cli_df.iloc[0]

    client_type = _safe_get(cli, "client_type")
    province    = _safe_get(cli, "province")
    agent       = _safe_get(cli, "agent")

    # ── 3. Unit cost & list price (last 12 months, any row_status) ─────────
    cutoff = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
    price_df = pd.read_sql_query(
        """
        SELECT unit_cost, list_price
        FROM   offers
        WHERE  article_code = ?
          AND  offer_date   >= ?
        """,
        con, params=[article_code, cutoff],
    )
    if price_df.empty:
        raise ValueError(f"Dati insufficienti per l'articolo {article_code}")

    unit_cost_used  = float(np.nanmedian(price_df["unit_cost"].dropna().values))
    list_price_used = float(np.nanmedian(price_df["list_price"].dropna().values))

    # ── 4. Load all ACC offers enriched with article/client metadata ───────
    all_acc = pd.read_sql_query(
        """
        SELECT
            o.client_code,
            o.article_code,
            o.discount_pct,
            a.sco_code,
            c.client_type,
            c.province,
            c.agent
        FROM   offers   o
        JOIN   articles a ON o.article_code = a.article_code
        JOIN   clients  c ON o.client_code  = c.client_code
        WHERE  o.row_status  = 'ACC'
          AND  o.discount_pct IS NOT NULL
        """,
        con,
    )

    # ── 5. Fallback cascade ────────────────────────────────────────────────
    trace: list[dict] = []
    used_pool: Optional[pd.DataFrame] = None

    def _run_step(step_name: str, mask: pd.Series) -> None:
        nonlocal used_pool
        pool = all_acc[mask].copy()
        med  = _nanmedian(pool["discount_pct"])
        entry: dict = {
            "step":            step_name,
            "pool_size":       int(len(pool)),
            "median_discount": med,
            "used":            False,
        }
        trace.append(entry)
        if used_pool is None and len(pool) >= MIN_POOL:
            used_pool = pool
            entry["used"] = True

    # Step 1 — Client × Article
    _run_step(
        "cliente_articolo",
        (all_acc["client_code"]  == client_code) &
        (all_acc["article_code"] == article_code),
    )

    # Step 2 — Client × SCO
    _run_step(
        "cliente_sco",
        (all_acc["client_code"] == client_code) &
        (all_acc["sco_code"]    == sco_code),
    )

    # Step 3 — ClientType × Article
    if client_type:
        _run_step(
            "tipo_articolo",
            (all_acc["client_type"]  == client_type) &
            (all_acc["article_code"] == article_code),
        )

    # Step 4 — ClientType × SCO
    if client_type:
        _run_step(
            "tipo_sco",
            (all_acc["client_type"] == client_type) &
            (all_acc["sco_code"]    == sco_code),
        )

    # Step 5 — Province × SCO (only if client has province)
    if province:
        _run_step(
            "provincia_sco",
            (all_acc["province"] == province) &
            (all_acc["sco_code"] == sco_code),
        )

    # Step 6 — Agent × SCO (only if client has agent)
    if agent:
        _run_step(
            "agente_sco",
            (all_acc["agent"]    == agent) &
            (all_acc["sco_code"] == sco_code),
        )

    # Step 7 — SCO global
    _run_step(
        "sco_globale",
        all_acc["sco_code"] == sco_code,
    )

    # ── 6. Determine pool and data sufficiency ─────────────────────────────
    if used_pool is not None:
        used_step       = next(t["step"] for t in trace if t["used"])
        data_sufficiency = _STEP_SUFFICIENCY.get(used_step, "low")

        raw_suggestion = float(np.nanmedian(used_pool["discount_pct"].values))
        min_discount   = float(used_pool["discount_pct"].quantile(0.25))
        max_discount   = float(used_pool["discount_pct"].quantile(0.75))
    else:
        # Last resort: global mean of all ACC offers (any SCO)
        data_sufficiency = "insufficient"
        if all_acc.empty:
            raw_suggestion = 0.0
            min_discount   = 0.0
            max_discount   = 0.0
        else:
            raw_suggestion = float(all_acc["discount_pct"].mean())
            min_discount   = float(all_acc["discount_pct"].quantile(0.25))
            max_discount   = float(all_acc["discount_pct"].quantile(0.75))

    # ── 7. Apply cartellino floor ──────────────────────────────────────────
    contract_floor_pct: Optional[float] = None
    requires_deroga = False

    cart_df = pd.read_sql_query(
        """
        SELECT contract_discount_pct
        FROM   cartellini
        WHERE  client_code = ? AND sco_code = ?
        """,
        con, params=[client_code, sco_code],
    )
    if not cart_df.empty:
        contract_floor_pct = float(cart_df.iloc[0]["contract_discount_pct"])
        if raw_suggestion < contract_floor_pct:
            # Bump suggestion to contractual floor; engine never goes below floor
            suggested_discount = contract_floor_pct
            requires_deroga    = False
        else:
            suggested_discount = raw_suggestion
            requires_deroga    = False
    else:
        suggested_discount = raw_suggestion
        requires_deroga    = False

    # ── 8. Check active promos ─────────────────────────────────────────────
    active_promo: Optional[dict] = None

    promo_df = pd.read_sql_query(
        """
        SELECT pa.promo_id, pa.promo_type
        FROM   promo_articles pa
        JOIN   promo_clients  pc ON pa.promo_id = pc.promo_id
        WHERE  pc.client_code  = ?
          AND  pa.article_code = ?
        LIMIT 1
        """,
        con, params=[client_code, article_code],
    )
    if not promo_df.empty:
        active_promo = {
            "promo_id":   str(promo_df.iloc[0]["promo_id"]),
            "promo_type": str(promo_df.iloc[0]["promo_type"]),
        }
        trace.append({
            "step":            "promo_attiva",
            "pool_size":       0,
            "median_discount": None,
            "used":            False,
            "detail": (
                f"Promo {active_promo['promo_id']}: "
                f"{active_promo['promo_type']} — valutare con il cliente"
            ),
        })

    # ── 9. Compute expected margin ─────────────────────────────────────────
    net_price_suggested = list_price_used * (1.0 - suggested_discount)
    if net_price_suggested > 0:
        expected_margin_pct = (net_price_suggested - unit_cost_used) / net_price_suggested
    else:
        expected_margin_pct = 0.0
    expected_margin_eur = (net_price_suggested - unit_cost_used) * qty

    # ── 10. Return ─────────────────────────────────────────────────────────
    return {
        "suggested_discount_pct": round(suggested_discount, 4),
        "min_discount_pct":       round(min_discount, 4),
        "max_discount_pct":       round(max_discount, 4),
        "contract_floor_pct":     contract_floor_pct,
        "expected_margin_pct":    round(expected_margin_pct, 4),
        "expected_margin_eur":    round(expected_margin_eur, 2),
        "unit_cost_used":         round(unit_cost_used, 4),
        "list_price_used":        round(list_price_used, 4),
        "requires_deroga":        requires_deroga,
        "active_promo":           active_promo,
        "explanation_trace":      trace,
        "data_sufficiency":       data_sufficiency,
    }
