"""
M0: CSV → SQLite ingestion pipeline for Marchiol pricing data.

Usage:
    python scripts/ingest.py [--db data/marchiol.db] [--raw data/raw]

Reads 7 CSVs in Italian format (semicolon delimiter, comma decimal separator,
UTF-8 BOM), normalises column names, derives discount_pct and margin_pct,
creates indexes, and prints a data-quality report.

Idempotent: drops and recreates all tables on each run.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--db", default="data/marchiol.db")
parser.add_argument("--raw", default="data/raw")
args = parser.parse_args()

DB_PATH = Path(args.db)
RAW_DIR = Path(args.raw)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def read_italian_csv(path: Path, **kwargs) -> pd.DataFrame:
    """Read a semicolon-delimited Italian CSV (comma decimals).

    Tries encodings in order: utf-8-sig → cp1252 → latin-1.
    Italian Excel exports are often cp1252 (e.g. 'n° promo' contains 0xb0).
    """
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            df = pd.read_csv(
                path,
                sep=";",
                decimal=",",
                encoding=enc,
                dtype=str,
                **kwargs,
            )
            return df
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError(f"Impossibile leggere {path}: encoding non riconosciuto")


def to_float(series: pd.Series) -> pd.Series:
    """Convert a string series with optional comma decimals to float."""
    return pd.to_numeric(
        series.str.replace(",", ".", regex=False).str.strip(),
        errors="coerce",
    )


def parse_italian_date(series: pd.Series) -> pd.Series:
    """Parse DD/MM/YYYY date strings."""
    return pd.to_datetime(series, format="%d/%m/%Y", errors="coerce").dt.date.astype(str)


def warn(msg: str) -> None:
    print(f"[WARN]  {msg}", file=sys.stderr)


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def strip_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing whitespace from all column names.

    Italian Excel exports often pad column headers with spaces.
    """
    df.columns = [c.strip() for c in df.columns]
    return df


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first column name from *candidates* that exists in *df*.

    Comparison is done after stripping whitespace from both the DataFrame
    column names and the candidate strings, so minor spacing differences
    in the source CSV are tolerated.
    """
    stripped_map = {c.strip(): c for c in df.columns}
    for candidate in candidates:
        match = stripped_map.get(candidate.strip())
        if match is not None:
            return match
    return None


# ── Read CSVs ─────────────────────────────────────────────────────────────────
section("Reading source CSVs")

raw_files = {
    "OFFERTE_2025":        RAW_DIR / "OFFERTE_2025.csv",
    "ODV_2025_v2":         RAW_DIR / "ODV_2025_v2.csv",
    "ANAG_CLIENTI":        RAW_DIR / "ANAG_CLIENTI.csv",
    "ANAG_ARTICOLI":       RAW_DIR / "ANAG_ARTICOLI.csv",
    "CARTELLINI":          RAW_DIR / "CARTELLINI.csv",
    "PROMOZIONI_ARTICOLI": RAW_DIR / "PROMOZIONI-ARTICOLI.csv",
    "PROMOZIONI_CLIENTI":  RAW_DIR / "PROMOZIONI-CLIENTI.csv",
}

for name, path in raw_files.items():
    if not path.exists():
        sys.exit(f"[ERROR] Required CSV not found: {path}")
    print(f"  {name}: {path}")

# ── ANAG_CLIENTI → clients ────────────────────────────────────────────────────
raw_clients = read_italian_csv(raw_files["ANAG_CLIENTI"])
strip_columns(raw_clients)
print(f"  ANAG_CLIENTI columns found: {list(raw_clients.columns)}")

# "Ragione Sociale" column name varies widely across Italian ERP exports.
rag_col = find_column(raw_clients, [
    # Gamma Enterprise variants
    "Rag. Sociale", "Rag.Sociale", "Rag Sociale", "Descrcli", "Descr.cli",
    # Generic Italian ERP
    "Ragione Sociale", "Ragione sociale", "RagSociale", "RagSoc", "Ragsoc",
    "Denominazione", "Nome/Rag.Soc.", "Descr. Cli.", "Descr.Cli",
    # Lowercase
    "rag. sociale", "rag.sociale", "ragione sociale", "denominazione",
])

# Last resort: if no candidate matched, look for any unmapped column whose
# values are long strings — almost certainly the company name field.
_already_mapped = {"Codcli", "Descrtipcli", "Descrfil", "Potenziale",
                   "Numdip", "Provincia", "Descrage", "Città", "Citta", "City"}
if rag_col is None:
    for col in raw_clients.columns:
        if col in _already_mapped:
            continue
        sample = raw_clients[col].dropna().head(20)
        if len(sample) == 0:
            continue
        avg_len = sample.astype(str).str.len().mean()
        if avg_len >= 8:  # company names are typically ≥ 8 chars
            rag_col = col
            warn(
                f"Auto-detected 'Rag. Sociale' as column '{col}' "
                f"(avg value length {avg_len:.1f}). "
                f"Verify sample: {sample.head(3).tolist()}"
            )
            break
_client_rename: dict[str, str] = {
    "Codcli":      "client_code",
    "Descrtipcli": "client_type",
    "Descrfil":    "branch",
    "Potenziale":  "potential",
    "Numdip":      "num_employees",
    "Provincia":   "province",
    "Descrage":    "agent",
}
# City column also uses accented character; strip_columns already stripped it.
city_col = find_column(raw_clients, ["Città", "Citta", "City"])
if city_col:
    _client_rename[city_col] = "city"
else:
    warn("Column for 'Città' not found in ANAG_CLIENTI.")

if rag_col:
    _client_rename[rag_col] = "client_name"
else:
    warn(
        f"Column for 'Rag. Sociale' not found in ANAG_CLIENTI. "
        f"Available columns: {list(raw_clients.columns)}"
    )

clients = raw_clients.rename(columns=_client_rename)
# Ensure client_name exists even when the source column was absent
if "client_name" not in clients.columns:
    clients["client_name"] = pd.NA

clients["client_code"] = clients["client_code"].str.strip()
# Replace empty strings with NaN for proper null handling
clients.replace(r"^\s*$", pd.NA, regex=True, inplace=True)
clients["num_employees"] = pd.to_numeric(clients["num_employees"], errors="coerce")

# ── ANAG_ARTICOLI → articles ──────────────────────────────────────────────────
raw_articles = read_italian_csv(raw_files["ANAG_ARTICOLI"])
strip_columns(raw_articles)
print(f"  ANAG_ARTICOLI columns found: {list(raw_articles.columns)}")

art_desc_col = find_column(raw_articles, [
    "Descart", "Descr.art.", "Descr. art.", "Descrizione articolo",
    "Descr art", "Descrizione Art", "desc art",
])
sco_desc_col = find_column(raw_articles, [
    "Descrsco", "Descr.sco", "Descr. sco", "Descrizione SCO",
    "Descr SCO", "Descrizione Sco", "desc sco",
])
_art_rename: dict[str, str] = {
    "Codart": "article_code",
    "Codsco": "sco_code",
}
if art_desc_col:
    _art_rename[art_desc_col] = "article_desc"
else:
    warn(
        f"Column for 'Descart' (article_desc) not found in ANAG_ARTICOLI. "
        f"Available columns: {list(raw_articles.columns)}"
    )
if sco_desc_col:
    _art_rename[sco_desc_col] = "sco_desc"
else:
    warn(
        f"Column for 'Descrsco' (sco_desc) not found in ANAG_ARTICOLI. "
        f"Available columns: {list(raw_articles.columns)}"
    )

articles = raw_articles.rename(columns=_art_rename)
if "article_desc" not in articles.columns:
    articles["article_desc"] = pd.NA
if "sco_desc" not in articles.columns:
    articles["sco_desc"] = pd.NA

articles["article_code"] = articles["article_code"].str.strip()
articles.replace(r"^\s*$", pd.NA, regex=True, inplace=True)

# ── OFFERTE_2025 → offers ─────────────────────────────────────────────────────
raw_offers = read_italian_csv(raw_files["OFFERTE_2025"])
strip_columns(raw_offers)
offers = raw_offers.rename(columns={
    "Numoff":          "offer_num",
    "Rigoff":          "offer_row",
    "Codcli":          "client_code",
    "Codart":          "article_code",
    "Data_Offerta":    "offer_date",
    "Qtaoff":          "qty",
    "List_Appl_Unit":  "list_price",
    "Prz_Netto_Unit":  "net_price",
    "Cdv_Unit":        "unit_cost",
    "Stato_Riga_Off":  "row_status",
})
offers["client_code"]  = offers["client_code"].str.strip()
offers["article_code"] = offers["article_code"].str.strip()
offers["row_status"]   = offers["row_status"].str.strip()
offers["offer_date"]   = parse_italian_date(offers["offer_date"])
for col in ("qty", "list_price", "net_price", "unit_cost"):
    offers[col] = to_float(offers[col])

# Derived columns
offers["discount_pct"] = (
    (offers["list_price"] - offers["net_price"]) / offers["list_price"]
).round(4)
offers["margin_pct"] = (
    (offers["net_price"] - offers["unit_cost"]) / offers["net_price"]
).round(4)
# Guard against division by zero / invalid prices
offers.loc[offers["list_price"] == 0, "discount_pct"] = pd.NA
offers.loc[offers["net_price"] == 0, "margin_pct"] = pd.NA

# ── ODV_2025_v2 → orders ──────────────────────────────────────────────────────
raw_orders = read_italian_csv(raw_files["ODV_2025_v2"])
strip_columns(raw_orders)
orders = raw_orders.rename(columns={
    "Numord":       "order_num",
    "Rigord":       "order_row",
    "Codcli":       "client_code",
    "Codart":       "article_code",
    "Data_ordine":  "order_date",
    "Qtaord":       "qty",
})
orders["client_code"]  = orders["client_code"].str.strip()
orders["article_code"] = orders["article_code"].str.strip()
orders["order_date"]   = parse_italian_date(orders["order_date"])
orders["qty"]          = to_float(orders["qty"])

# ── CARTELLINI ────────────────────────────────────────────────────────────────
raw_cartellini = read_italian_csv(raw_files["CARTELLINI"])
strip_columns(raw_cartellini)
cartellini = raw_cartellini.rename(columns={
    "Codcli":    "client_code",
    "Codsco":    "sco_code",
    "PercSco":   "contract_discount_pct",
})
cartellini["client_code"]          = cartellini["client_code"].str.strip()
cartellini["sco_code"]             = cartellini["sco_code"].str.strip()
cartellini["contract_discount_pct"] = to_float(cartellini["contract_discount_pct"])

# ── PROMOZIONI-ARTICOLI → promo_articles ─────────────────────────────────────
raw_promo_art = read_italian_csv(raw_files["PROMOZIONI_ARTICOLI"])
strip_columns(raw_promo_art)
promo_articles = raw_promo_art.rename(columns={
    "N*promo":       "promo_id",
    "Tipo promo":    "promo_type",
    "Articolo":      "article_code",
    "Importo":       "amount",
    "Divisa":        "currency",
    "Moltiplicatore":"multiplier",
    "UM":            "unit",
})
promo_articles["promo_id"]      = promo_articles["promo_id"].str.strip()
promo_articles["article_code"]  = promo_articles["article_code"].str.strip()
promo_articles["amount"]        = to_float(promo_articles["amount"])
promo_articles["multiplier"]    = to_float(promo_articles["multiplier"])

# ── PROMOZIONI-CLIENTI → promo_clients ───────────────────────────────────────
raw_promo_cli = read_italian_csv(raw_files["PROMOZIONI_CLIENTI"])
strip_columns(raw_promo_cli)
promo_clients = raw_promo_cli.rename(columns={
    "n° promo": "promo_id",
    "Cliente":  "client_code",
})
promo_clients["promo_id"]     = promo_clients["promo_id"].str.strip()
promo_clients["client_code"]  = promo_clients["client_code"].str.strip()

# ── Write SQLite ──────────────────────────────────────────────────────────────
section("Writing SQLite database")
print(f"  Target: {DB_PATH}")

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

# Drop all tables for idempotency
for tbl in (
    "offers", "orders", "clients", "articles",
    "cartellini", "promo_articles", "promo_clients",
):
    cur.execute(f"DROP TABLE IF EXISTS {tbl}")

# Write tables
offers.to_sql("offers",         con, index=False, if_exists="replace")
orders.to_sql("orders",         con, index=False, if_exists="replace")
clients.to_sql("clients",       con, index=False, if_exists="replace")
articles.to_sql("articles",     con, index=False, if_exists="replace")
cartellini.to_sql("cartellini", con, index=False, if_exists="replace")
promo_articles.to_sql("promo_articles", con, index=False, if_exists="replace")
promo_clients.to_sql("promo_clients",   con, index=False, if_exists="replace")

# ── Indexes ───────────────────────────────────────────────────────────────────
cur.executescript("""
    CREATE INDEX IF NOT EXISTS idx_offers_client_article ON offers(client_code, article_code);
    CREATE INDEX IF NOT EXISTS idx_offers_sco ON offers(article_code);
    CREATE INDEX IF NOT EXISTS idx_offers_date ON offers(offer_date);
    CREATE INDEX IF NOT EXISTS idx_orders_client_article ON orders(client_code, article_code);
    CREATE INDEX IF NOT EXISTS idx_articles_sco ON articles(sco_code);
    CREATE INDEX IF NOT EXISTS idx_cartellini_client_sco ON cartellini(client_code, sco_code);
    CREATE INDEX IF NOT EXISTS idx_promo_articles_article ON promo_articles(article_code);
    CREATE INDEX IF NOT EXISTS idx_promo_clients_client ON promo_clients(client_code);
