# Marchiol Pricing Cockpit

Demonstrative pricing recommendation prototype for Marchiol (B2B electrotechnical distributor).

## Stack
- **Frontend**: Next.js 14 (App Router) + shadcn/ui
- **Backend**: FastAPI + SQLite + scikit-learn
- **Package managers**: pnpm (frontend), uv (Python)

## Quick Start

```bash
# Install all dependencies
make install

# Ingest CSVs → SQLite (drop real CSVs in data/raw/ first)
make ingest

# Start backend API
make backend

# Run tests
make test
```

## Data

Drop the following CSVs into `data/raw/` before running `make ingest`:
- `OFFERTE_2025.csv`
- `ODV_2025_v2.csv`
- `ANAG_CLIENTI.csv`
- `ANAG_ARTICOLI.csv`
- `CARTELLINI.csv`
- `PROMOZIONI-ARTICOLI.csv`
- `PROMOZIONI-CLIENTI.csv`

Italian format expected: semicolon delimiters, comma decimals, UTF-8 or UTF-8 BOM.

## API

- `GET  /health`
- `GET  /catalog/clients?search=<str>&limit=20`
- `GET  /catalog/articles?search=<str>&limit=20`
- `GET  /clients/{client_code}/context`
- `POST /pricing/recommend`

See `backend/README.md` for full API docs.
