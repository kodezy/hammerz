# Hammerz

Simulated live auctions: lots from [The Met Collection API](https://metmuseum.github.io/), USD wallets, WebSocket bidding, settlement receipts, and a tamper-evident audit journal. Deposits and payouts are ledger entries only — no payment processor.

Local: **http://localhost** (HTTP). Production hostname is `SITE_ADDRESS` (HTTPS via Caddy).

## Quick start

```bash
cp .env.example .env
# JWT_SECRET, HMAC_SECRET, ALIAS_SECRET — at least 32 characters each.

docker compose up --build -d
docker compose exec backend seed-demo
docker compose exec backend seed-demo --ensure-live
```

Migrations run on backend startup. `seed-demo` is idempotent (does not reset passwords, balances, or history). `--ensure-live` creates a live lot only when none exists.

## Accounts

Credentials are not shown in the app.

| Email | Password | Role |
| --- | --- | --- |
| `seller@hammerz.test` | `Seller-Demo-2026!` | Seller |
| `bidder1@hammerz.test` | `Bidder1-Demo-2026!` | Bidder |
| `bidder2@hammerz.test` | `Bidder2-Demo-2026!` | Bidder |

After a **fresh** seed: seller $0; each bidder $10,000 total; bidder1 has $1,500 committed on the live lot (opening $1,000, increment $50; bids $1,000 then $1,500). Seed also includes a settled, a scheduled, and a cancelled lot. Further deposits and bids change wallets through the app.

Seller: **Dashboard** → lots / **New lot**. Bidder: **Auctions** → live lot → bid; **Wallet** and **Bids**.

## Routes

| Path | Purpose |
| --- | --- |
| `/` | Vitrine (Live / Upcoming / Ended) |
| `/login`, `/register` | Auth |
| `/seller` | Met search, lots, proceeds |
| `/wallet` | Balances, simulated deposits |
| `/bids` | Participations |
| `/lots/:id` | Lot room (REST + WebSocket) |
| `/lots/:id/audit` | Public integrity check |
| `/receipts/:id` | Settlement receipt |

Rules and API: [SPEC.md](SPEC.md). Journal, backup, tamper check: [docs/architecture.md](docs/architecture.md).

## Stack

React (Vite, TypeScript, Tailwind), TanStack Query, FastAPI, PostgreSQL 16, SQLAlchemy 2, Alembic, Caddy, Docker Compose. One API worker. Audit journal is JSONL on `audit_data`, not in Postgres.

## Money and bidding

Integer USD cents only. Anti-snipe: a bid in the last 120 seconds extends `ends_at` by 2 minutes from the previous end. Cancel with bids requires a public reason (10–500 characters after trim). Bid, deposit, and cancel require `Idempotency-Key` (UUID).

## Audit and operations

HMAC-chained append-only journal: PREPARE (fsync) before Postgres commit; COMMIT or ABORT after a known DB outcome. Public `/lots/:id/audit` recomputes verification (no cached seal). Pending PREPARE after a crash blocks audited writes until an operator resolves it — there is no auto-ABORT from missing rows.

Restore `postgres_data` and `audit_data` together with the same secrets. Do not pair an old database with an empty journal. Avoid `docker compose down -v` on a running install.

Tamper check and crash behavior: [docs/architecture.md](docs/architecture.md).

## Deploy

1. DNS for the public hostname → the host.
2. `.env`: secrets; `CORS_ORIGINS` = exact HTTPS origin (no trailing slash).
3. `SITE_ADDRESS` = that hostname (see `.env.example`). Unset keeps local HTTP on port 80.
4. `docker compose up --build -d`, then both seed commands.
5. Confirm from outside the LAN: HTTPS, login, bid, WebSocket, audit and receipt pages, and a **Live** lot.

Caddy Automatic HTTPS applies when `SITE_ADDRESS` is a public hostname.

## Limitations

No password reset, seller self-registration, or real payments. Vitrine title filter is client-side on the current tab (up to 20 lots).

## Development

Backend tests need PostgreSQL 16. Compose does not publish `5432` by default; use local Postgres or [CI](.github/workflows/ci.yml).

```bash
cd backend && uv sync --extra dev
export DATABASE_URL=postgresql+psycopg://hammerz:hammerz@127.0.0.1:5432/hammerz
export JWT_SECRET=test-secret-32-chars-minimum!!
export HMAC_SECRET=test-secret-32-chars-minimum!!
export ALIAS_SECRET=test-secret-32-chars-minimum!!
uv run ruff format . && uv run ruff check . && uv run pytest -q
```

```bash
cd frontend && npm ci && npm run test && npm run build
cd frontend && npm run dev
```
