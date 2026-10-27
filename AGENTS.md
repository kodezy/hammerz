# AGENTS.md

## Purpose

Map for coding agents. Prefer matching nearby files over new layers. Details live in linked docs — do not paste research or specs here.

## Repository map

- Architecture: `docs/architecture.md`
- Product onboarding: `README.md`
- Backend: `backend/app/` (`api/`, `modules/`, `core/`, `db/`)
- Frontend: `frontend/src/` (`app/`, `pages/`, `features/`, `components/`, `lib/`)
- Edge: `infra/Caddyfile`, `compose.yaml`

## Commands

Bootstrap:

```bash
cp .env.example .env   # JWT_SECRET, HMAC_SECRET, ALIAS_SECRET ≥ 32 chars, not change-me
docker compose up --build -d
docker compose exec backend seed-demo
```

Local backend (Postgres reachable; CI uses a service, default Compose does not publish 5432):

```bash
cd backend && uv sync --extra dev
export DATABASE_URL=postgresql+psycopg://hammerz:hammerz@127.0.0.1:5432/hammerz
export JWT_SECRET=test-secret-32-chars-minimum!!
export HMAC_SECRET=test-secret-32-chars-minimum!!
export ALIAS_SECRET=test-secret-32-chars-minimum!!
```

Fast validation: `cd backend && uv run ruff check .`

Full backend tests: `cd backend && uv run pytest -q`

Frontend: `cd frontend && npm ci && npm run lint && npm run build`

Architecture checks: none — see `docs/architecture.md`.

Do not seed on API startup. Seed is `docker compose exec backend seed-demo` only.

## Core invariants

- USD integer cents. No floats in APIs or ledger. Convert dollars→cents on the client (`parseDollarsToCents`).
- Bid, deposit, and cancel require header `Idempotency-Key` (UUID). Same key + body returns the stored result; different body → `IDEMPOTENCY_KEY_REUSED`.
- Journal PREPARE before Postgres commit; COMMIT/ABORT after a known DB outcome. Pending prepare blocks further audited writes (`AUDIT_UNAVAILABLE` / `OPERATION_PENDING`).
- Errors are `AppError` + `ErrorCode` (`{code, message, details?, request_id}`). Do not invent a parallel error type.
- Public UI copy is English. No demo-mode chrome, role picker, or auto-login.
- One-word Python modules (`bids.py`); pytest `test_<word>.py`; React pages `Lot.tsx`. Empty `__init__.py` is fine. Do not add Repository/UoW/`CurrencyProvider`/theme-cloned pages.
- Schema changes go through Alembic. Driver is `postgresql+psycopg://` only.
- Colors: Tailwind v4 tokens in `frontend/src/styles.css`. Do not scatter raw hex in components.
- JWT: keep off `localStorage`. Idempotency retry keys may use `localStorage` via `lib/pending.ts`.
- Catalog HTTP happens before the short create transaction. Met is the catalog source; snapshot fields stay in `catalog_items`.
- Sellers are provisioned by seed (`auth.provision`), not public register.

Enforced by CI: `ruff check` and `pytest` (backend); `npm run build` (tsc + Vite). Frontend `oxlint` is local-only.

## Context routing

When changing module boundaries, lock order, journal, or money: read `docs/architecture.md` and the owning file under `backend/app/modules/`.

When changing HTTP contracts: `backend/app/api/` plus the matching `frontend/src/features/` client.

When changing UI: match `frontend/src/pages/` and `frontend/src/components/` already on the route; tokens in `frontend/src/styles.css`.

When changing Compose/Caddy/secrets: `compose.yaml`, `infra/Caddyfile`, `.env.example`.

Do not read all documentation before every task.

## Definition of done

- `ruff` / `pytest` / `npm run build` pass for the area you touched
- behavior matches the task (including empty, error, and pending-audit paths)
- no new abstraction unless an existing file already uses that pattern
- docs only if behavior or commands changed

## Local instructions

User chat in the session wins. This repo has a single root `AGENTS.md`.
