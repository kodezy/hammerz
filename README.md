# Hammerz

Simulated live-auction platform. USD-only simulated wallets, Met Museum catalog lots, concurrent bidding with anti-snipe, settlement receipts, and an HMAC-chained audit journal. Product UI is English; authoritative requirements are in [SPEC.md](SPEC.md).



## 1. Objective

Hammerz demonstrates a single-node auction platform: bidders deposit simulated funds, bid on real Met catalog snapshots, and receive public receipts; sellers create lots and settle automatically after `ends_at`. No real payments. All money is **USD** integer cents end-to-end.

## 2. Prerequisites and run

- Docker and Docker Compose
- Copy `.env.example` to `.env` and set strong `JWT_SECRET`, `HMAC_SECRET`, and `ALIAS_SECRET` (≥32 bytes recommended)

```bash
docker compose up --build -d
docker compose exec backend python -m app.modules.seed
docker compose exec backend python -m app.modules.seed --ensure-live
```

- Migrations run on backend startup (`app.boot`).
- Tests (PostgreSQL required):

```bash
cd backend && uv sync --extra dev
export DATABASE_URL=postgresql+psycopg://hammerz:hammerz@127.0.0.1:5432/hammerz
export JWT_SECRET=test-secret-32-chars-minimum!!
export HMAC_SECRET=test-secret-32-chars-minimum!!
export ALIAS_SECRET=test-secret-32-chars-minimum!!
uv run pytest -q
```

- Frontend dev (proxies API to port 8000):

```bash
cd frontend && npm install && npm run dev
```

## 3. Evaluation accounts

Provisioned by seed (not shown in the UI):

| Email | Password | Role |
| --- | --- | --- |
| `seller@hammerz.test` | `Seller-Eval-2026!` | Seller |
| `bidder1@hammerz.test` | `Bidder1-Eval-2026!` | Bidder |
| `bidder2@hammerz.test` | `Bidder2-Eval-2026!` | Bidder |

Sign in at `/login`. Bidders start with wallet balance from seed opening balances; public registration creates a bidder with **zero** balance until deposit.

## 4. Stack and layout

- **Compose:** Caddy (`web`) → SPA + reverse proxy `/api`, `/ws`, `/health`; FastAPI (`backend`); PostgreSQL 16
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Argon2, JWT, JSONL journal on `AUDIT_DIR`
- **Frontend:** React, TypeScript, Vite, Tailwind, TanStack Query
- Routes: `/`, `/login`, `/register`, `/seller`, `/wallet`, `/my-wins`, `/lots/:id`, `/lots/:id/audit`, `/receipts/:id`

## 5. Financial rules (summary)

- `available = total - committed`; reserves follow the current high bidder per open lot.
- Anti-snipe: bid accepted within 120s of `ends_at` extends end by 2 minutes.
- Cancellation releases the active reserve; settlement moves funds winner → seller once per lot.

## 6. Audit and threat model

- Append-only `journal.jsonl` with HMAC-SHA256 chain; PREPARE before DB commit, COMMIT/ABORT after.
- Public `/lots/:id/audit` and receipt integrity (`Verified` / `Changes detected` / `Unable to verify`).
- Secrets stay on the server; clients never see HMAC keys. Tampering tests belong in a disposable environment.

## 7. Pending operations and crashes

- If journal state is unknown after PREPARE, API returns `202 OPERATION_PENDING`; client keeps idempotency key in `localStorage` (`hammerz:pending:*`).
- Automatic recovery after partial failure is limited; admins reconcile journal vs DB before unblocking.

## 8. Operations

- Backup: PostgreSQL volume + `audit_data` volume.
- Keep a live lot for demos: `python -m app.modules.seed --ensure-live` (non-destructive).
- HTTPS: Caddy Automatic HTTPS on the public hostname.

## 9. Known gaps

- Deploy URL and live HTTPS verification are manual checklist items (SPEC §18).
- 

## 10. AI usage


