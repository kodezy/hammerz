# Hammerz

Simulated live auctions: Met catalog lots, USD wallets, WebSocket bidding, settlement receipts, and a tamper-evident audit journal. Ledger-only money (no payment processor).

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

Migrations run on backend startup. `seed-demo` is idempotent. `--ensure-live` adds a live lot when none exists.

### Public deploy (HTTPS + WSS)

1. Point DNS at your server.
2. In `.env`, set secrets and `CORS_ORIGINS=https://your-public-origin` (exact origin, no trailing slash).
3. Export `SITE_ADDRESS=your-public-hostname` for Compose (see `.env.example`).
4. `docker compose up --build -d`, then run both seed commands.
5. From an external network: HTTPS, login, bid, WebSocket updates, audit and receipt pages.

Caddy uses Automatic HTTPS when `SITE_ADDRESS` is a public hostname (not `:80`).

## Demo accounts

Not shown in the app. Use after `seed-demo`.

| Email | Password | Role |
| --- | --- | --- |
| `seller@hammerz.test` | `Seller-Demo-2026!` | Seller |
| `bidder1@hammerz.test` | `Bidder1-Demo-2026!` | Bidder |
| `bidder2@hammerz.test` | `Bidder2-Demo-2026!` | Bidder |

On a **fresh** database, bidder1 has $1,500 committed after seed (live lot with two bids). Sample settled, scheduled, and cancelled lots are included. Bidding and deposits change balances normally.

| Account | Total | Committed | Available |
| --- | --- | --- | --- |
| seller | $0.00 | $0.00 | $0.00 |
| bidder1 | $10,000.00 | $1,500.00 | $8,500.00 |
| bidder2 | $10,000.00 | $0.00 | $10,000.00 |

Smoke test: seller → **Dashboard** / **New lot**; bidder → **Auctions** → live lot → bid; **Wallet** and **Bids**.

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

**Docs:** product and API — [SPEC.md](SPEC.md); code map, journal, backup, tamper demo — [docs/architecture.md](docs/architecture.md); agent commands — [AGENTS.md](AGENTS.md).

## Limitations

No password reset, seller self-registration, or real payments. Vitrine title filter is client-side on the current tab only (up to 20 lots).

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


