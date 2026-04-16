"""
Generate synthetic sample CSVs in Italian format (semicolon delimiter, comma decimals)
matching the Marchiol schema. Run once to populate data/raw/.
"""

import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

OUT = Path(__file__).parent.parent / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)


def comma_float(v: float) -> str:
    return f"{v:.2f}".replace(".", ",")


def write_csv(name: str, rows: list[str]) -> None:
    path = OUT / name
    path.write_text("\n".join(rows) + "\n", encoding="utf-8-sig")
    print(f"  wrote {path} ({len(rows)-1} data rows)", file=sys.stderr)


# ── ANAG_CLIENTI ─────────────────────────────────────────────────────────────
clients = [
    ("C001", "Installatore", "Filiale Nord", "Mario Rossi Impianti", "Alto", "15", "Milano", "MI", "Rossi"),
    ("C002", "Impresa", "Filiale Centro", "Costruzioni Bianchi Srl", "Medio", "45", "Roma", "RM", "Bianchi"),
    ("C003", "Rivenditore", "Filiale Nord", "Elettrostore Torino", "Alto", "8", "Torino", "TO", "Rossi"),
    ("C004", "OEM", "Filiale Nord", "AutoElettro OEM Srl", "Alto", "120", "Milano", "MI", "Bianchi"),
    ("C005", "Quadrista", "Filiale Sud", "Quadri Napoli Srl", "Basso", "5", "Napoli", "NA", "Verdi"),
    ("C006", "Installatore", "Filiale Nord", "Bergamo Impianti", "", "10", "Bergamo", "BG", "Rossi"),
    ("C007", "Impresa", "Filiale Centro", "Costruzioni Verde Srl", "Medio", "30", "Firenze", "FI", "Bianchi"),
    ("C008", "Rivenditore", "Filiale Sud", "", "Basso", "", "Palermo", "PA", "Verdi"),
    ("C009", "Installatore", "Filiale Nord", "Varese Elettrica", "", "7", "Varese", "VA", "Rossi"),
    ("C010", "OEM", "Filiale Centro", "Roma OEM Srl", "Medio", "55", "Roma", "RM", "Bianchi"),
]
header = "Codcli;Descrtipcli;Descrfil;Rag. Sociale;Potenziale;Numdip;Città;Provincia;Descrage"
rows = [header] + [";".join(c) for c in clients]
write_csv("ANAG_CLIENTI.csv", rows)

# ── ANAG_ARTICOLI ─────────────────────────────────────────────────────────────
articles = [
    ("A001", "SCO_01", "Interruttori Modulari", "Interruttore 1P 10A"),
    ("A002", "SCO_01", "Interruttori Modulari", "Interruttore 1P 16A"),
    ("A003", "SCO_01", "Interruttori Modulari", "Interruttore 2P 25A"),
    ("A004", "SCO_02", "Cavi e Conduttori", "Cavo NYM 3x1.5"),
    ("A005", "SCO_02", "Cavi e Conduttori", "Cavo NYM 3x2.5"),
    ("A006", "SCO_03", "Quadri Elettrici", "Quadro 8 Moduli"),
    ("A007", "SCO_03", "Quadri Elettrici", "Quadro 12 Moduli"),
    ("A008", "SCO_03", "Quadri Elettrici", "Quadro 24 Moduli"),
    ("A009", "SCO_01", "Interruttori Modulari", ""),   # new article, sparse offers
    ("A010", "SCO_02", "Cavi e Conduttori", "Cavo FG7 3x6"),
]
header = "Codart;Codsco;Descrsco;Descart"
rows = [header] + [";".join(a) for a in articles]
write_csv("ANAG_ARTICOLI.csv", rows)

# ── Base prices (list, cost) ──────────────────────────────────────────────────
base = {
    "A001": (5.50, 3.50),
    "A002": (7.20, 4.60),
    "A003": (12.80, 8.20),
    "A004": (85.00, 55.00),
    "A005": (120.00, 78.00),
    "A006": (45.00, 28.00),
    "A007": (68.00, 42.00),
    "A008": (125.00, 78.00),
    "A009": (28.00, 18.00),
    "A010": (180.00, 115.00),
}

