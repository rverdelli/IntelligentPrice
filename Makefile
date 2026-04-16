.PHONY: install ingest backend test clean

# ── Install dependencies ───────────────────────────────────────────────────────
install:
	@echo "→ Installing backend dependencies (uv)..."
	cd backend && uv sync --extra test
	@echo "→ Installing frontend dependencies (pnpm)..."
	cd frontend && pnpm install --frozen-lockfile 2>/dev/null || pnpm install
	@echo "✓ Install complete."

install-backend:
	cd backend && uv sync --extra test

# ── Data ingestion ─────────────────────────────────────────────────────────────
ingest:
	@echo "→ Running CSV → SQLite ingestion..."
	cd backend && uv run python ../scripts/ingest.py --db ../data/marchiol.db --raw ../data/raw

# ── Backend server ─────────────────────────────────────────────────────────────
backend:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ── Tests ──────────────────────────────────────────────────────────────────────
test:
	cd backend && uv run pytest tests/ -v

test-cov:
	cd backend && uv run pytest tests/ -v --tb=short

# ── Sample request ─────────────────────────────────────────────────────────────
sample-request:
	curl -s -X POST http://localhost:8000/pricing/recommend \
	  -H "Content-Type: application/json" \
	  -d @sample/recommend.json | python3 -m json.tool

# ── Cleanup ────────────────────────────────────────────────────────────────────
clean:
	rm -f data/marchiol.db
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