""")
con.commit()
con.close()
print("  Done.")

# ── Data Quality Report ───────────────────────────────────────────────────────
section("Data Quality Report")

print("\n── Row counts ──────────────────────────────────────────────")
table_counts = {
    "offers":         len(offers),
    "orders":         len(orders),
    "clients":        len(clients),
    "articles":       len(articles),
    "cartellini":     len(cartellini),
    "promo_articles": len(promo_articles),
    "promo_clients":  len(promo_clients),
}
for tbl, cnt in table_counts.items():
    print(f"  {tbl:<20} {cnt:>6} rows")

print("\n── Offer row_status distribution ───────────────────────────")
for status, cnt in offers["row_status"].value_counts().items():
    pct = 100 * cnt / len(offers)
    print(f"  {status:<10} {cnt:>5} ({pct:.1f}%)")

print("\n── Client type distribution ────────────────────────────────")
for ctype, cnt in clients["client_type"].value_counts().items():
    print(f"  {str(ctype):<20} {cnt:>4}")

print("\n── Null rates for optional client fields ───────────────────")
optional_fields = ["province", "agent", "potential", "num_employees"]
for fld in optional_fields:
    n_null = clients[fld].isna().sum()
    pct = 100 * n_null / len(clients) if len(clients) > 0 else 0
    print(f"  {fld:<20} {n_null:>3} / {len(clients)} null  ({pct:.1f}%)")

print("\n── Article coverage ────────────────────────────────────────")
arts_in_offers   = set(offers["article_code"].dropna())
arts_in_anagrafica = set(articles["article_code"].dropna())
print(f"  Articles in offers:       {len(arts_in_offers)}")
print(f"  Articles in anagrafica:   {len(arts_in_anagrafica)}")
arts_only_offers = arts_in_offers - arts_in_anagrafica
if arts_only_offers:
    warn(f"Articles in offers not in anagrafica: {sorted(arts_only_offers)}")
else:
    print("  All offer articles found in anagrafica: OK")

print("\n── Client coverage ─────────────────────────────────────────")
clients_in_offers = set(offers["client_code"].dropna())
clients_in_anagrafica = set(clients["client_code"].dropna())
orphan_clients = clients_in_offers - clients_in_anagrafica
if orphan_clients:
    warn(f"Clients in offers not found in anagrafica: {sorted(orphan_clients)}")
else:
    print("  All offer clients found in anagrafica: OK")

print("\n── Promo warnings ──────────────────────────────────────────")
if "offer_date" not in raw_promo_art.columns and "data_inizio" not in raw_promo_art.columns:
    warn("PROMOZIONI-ARTICOLI has no date/period column — all promos treated as currently active.")
if "offer_date" not in raw_promo_cli.columns:
    warn("PROMOZIONI-CLIENTI has no date/period column — all promos treated as currently active.")

print("\n── Derived columns sample (offers) ─────────────────────────")
sample = offers[["offer_num", "client_code", "article_code",
                  "list_price", "net_price", "unit_cost",
                  "discount_pct", "margin_pct"]].head(5)
print(sample.to_string(index=False))

print(f"\n{'='*60}")
print(f"  Ingestion complete → {DB_PATH}")
print(f"{'='*60}\n")
