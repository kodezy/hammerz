# Hammerz

Hammerz is a simulated live-auction platform: USD wallets, catalog lots from [The Met Collection API](https://metmuseum.github.io/), real-time bidding with anti-snipe extensions, settlement receipts, and a tamper-evident audit journal. Deposits and payouts are internal ledger entries only—there is no payment integration.

## Quick start

```bash
cp .env.example .env
# Set JWT_SECRET, HMAC_SECRET, and ALIAS_SECRET (at least 32 characters each).

docker compose up --build -d
docker compose exec backend seed-demo
docker compose exec backend seed-demo --ensure-live
```

Open **http://localhost**. The backend runs database migrations on startup.

**Public deploy:** terminate TLS in front of Caddy (port 80). Set `JWT_SECRET`, `HMAC_SECRET`, and `ALIAS_SECRET` to unique values of at least 32 characters. Set `CORS_ORIGINS` to your public site origin only (for example `https://auctions.example.com`) so live lot WebSockets pass the Origin check.

## Demo accounts

Share these credentials with anyone using a stack where demo data has been loaded. They are not shown inside the app.

| Email | Password | Role |
| --- | --- | --- |
| `seller@hammerz.test` | `Seller-Demo-2026!` | Seller |
| `bidder1@hammerz.test` | `Bidder1-Demo-2026!` | Bidder |
| `bidder2@hammerz.test` | `Bidder2-Demo-2026!` | Bidder |

After the **first** successful seed, bidder wallets are approximately:

| Account | Total | Committed | Available |
| --- | --- | --- | --- |
| `bidder1@hammerz.test` | $10,000.00 | $1,500.00 | $8,500.00 |
| `bidder2@hammerz.test` | $10,000.00 | $1,500.00 | $8,500.00 |

The seller dashboard reports about **$2,400** in proceeds from a settled demo lot. Seed runs are **idempotent** (they do not reset passwords, balances, or history). New registrations start at **$0** until the user adds funds.

**Try it:** sign in as the seller to review lots on the dashboard; sign in as a bidder to open a live lot from **Auctions** and place a bid. Use **Add funds** if demo balances were spent.

## Documentation

Stack and module layout: [docs/architecture.md](docs/architecture.md). Agent map: [AGENTS.md](AGENTS.md).

## Development

PostgreSQL on `localhost:5432` with the same credentials as Compose:

```bash
cd backend && uv sync --extra dev
export DATABASE_URL=postgresql+psycopg://hammerz:hammerz@127.0.0.1:5432/hammerz
export JWT_SECRET=test-secret-32-chars-minimum!!
export HMAC_SECRET=test-secret-32-chars-minimum!!
export ALIAS_SECRET=test-secret-32-chars-minimum!!
uv run ruff format .
uv run ruff check .
uv run pytest -q
```

Frontend dev server (API on `:8000`; Vite proxies `/api` and `/ws`):

```bash
cd frontend && npm install && npm run dev
```

Production build: `cd frontend && npm run build`