# ── OFFERTE_2025 ──────────────────────────────────────────────────────────────
# For each (client, article) combo below we create N accepted offers,
# with discounts drawn from [low, high] range and a scattering of PER rows.
# Columns: Numoff;Rigoff;Codcli;Codart;Data_Offerta;Qtaoff;List_Appl_Unit;Prz_Netto_Unit;Cdv_Unit;Stato_Riga_Off

combos_acc: list[tuple[str, str, int, float, float]] = [
    # (client, article, count, disc_low, disc_high)
    # ── C001 / Installatore / MI / Rossi ──
    ("C001", "A001", 10, 0.20, 0.24),   # main integration test pair
    ("C001", "A002",  4, 0.21, 0.25),
    ("C001", "A003",  3, 0.22, 0.26),
    ("C001", "A006",  6, 0.25, 0.30),
    ("C001", "A010",  5, 0.28, 0.33),
    # ── C002 / Impresa / RM ──
    ("C002", "A001",  5, 0.24, 0.28),
    ("C002", "A004",  6, 0.27, 0.31),
    ("C002", "A007",  5, 0.26, 0.30),
    # ── C003 / Rivenditore / TO ──
    ("C003", "A002",  5, 0.30, 0.35),
    ("C003", "A005",  5, 0.31, 0.36),
    ("C003", "A006",  5, 0.32, 0.37),
    # ── C004 / OEM / MI ──
    ("C004", "A001",  5, 0.35, 0.40),
    ("C004", "A003",  5, 0.36, 0.41),
    ("C004", "A010",  5, 0.33, 0.38),
    # ── C005 / Quadrista / NA ──
    ("C005", "A003",  5, 0.27, 0.32),
    ("C005", "A007",  5, 0.28, 0.33),
    ("C005", "A008",  5, 0.29, 0.34),
    # ── C006 / Installatore / BG ──
    ("C006", "A001",  5, 0.19, 0.23),
    ("C006", "A002",  5, 0.20, 0.24),
    # ── C007 / Impresa / FI ──
    ("C007", "A004",  5, 0.28, 0.32),
    ("C007", "A005",  5, 0.29, 0.33),
    # ── C008 / Rivenditore / PA ──
    ("C008", "A005",  5, 0.33, 0.38),
    ("C008", "A008",  3, 0.30, 0.35),
    # ── C009 / Installatore / VA — sparse, for cascade testing ──
    ("C009", "A001",  3, 0.21, 0.24),
    # ── C010 / OEM / RM ──
    ("C010", "A003",  5, 0.37, 0.42),
    ("C010", "A004",  5, 0.34, 0.39),
    # ── A009 sparse offers — only 3 total across all clients ──
    ("C001", "A009",  1, 0.18, 0.22),
    ("C002", "A009",  1, 0.20, 0.24),
    ("C003", "A009",  1, 0.22, 0.26),
]

offer_header = "Numoff;Rigoff;Codcli;Codart;Data_Offerta;Qtaoff;List_Appl_Unit;Prz_Netto_Unit;Cdv_Unit;Stato_Riga_Off"
offer_rows = [offer_header]
numoff = 10000
rigoff = 1

start_date = date(2025, 1, 1)

for client, art, count, dlow, dhigh in combos_acc:
    list_p, cost_p = base[art]
    for i in range(count):
        disc = random.uniform(dlow, dhigh)
        net = round(list_p * (1 - disc), 2)
        qty = random.choice([1, 2, 5, 10, 20, 50])
        day_offset = random.randint(0, 365)
        d = start_date + timedelta(days=day_offset)
        row = (
            f"OFF{numoff};{rigoff};{client};{art};"
            f"{d.strftime('%d/%m/%Y')};{qty};"
            f"{comma_float(list_p)};{comma_float(net)};{comma_float(cost_p)};ACC"
        )
        offer_rows.append(row)
        numoff += 1
        rigoff += 1

