# Hammerz

Simulated live-auction platform: USD wallets, catalog lots from [The Met Collection API](https://metmuseum.github.io/), real-time bidding with anti-snipe extensions, settlement receipts, and a tamper-evident audit journal. Deposits and payouts are ledger entries only—no payment integration. There is no payment processor.

## Live demo

After deploy, set your public URL here (example shape):



Local development: **http://localhost** (HTTP only).

## Quick start

```bash
cp .env.example .env
# JWT_SECRET, HMAC_SECRET, ALIAS_SECRET — at least 32 characters each.

docker compose up --build -d
docker compose exec backend seed-demo
docker compose exec backend seed-demo --ensure-live
```

Migrations run on backend startup. Seed is idempotent (no reset of passwords, balances, or history). `--ensure-live` adds a live lot only when none exists.

### Public deploy (HTTPS + WSS)

1. Point DNS at your server.
2. In `.env`, set secrets and `CORS_ORIGINS=https://your-public-origin` (exact origin, no trailing slash).
3. Export `SITE_ADDRESS=your-public-hostname` for Compose (see `.env.example` comment).
4. `docker compose up --build -d`, then run both seed commands on the server.
5. Verify from an external network: HTTPS, login, bid, WebSocket updates, public audit and receipt links.

Caddy uses Automatic HTTPS when `SITE_ADDRESS` is a public hostname (not `:80`).

## Demo accounts

Credentials are not shown in the app. Use after `seed-demo`.

| Email | Password | Role |
| --- | --- | --- |
| `seller@hammerz.test` | `Seller-Demo-2026!` | Seller |
| `bidder1@hammerz.test` | `Bidder1-Demo-2026!` | Bidder |
| `bidder2@hammerz.test` | `Bidder2-Demo-2026!` | Bidder |

### Balances after first seed (fresh database)

| Account | Total | Committed | Available |
| --- | --- | --- | --- |
| seller | $0.00 | $0.00 | $0.00 |
| bidder1 | $10,000.00 | $1,500.00 | $8,500.00 |
| bidder2 | $10,000.00 | $0.00 | $10,000.00 |

The evaluation live lot uses opening $1,000.00, increment $50.00, with bids at $1,000.00 (bidder2) and $1,500.00 (bidder1). The seed also creates a settled lot (seller proceeds on Dashboard), a scheduled lot, and a cancelled lot with public reason. Re-running `seed-demo` does not reset passwords, balances, or history. Real evaluation changes wallets normally.

**Roteiro:** Sign in as seller → **Dashboard** → manage lots / **New lot** (Met search). Sign in as each bidder → **Auctions** → open a live lot → bid; **Wallet** / **Bids** for balances and participations.

## Routes

| Path | Purpose |
| --- | --- |
| `/` | Vitrine (Live / Upcoming / Ended) |
| `/login`, `/register` | Auth |
| `/seller` | Met search, lots, proceeds |
| `/wallet` | Balances, simulated deposits |
| `/bids` | Active, won, and past participations |
| `/lots/:id` | Lot room (REST + WebSocket) |
| `/lots/:id/audit` | Public integrity check |
| `/receipts/:id` | Public settlement receipt |

Domain rules and API detail: [SPEC.md](SPEC.md). Stack, journal, backup: [docs/architecture.md](docs/architecture.md). Agents: [AGENTS.md](AGENTS.md).

## Stack

React (Vite, TypeScript, Tailwind), TanStack Query, FastAPI, PostgreSQL 16, SQLAlchemy 2, Alembic, Caddy, Docker Compose. Single API worker; audit journal JSONL on `audit_data` volume (not in Postgres).

## Auction rules (summary)

- USD integer cents everywhere; anti-snipe: if a bid lands in the last 120s, `ends_at` extends by 2 minutes from the previous end (not from bid time).
- Cancel with bids requires a public reason (10–500 characters after trim).
- Bid, deposit, and cancel require header `Idempotency-Key` (UUID).

## Audit and tamper check

HMAC-chained events in an append-only journal; PREPARE before DB commit, COMMIT after success. Public `/lots/:id/audit` recomputes verification (no cached seal).

**Safe demo on a disposable DB:** open audit on a seeded lot → **VERIFIED**. In psql: `UPDATE bids SET amount_cents = amount_cents + 1 WHERE auction_id = '<uuid>';` → audit and receipt banners show **TAMPERED**.

Threat model: attacker with Postgres-only access, not app secrets or journal volume. Pending PREPARE after crash blocks audited writes until admin recovery (no auto-ABORT from missing rows).

## Operations

- Backup: restore `postgres_data` and `audit_data` together with the same secrets; do not pair an old DB with an empty journal.
- Avoid `docker compose down -v` in normal operation.
- Before sharing the public link: `seed-demo --ensure-live` and confirm a **Live** lot from outside your LAN.

## Decisions

- Sign-in persists via HttpOnly refresh cookie; access JWT stays in memory only.
- Sellers are seed-provisioned; public register creates bidders with $0 wallets.
- Seed command: `seed-demo` .

## Limitations

- No password reset, seller self-registration, or real payments.
- Vitrine title filter is client-side on the current tab only (up to 20 lots).
- Full journal-vs-DB reconciliation on every tamper class is bounded by what PREPARE records; see tests in `backend/tests/test_audit*.py`.

## AI & authorship



## Development

Backend tests need PostgreSQL 16. Default Compose does **not** publish port 5432; run Postgres locally or match [CI](.github/workflows/ci.yml).

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
