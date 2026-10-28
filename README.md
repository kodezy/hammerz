# Hammerz

Simulated live-auction platform: USD wallets, catalog lots from [The Met Collection API](https://metmuseum.github.io/), real-time bidding with anti-snipe extensions, settlement receipts, and a tamper-evident audit journal. Deposits and payouts are ledger entries only—no payment integration.

## Quick start

```bash
cp .env.example .env
# JWT_SECRET, HMAC_SECRET, ALIAS_SECRET — at least 32 characters each.

docker compose up --build -d
docker compose exec backend seed-demo
docker compose exec backend seed-demo --ensure-live
```

Open **http://localhost**. Migrations run on backend startup. Seed is idempotent (no reset of passwords, balances, or history). `--ensure-live` adds a live lot only when none exists.

**Deploy:** TLS in front of Caddy. Use unique secrets and set `CORS_ORIGINS` to the public site origin so WebSockets pass the Origin check.

## Demo accounts

Credentials are not shown in the app. Use after `seed-demo`.

| Email | Password | Role |
| --- | --- | --- |
| `seller@hammerz.test` | `Seller-Demo-2026!` | Seller |
| `bidder1@hammerz.test` | `Bidder1-Demo-2026!` | Bidder |
| `bidder2@hammerz.test` | `Bidder2-Demo-2026!` | Bidder |

After the first seed, bidder wallets are roughly $10,000 total with committed funds on active lots; the seller dashboard shows proceeds from a settled demo lot. New registrations start at $0 until **Add funds**.

Sign in as seller to manage lots; as bidder, open a live lot from **Auctions** and bid.

## Routes

| Path | Purpose |
| --- | --- |
| `/` | Vitrine (Live / Upcoming / Ended) |
| `/login`, `/register` | Auth |
| `/seller` | Met search, lots, proceeds |
| `/wallet` | Balances, simulated deposits |
| `/my-wins` | Participations and receipts |
| `/lots/:id` | Lot room (REST + WebSocket) |
| `/lots/:id/audit` | Public integrity check |
| `/receipts/:id` | Public settlement receipt |

Domain rules and API detail: [SPEC.md](SPEC.md). Stack, journal, backup: [docs/architecture.md](docs/architecture.md). Agents: [AGENTS.md](AGENTS.md).

## Limitations

- No password reset, seller self-registration, or real payments.
- Vitrine title filter is client-side on the current tab only (up to 20 lots).
- Sign-in persists via HttpOnly cookie `hammerz_refresh`; access JWT stays in memory only.

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
