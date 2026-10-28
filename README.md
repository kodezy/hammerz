# Hammerz

Simulated live auctions: Met catalog lots, USD wallets, WebSocket bidding, settlement receipts, and a tamper-evident audit journal.

Ledger-only money — no payment processor.

## URLs

| Environment | Address |
| --- | --- |
| Local | **http://localhost** (HTTP) |
| Production | Public hostname in `SITE_ADDRESS` (HTTPS via Caddy) |

## Quick start

```bash
cp .env.example .env
# Set JWT_SECRET, HMAC_SECRET, ALIAS_SECRET (≥32 chars each).

docker compose up --build -d
docker compose exec backend seed-demo
docker compose exec backend seed-demo --ensure-live
```

Migrations run on backend startup.

`seed-demo` is idempotent (does not reset passwords, balances, or history).

`--ensure-live` adds a live lot when none exists.

## Accounts

Credentials are not shown in the app. Use after `seed-demo`.

| Email | Password | Role |
| --- | --- | --- |
| `seller@hammerz.test` | `Seller-Demo-2026!` | Seller |
| `bidder1@hammerz.test` | `Bidder1-Demo-2026!` | Bidder |
| `bidder2@hammerz.test` | `Bidder2-Demo-2026!` | Bidder |

**Fresh database (after first seed)**

- Seller: $0 total.
- Each bidder: $10,000 total.
- Bidder1: $1,500 committed on the live lot.

Sample lots: one live, one settled, one scheduled, one cancelled.

**Walkthrough**

- Seller → **Dashboard** → **New lot** (Met search).
- Bidder → **Auctions** → open a **Live** lot → bid.
- **Wallet** and **Bids** for balances and history.

## Routes

| Path | Purpose |
| --- | --- |
| `/` | Vitrine |
| `/login`, `/register` | Auth |
| `/seller` | Lots, Met search, proceeds |
| `/wallet` | Balances, deposits |
| `/bids` | Participations |
| `/lots/:id` | Lot room (REST + WebSocket) |
| `/lots/:id/audit` | Integrity check |
| `/receipts/:id` | Settlement receipt |

**More detail**

- Product rules and API — [SPEC.md](SPEC.md)
- Code map, journal, backup, tamper demo — [docs/architecture.md](docs/architecture.md)

## Deploy

1. Point DNS at the host.

2. In `.env`: set secrets and `CORS_ORIGINS` to the exact HTTPS origin (no trailing slash).

3. Set `SITE_ADDRESS` to the public hostname (see `.env.example`).  
   Leave unset for local HTTP on port 80 only.

4. Run `docker compose up --build -d`, then both seed commands.

5. From outside your LAN: confirm HTTPS, login, bid, WebSocket updates, audit/receipt pages, and at least one **Live** lot.

## Limitations

- No password reset.
- No seller self-registration.
- No real payments.
- Vitrine title filter is client-side on the current tab only (up to 20 lots).

## Development

Backend tests need PostgreSQL 16.

Compose does not publish `5432` by default — use local Postgres or match [CI](.github/workflows/ci.yml).

**Backend**

```bash
cd backend && uv sync --extra dev
export DATABASE_URL=postgresql+psycopg://hammerz:hammerz@127.0.0.1:5432/hammerz
export JWT_SECRET=test-secret-32-chars-minimum!!
export HMAC_SECRET=test-secret-32-chars-minimum!!
export ALIAS_SECRET=test-secret-32-chars-minimum!!
uv run ruff format . && uv run ruff check . && uv run pytest -q
```

**Frontend**

```bash
cd frontend && npm ci && npm run test && npm run build
cd frontend && npm run dev
```
