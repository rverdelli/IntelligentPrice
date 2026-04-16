# Marchiol Pricing Backend

FastAPI backend for the Marchiol Pricing Cockpit.

## Setup

```bash
uv sync --extra test
```

## Running

```bash
uvicorn app.main:app --reload --port 8000
```

Or via Makefile: `make backend`

## API Endpoints

### Health
`GET /health` → `{"status": "ok"}`

### Catalog
`GET /catalog/clients?search=rossi&limit=20`
`GET /catalog/articles?search=interruttore&limit=20`

### Client Context
`GET /clients/{client_code}/context`

Returns client details, active cartellini, and last 10 offers.

### Pricing
`POST /pricing/recommend`

```json
{
  "client_code": "C001",
  "items": [
    {"article_code": "A001", "qty": 10}
  ]
}
```

## Tests

```bash
uv run pytest tests/ -v
```
