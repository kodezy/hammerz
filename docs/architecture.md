# Architecture

Hammerz is a monorepo: Caddy serves the React SPA and proxies `/api`, `/ws`, and `/health` to a FastAPI backend backed by PostgreSQL. Audit journal files live on the `audit_data` volume.

Backend domain logic uses single-word modules under `backend/app/modules/` (`auth`, `bids`, `journal`, `settle`, …). HTTP routes sit in `backend/app/api/`. The frontend uses Vite, React, TanStack Query, and Tailwind v4 semantic tokens in `frontend/src/styles.css`.

Money is integer USD cents. Mutations use `Idempotency-Key`. The audit journal uses PREPARE / COMMIT / ABORT with an HMAC chain.
