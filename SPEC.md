# Hammerz — MVP specification

**Version:** 0.5 (2026-10-28, aligned with implementation)

**Run the app:** [README.md](README.md) · **Stack, journal, ops:** [docs/architecture.md](docs/architecture.md) · **Agents:** [AGENTS.md](AGENTS.md)

Simulated live art auctions: Met catalog snapshots, USD wallets, WebSocket room updates, public audit and receipts. No real payments.



## Scope

**In:** seller and bidder roles; lot lifecycle; simulated deposits; bid rules, reserves, anti-snipe, settlement; public audit and receipts; English product UI; Docker Compose; automated tests for critical rules.

**Out:** real payments, password reset, email verification, public seller registration, multi-region HA, free-form wallet transfers.

Public `/register` creates **bidder** accounts with $0 wallets. Sellers are provisioned via `seed-demo` only.

## Roles

| Action | Guest | Seller | Bidder |
| --- | :---: | :---: | :---: |
| Vitrine, lot room, public bid history, audit, receipt | Yes | Yes | Yes |
| Create / manage own lots, cancel, proceeds | No | Yes | No |
| Simulated deposit, bid, wallet, bids list | No | No | Yes |

## Auth and session

- Passwords: Argon2; 8–128 characters. Email normalized; unique in DB.
- Short-lived access JWT in frontend memory only (not `localStorage` / `sessionStorage`).
- Persistent sign-in: HttpOnly cookie `hammerz_refresh` and `POST /api/v1/auth/refresh`.
- Logout revokes refresh and clears private client caches.
- Server enforces role and lot ownership; client-supplied user IDs are not trusted.

## UI routes

See [README.md](README.md). Product copy is English. No demo mode, role picker, or in-app evaluation credentials.

Personal bid states: `NOT_PARTICIPATING`, `LEADING`, `OUTBID`, `WON`, `LOST`, `CANCELLED`. Show specific rejection reasons (below minimum, insufficient funds, already leading, not started, ended, cancelled, audit unavailable). Countdown and live/scheduled labels use server time from REST/WS snapshots.

## Auction states

Persisted: `OPEN`, `CLOSED`, `CANCELLED`.

| Condition | Display |
| --- | --- |
| `OPEN` and `db_now < starts_at` | `SCHEDULED` |
| `OPEN` and `starts_at <= db_now < ends_at` | `LIVE` |
| `OPEN` and `db_now >= ends_at` | `FINALIZING` |
| `CLOSED` | `CLOSED` |
| `CANCELLED` | `CANCELLED` |

Vitrine tabs hide cancelled lots; ended tab may show `FINALIZING`. Lot config (opening bid, increment, catalog snapshot) is immutable after create; only anti-snipe may change `ends_at`.

## Money

- Integer USD cents everywhere; `currency: "USD"` on monetary API fields; display with `en-US`.
- `available_cents = total_cents - committed_cents` with DB constraints keeping both non-negative and committed ≤ total.
- Leader reserve on each open lot counts toward committed. Ledger records separate total and committed deltas (`DEPOSIT_SIMULATED`, `BID_RESERVE`, `OUTBID_RELEASE`, `CANCELLATION_RELEASE`, settlement types, etc.) in the same transaction as balance updates.

## Bid acceptance

Accept only when:

1. Authenticated bidder; lot `OPEN`; `starts_at <= accepted_at < ends_at`.
2. Bidder is not current leader.
3. First bid ≥ opening; later bids ≥ current + minimum increment.
4. Available balance covers full bid (including other lot reserves).
5. Audit journal writable and lot history consistent with evidence.

`accepted_at` from `SELECT clock_timestamp()` **after** required locks — not client time or transaction start.

## Anti-snipe

If `0 < old_ends_at - accepted_at <= 120` seconds: `new_ends_at = old_ends_at + 2 minutes` (not `accepted_at + 2`). Reject when `accepted_at == ends_at`.

## Cancellation [EXTRA]

