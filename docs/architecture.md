# Architecture

Hammerz is a simulated live-auction platform: USD wallets, Met catalog lots, concurrent bidding with anti-snipe, settlement receipts, and a tamper-evident HMAC journal. Deposits and payouts are ledger entries only — no payment processor.

## System map

```
compose.yaml          Caddy (web) → FastAPI (backend) → PostgreSQL 16
infra/Caddyfile       SPA + reverse_proxy /api /ws /health
backend/src/
  main.py             app factory, WS /ws/auctions/{id}, settle loop
  boot.py             wait for Postgres, alembic upgrade, uvicorn --workers 1
  api/                HTTP routers under /api/v1
  modules/            domain: auth, alias, auctions, bids, cancel,
                      catalog, journal, settle, wallet, audit, seed
  core/               config, errors, money, canon, security, limits
  db/                 SQLAlchemy 2 tables + session (psycopg3, sync)
  realtime/hub.py     in-process WebSocket fan-out after COMMIT
backend/migrations/  Alembic (0001_init.py)
frontend/src/
  app/                routes, session, query, theme
  pages/              one PascalCase word per route; TanStack Query lives here
  features/           HTTP clients for `/api/v1`
  components/         shared UI
  lib/                http, money, ws, types
```

REST is authoritative. WebSocket frames broadcast confirmed transitions only after PostgreSQL commit and journal COMMIT. One API process; no Redis, queue, or extra workers.

## Boundaries

**api** — HTTP shapes, auth deps, `Idempotency-Key`. Does not own ledger or journal rules. In-memory limits live in `core/limits.py` (auth routes, bids, WebSocket).

**modules** — auctions, bids, cancel, settle, wallet, journal, catalog, auth. Owns money movement, lock order, and audit records.

**journal** — append-only JSONL + manifest on `AUDIT_DIR` (`audit_data` volume). PREPARE (fsync) before DB commit; COMMIT or ABORT after known DB outcome. Unknown outcome → `202 OPERATION_PENDING`; do not infer ABORT from missing rows.

**frontend** — English React SPA. Talks to `/api/v1` and `/ws`. JWT in module memory plus `sessionStorage["hammerz:token"]` (not `localStorage`). Theme in `localStorage["hammerz:theme"]`.

**Caddy** — serves the built SPA; proxies API/WS/health. Compose does not publish backend or Postgres ports.

## Dependency direction

Allowed: `api` → `modules` → `core` / `db` / `journal`. Frontend → HTTP/WS only.

Forbidden: frontend importing backend; modules calling React; second datastore; asyncpg alongside psycopg; SQLite in tests.

## Money and time

Integer USD cents everywhere (`MoneyCents` / `StrictInt` on write paths). Clocks for bid/cancel/close use `SELECT clock_timestamp()` after locks, not client time. Anti-snipe: if a bid lands in the last 120s, extend `ends_at` by 2 minutes; refuse `accepted_at == ends_at`.

Audited mutations lock journal first, then auction `FOR UPDATE`, then wallets by ascending UUID. Deposits lock the wallet only.

## Verification

Architecture checks: none.

Fast check: `cd backend && uv run ruff format . && uv run ruff check .`

Tests: `cd backend && uv run pytest -q` (real PostgreSQL 16; `DATABASE_URL` as in CI).

SPA: `cd frontend && npm run build`

## Freshness

Last verified: 2026-10-27