# Add some PER (lost) offers
per_combos = [
    ("C001", "A001"), ("C001", "A002"), ("C002", "A004"),
    ("C003", "A005"), ("C004", "A003"), ("C005", "A008"),
]
for client, art in per_combos:
    list_p, cost_p = base[art]
    disc = random.uniform(0.15, 0.18)  # lower discount → lost
    net = round(list_p * (1 - disc), 2)
    qty = random.choice([1, 2, 5])
    day_offset = random.randint(0, 365)
    d = start_date + timedelta(days=day_offset)
    row = (
        f"OFF{numoff};{rigoff};{client};{art};"
        f"{d.strftime('%d/%m/%Y')};{qty};"
        f"{comma_float(list_p)};{comma_float(net)};{comma_float(cost_p)};PER"
    )
    offer_rows.append(row)
    numoff += 1
    rigoff += 1

# A few IN CORSO offers
for client, art in [("C001", "A001"), ("C002", "A007")]:
    list_p, cost_p = base[art]
    disc = 0.22
    net = round(list_p * (1 - disc), 2)
    row = (
        f"OFF{numoff};{rigoff};{client};{art};"
        f"01/03/2025;5;"
        f"{comma_float(list_p)};{comma_float(net)};{comma_float(cost_p)};INC"
    )
    offer_rows.append(row)
    numoff += 1
    rigoff += 1

write_csv("OFFERTE_2025.csv", offer_rows)

# ── ODV_2025_v2 ───────────────────────────────────────────────────────────────
odv_header = "Numord;Rigord;Codcli;Codart;Data_ordine;Qtaord"
odv_rows = [odv_header]
numord = 5000
for client, art, count, _, _ in combos_acc:
    for i in range(min(count, 4)):
        day_offset = random.randint(0, 365)
        d = start_date + timedelta(days=day_offset)
        qty = random.choice([1, 2, 5, 10])
        odv_rows.append(
            f"ORD{numord};{i+1};{client};{art};"
            f"{d.strftime('%d/%m/%Y')};{qty}"
        )
        numord += 1
write_csv("ODV_2025_v2.csv", odv_rows)

# ── CARTELLINI ────────────────────────────────────────────────────────────────
cartellini = [
    ("C001", "SCO_01", "0,25"),   # 25% floor — key for floor test
    ("C001", "SCO_02", "0,30"),
    ("C001", "SCO_03", "0,28"),
    ("C002", "SCO_01", "0,28"),
    ("C002", "SCO_02", "0,30"),
    ("C003", "SCO_02", "0,33"),
    ("C003", "SCO_03", "0,35"),
    ("C004", "SCO_01", "0,38"),
    ("C004", "SCO_02", "0,35"),
    ("C005", "SCO_01", "0,28"),
    ("C005", "SCO_03", "0,30"),
    ("C007", "SCO_02", "0,30"),
    ("C010", "SCO_01", "0,38"),
    ("C010", "SCO_02", "0,36"),
]
header = "Codcli;Codsco;PercSco"
rows = [header] + [";".join(c) for c in cartellini]
write_csv("CARTELLINI.csv", rows)

# ── PROMOZIONI-ARTICOLI ───────────────────────────────────────────────────────
promo_art = [
    ("P001", "Sconto Speciale", "A010", "10,00", "EUR", "1,00", "PZ"),
    ("P001", "Sconto Speciale", "A005", "8,00", "EUR", "1,00", "PZ"),
    ("P002", "Promo Volume", "A001", "5,00", "EUR", "10,00", "PZ"),
    ("P002", "Promo Volume", "A002", "6,00", "EUR", "10,00", "PZ"),
]
header = "N*promo;Tipo promo;Articolo;Importo;Divisa;Moltiplicatore;UM"
rows = [header] + [";".join(p) for p in promo_art]
write_csv("PROMOZIONI-ARTICOLI.csv", rows)

# ── PROMOZIONI-CLIENTI ────────────────────────────────────────────────────────
promo_cli = [
    ("P001", "C001"),
    ("P001", "C003"),
    ("P002", "C001"),
    ("P002", "C002"),
    ("P002", "C006"),
]
header = "n° promo;Cliente"
rows = [header] + [";".join(p) for p in promo_cli]
write_csv("PROMOZIONI-CLIENTI.csv", rows)

print("Sample data generation complete.", file=sys.stderr)
