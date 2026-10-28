# Hammerz

Simulated live auctions: Met catalog lots, USD wallets, WebSocket bidding, settlement receipts, and a tamper-evident audit journal. Ledger-only money (no payment processor).

Local: **http://localhost**. Production: set `SITE_ADDRESS` for HTTPS (Caddy).

## Quick start

```bash
cp .env.example .env
# Set JWT_SECRET, HMAC_SECRET, ALIAS_SECRET (≥32 chars each).

docker compose up --build -d
docker compose exec backend seed-demo
docker compose exec backend seed-demo --ensure-live
```

Migrations run on backend startup. `seed-demo` is idempotent. `--ensure-live` adds a live lot when none exists.

## Accounts

Credentials are not shown in the app.

| Email | Password | Role |
| --- | --- | --- |
| `seller@hammerz.test` | `Seller-Demo-2026!` | Seller |
| `bidder1@hammerz.test` | `Bidder1-Demo-2026!` | Bidder |
| `bidder2@hammerz.test` | `Bidder2-Demo-2026!` | Bidder |

After a fresh seed: seller $0; each bidder $10,000 total; bidder1 has $1,500 committed on the live lot. Seed includes settled, scheduled, and cancelled sample lots.

Seller: **Dashboard** / **New lot**. Bidder: **Auctions** → live lot → bid; **Wallet** and **Bids**.

## Routes

| Path | Purpose |
| --- | --- |
| `/` | Vitrine |
| `/login`, `/register` | Auth |
| `/seller` | Lots, Met search, proceeds |
| `/wallet` | Balances, deposits |
| `/bids` | Participations |
| `/lots/:id` | Lot room |
| `/lots/:id/audit` | Integrity check |
| `/receipts/:id` | Settlement receipt |

Rules and API: [SPEC.md](SPEC.md). Code layout, journal, backup, tamper demo: [docs/architecture.md](docs/architecture.md).

## Deploy

1. DNS → host; `.env` secrets and `CORS_ORIGINS` (exact HTTPS origin, no trailing slash).
2. `SITE_ADDRESS` for the public hostname (see `.env.example`); unset = HTTP on port 80.
3. `docker compose up --build -d`, both seed commands, confirm HTTPS/WSS and a **Live** lot from outside the LAN.

## Limitations

No password reset, seller self-registration, or real payments. Vitrine title filter is client-side on the current tab (up to 20 lots).

## Development

PostgreSQL 16 for backend tests. Compose does not publish `5432`; use local Postgres or [CI](.github/workflows/ci.yml).

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
