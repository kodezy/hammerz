# Hammerz

Hammerz is a simulated live-auction platform: USD wallets, catalog lots from [The Met Collection API](https://metmuseum.github.io/), real-time bidding with anti-snipe extensions, settlement receipts, and a tamper-evident audit journal. Deposits and payouts are internal ledger entries only—there is no payment integration.

**Public URL:** TBA (fill in after deploy). **Repository:** currently private until published for evaluation.

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

The seller dashboard reports about **$2,400** in proceeds from a settled demo lot. The seed also creates **live**, **scheduled**, and **cancelled** lots (see seller **Cancelled** tab). Seed runs are **idempotent** (they do not reset passwords, balances, or history). New registrations start at **$0** until the user adds funds.

The spec’s minimal one-live-lot balance table is an example; this seed uses multiple lots, so both bidders may show committed funds.

**Try it:** sign in as the seller to review lots on the dashboard; sign in as a bidder to open a live lot from **Auctions** and place a bid. Use **Add funds** if demo balances were spent.

## Routes

| Path | Purpose |
| --- | --- |
| `/` | Auction vitrine (Live / Upcoming / Ended) |
| `/login`, `/register` | Auth |
| `/seller` | Met catalog search, lot management, proceeds |
| `/wallet` | Bidder balances and simulated deposits |
| `/my-wins` | Participations and receipts |
| `/lots/:id` | Lot room (bids, WebSocket) |
| `/lots/:id/audit` | Public integrity check and audit events |
| `/receipts/:id` | Public settlement receipt |

Full behavior: [SPEC.md](SPEC.md). Stack map: [docs/architecture.md](docs/architecture.md). Agent map: [AGENTS.md](AGENTS.md).

## Rules (summary)

- USD integer cents everywhere; display uses `en-US`.
- First bid ≥ opening; later bids ≥ current + minimum increment; leaders cannot raise their own bid.
- Anti-snipe: if a bid is accepted when `0 < ends_at - accepted_at ≤ 120s`, set `ends_at = old_ends_at + 2 minutes` (not `accepted_at + 2`).
- Cancel with bids requires a public reason (10–500 characters after trim). Without bids, reason is optional.
- Audited writes (bids, cancel, create, settle) use an external HMAC journal (`audit_data` volume). If evidence cannot be verified, new bids are refused (`AUDIT_UNAVAILABLE`).

## Audit and tamper demo (local only)

1. Open `/lots/:id/audit` for a seeded lot — expect **VERIFIED** and event rows (aliases only, no email).
2. On a **disposable** database, tamper one bid row, then reload audit:

```sql
UPDATE bids SET amount_cents = amount_cents + 1 WHERE auction_id = '<lot-uuid>';
```

Expect **TAMPERED** and reason codes on the audit page and on the receipt’s integrity banner.

Do not “fix” tampering by wiping the journal while keeping an old database snapshot.

## Journal protocol (crash behavior)

- **PREPARE** is appended and fsync’d before PostgreSQL commit; **COMMIT** or **ABORT** after a known DB outcome.
- If the outcome is unknown after a crash, the API may return **202 OPERATION_PENDING**; retry with the same idempotency key.
- A **PREPARE** without a durable decision after restart stays pending; audited mutations stay blocked until an admin resolves it. The app does not infer ABORT from missing DB rows.

## Backup

Coherent recovery needs **both** `postgres_data` and `audit_data` (plus secrets). Do not restore an old DB with a new empty journal to hide tampering.

## Seed command

The implementation command is `seed-demo` 

```bash
docker compose exec backend seed-demo
docker compose exec backend seed-demo --ensure-live
```

`--ensure-live` creates a live lot only when none exists; it does not reset balances or history.

## Session note

JWT is stored in `sessionStorage` (`hammerz:token`), so reload on the same tab keeps you signed in. Spec §3.2 described memory-only sessions; this is an intentional UX choice.

## Optional features delivered

- Light/dark theme toggle (header).
- Vitrine title filter on the current tab (client-side, up to 20 lots per tab).
- Seller **Proceeds by lot** bar chart on the Ended tab.

## Limitations

- No password reset, seller self-registration, or real payments.
- Vitrine search does not query the server across tabs or pages.
- Public GitHub URL and HTTPS/WSS deploy: fill in when ready.

## AI usage



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

Frontend:

```bash
cd frontend && npm run test
cd frontend && npm ci && npm run build
cd frontend && npm run dev
```