Owner may cancel `OPEN` lot before `ends_at` (scheduled or live). No bids: reason optional. With bids: public reason required, 10–500 characters after trim. Releases **current leader’s** reserve only; preserves bid history and audit. No settlement or winner receipt. Idempotent retry returns original outcome.

## Settlement

Background job closes expired `OPEN` lots. With bids: debit winner, credit seller, settlement + public receipt, `CLOSED`. Without bids: close with no winner. One settlement and one receipt per lot. If audit evidence is missing or inconsistent, do not close; keep reserve until safe recovery.

## Lock order [DECISION]

Audited mutations: journal lock → auction `FOR UPDATE` → wallets by ascending UUID. Deposits: wallet only. Catalog HTTP completes before the short create transaction.

## Idempotency

Header `Idempotency-Key` (UUID) required on bid, deposit, and cancel.

- Same key + same body → stored result (including after lot state changes).
- Same key + different body → `409 IDEMPOTENCY_KEY_REUSED`.
- Audited success requires journal COMMIT, not only DB row; uncertain outcome → `202 OPERATION_PENDING` — retry with the same key.

## Audit (summary)

External append-only JSONL journal on `audit_data` (not in Postgres). PREPARE + fsync before DB commit; COMMIT or ABORT after known DB outcome. Pending prepare blocks new audited writes (`AUDIT_UNAVAILABLE`). Public verification: `VERIFIED`, `TAMPERED`, `UNVERIFIABLE`. Public history uses per-lot aliases only.

Tamper demo, backup pairing, and crash behavior: [docs/architecture.md](docs/architecture.md).

## REST `/api/v1`

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/register` | Public | Register bidder + zero wallet |
| POST | `/auth/login` | Public | Login |
| POST | `/auth/refresh` | Cookie | New access token |
| GET | `/auth/me` | Auth | Profile and role |
| GET | `/catalog/search` | Seller | Met search |
| POST | `/auctions` | Seller | Create lot |
| GET | `/auctions` | Public | Vitrine (paginated) |
| GET | `/auctions/{id}` | Public | Lot snapshot + server time |
| POST | `/auctions/{id}/bids` | Bidder | Place bid |
| POST | `/auctions/{id}/cancel` | Owner | Cancel lot |
| GET | `/auctions/{id}/bids` | Public | Pseudonymous bid history |
| GET | `/auctions/{id}/audit` | Public | Verification + events |
| GET | `/seller/auctions` | Seller | Own lots and proceeds |
| GET | `/me/auctions/{id}/status` | Bidder | Private position |
| GET | `/wallet` | Bidder | Balances |
| POST | `/wallet/deposits` | Bidder | Simulated deposit |
| GET | `/me/bids` | Bidder | Bidder participations by tab |
| GET | `/receipts/{id}` | Public | Settlement receipt |
| GET | `/health/live` | Public | Process up |
| GET | `/health/ready` | Public | DB + journal ready for audited writes |

Errors: `{ code, message, details?, request_id }`. Notable HTTP: `202 OPERATION_PENDING`, `503 AUDIT_UNAVAILABLE` before effect.

## WebSocket

Public `/ws/auctions/{auction_id}` for fan-out after DB commit and journal COMMIT. Bids only via REST. Frame types include `auction.snapshot`, `bid.accepted`, `auction.cancelled`, `auction.closed`. Client reconciles by `auction.version`; gap or reconnect triggers REST refetch.

## Met catalog

Search and object fetch use the [Met Collection API](https://metmuseum.github.io/) during seller import; published lots use local `catalog_items` snapshots. Met outage must not break existing vitrine, rooms, audit, or receipts.

## Demo seed

```bash
docker compose exec backend seed-demo
docker compose exec backend seed-demo --ensure-live
```

Idempotent: does not reset passwords, balances, or history. Credentials and expected balances: [README.md](README.md).

## References

- Met Collection API: https://metmuseum.github.io/
- PostgreSQL 16 transaction isolation: https://www.postgresql.org/docs/16/transaction-iso.html
- Caddy automatic HTTPS: https://caddyserver.com/docs/automatic-https
