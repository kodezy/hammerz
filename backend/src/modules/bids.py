import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.errors import AppError, ErrorCode
from src.core.limits import limiter
from src.core.money import available
from src.db.tables import Auction, Bid, Event, Key, Ledger, User, Wallet
from src.modules import audit as audit_module
from src.modules.alias import display_alias
from src.modules.journal import Journal

Position = Literal[
    "NOT_PARTICIPATING",
    "LEADING",
    "OUTBID",
    "WON",
    "LOST",
    "CANCELLED",
]


@dataclass
class BidResult:
    bid_id: uuid.UUID
    auction_id: uuid.UUID
    amount_cents: int
    sequence: int
    version: int
    ends_at: datetime
    response: dict[str, Any]


def _db_now(session: Session) -> datetime:
    return session.scalar(select(func.clock_timestamp()))


def _min_required_bid(auction: Auction) -> int:
    if auction.current_bid_cents is None:
        return auction.opening_bid_cents
    return auction.current_bid_cents + auction.minimum_increment_cents


def _auction_live(auction: Auction, now: datetime) -> None:
    if auction.status == "CANCELLED":
        raise AppError(409, ErrorCode.AUCTION_CANCELLED, "Auction cancelled")
    if auction.status == "CLOSED":
        raise AppError(409, ErrorCode.AUCTION_CLOSED, "Auction closed")
    if now < auction.starts_at:
        raise AppError(409, ErrorCode.AUCTION_NOT_STARTED, "Auction not started")
    if now >= auction.ends_at:
        raise AppError(409, ErrorCode.AUCTION_NOT_LIVE, "Auction not live")


def _next_bid_sequence(session: Session, auction_id: uuid.UUID) -> int:
    current = session.scalar(
        select(func.coalesce(func.max(Bid.sequence), 0)).where(Bid.auction_id == auction_id)
    )
    return int(current) + 1


def _next_event_sequence(session: Session, auction_id: uuid.UUID) -> int:
    current = session.scalar(
        select(func.coalesce(func.max(Event.sequence), 0)).where(Event.auction_id == auction_id)
    )
    return int(current) + 1


def _prev_event_hash(session: Session, auction_id: uuid.UUID) -> str:
    row = session.scalar(
        select(Event.event_hash)
        .where(Event.auction_id == auction_id)
        .order_by(Event.sequence.desc())
        .limit(1)
    )
    return row if row else audit_module.genesis_event_hash()


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _bid_response(
    session: Session,
    auction: Auction,
    bid: Bid,
    bidder: User,
) -> dict[str, Any]:
    alias = display_alias(auction.id, bidder.id, bidder.role)
    return {
        "accepted_at": _iso(bid.accepted_at),
        "amount_cents": bid.amount_cents,
        "auction_id": str(auction.id),
        "bidder_alias": alias,
        "currency": "USD",
        "ends_at": _iso(auction.ends_at),
        "id": str(bid.id),
        "sequence": bid.sequence,
        "version": auction.version,
    }


def _idempotency_early(
    session: Session,
    journal: Journal,
    bidder_id: uuid.UUID,
    idempotency_key: uuid.UUID,
    fingerprint: str,
) -> dict[str, Any] | None:
    existing = session.scalar(
        select(Key).where(
            Key.actor_id == bidder_id,
            Key.idempotency_key == idempotency_key,
        )
    )
    if existing is None:
        return None
    if existing.fingerprint != fingerprint:
        raise AppError(409, ErrorCode.IDEMPOTENCY_KEY_REUSED, "Idempotency key reused")
    if existing.response_json and existing.status_code:
        if existing.operation_id and not journal.has_commit(existing.operation_id):
            raise AppError(
                202,
                ErrorCode.OPERATION_PENDING,
                "Operation pending",
                details={"operation_id": str(existing.operation_id)},
            )
        return existing.response_json
    raise AppError(
        202,
        ErrorCode.OPERATION_PENDING,
        "Operation pending",
        details={"operation_id": str(existing.operation_id) if existing.operation_id else None},
    )


async def place_bid(
    session: Session,
    journal: Journal,
    bidder_id: uuid.UUID,
    auction_id: uuid.UUID,
    amount_cents: int,
    idempotency_key: uuid.UUID,
    fingerprint: str,
) -> BidResult:
    if journal.blocked:
        raise AppError(503, ErrorCode.AUDIT_UNAVAILABLE, "Audit journal unavailable")
    if journal.pending_prepare() is not None:
        raise AppError(503, ErrorCode.AUDIT_UNAVAILABLE, "Audit journal has pending prepare")
    if not limiter.allow(f"bid:{bidder_id}", 30):
        raise AppError(429, ErrorCode.RATE_LIMITED, "Too many bids")

    cached = _idempotency_early(session, journal, bidder_id, idempotency_key, fingerprint)
    if cached is not None:
        bid = session.scalar(select(Bid).where(Bid.id == uuid.UUID(cached["id"])))
        auction = session.get(Auction, auction_id)
        if bid is None or auction is None:
            return BidResult(
                bid_id=uuid.UUID(cached["id"]),
                auction_id=auction_id,
                amount_cents=int(cached["amount_cents"]),
                sequence=int(cached["sequence"]),
                version=int(cached["version"]),
                ends_at=cached["ends_at"],
                response=cached,
            )
        return BidResult(
            bid_id=bid.id,
            auction_id=auction_id,
            amount_cents=bid.amount_cents,
            sequence=bid.sequence,
            version=auction.version,
            ends_at=auction.ends_at,
            response=cached,
        )

    bidder = session.get(User, bidder_id)
    if bidder is None or bidder.role != "BIDDER":
        raise AppError(403, ErrorCode.FORBIDDEN, "Bidder access required")

    settings = get_settings()
    if amount_cents <= 0 or amount_cents > settings.max_bid_cents:
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "Invalid bid amount")

    operation_id = uuid.uuid4()
    bid_id = uuid.uuid4()

    async with journal._async_lock:
        existing = session.scalar(
            select(Key).where(
                Key.actor_id == bidder_id,
                Key.idempotency_key == idempotency_key,
            )
        )
        if existing:
            if existing.fingerprint != fingerprint:
                raise AppError(409, ErrorCode.IDEMPOTENCY_KEY_REUSED, "Idempotency key reused")
            if existing.response_json:
                if existing.operation_id and not journal.has_commit(existing.operation_id):
                    raise AppError(
                        202,
                        ErrorCode.OPERATION_PENDING,
                        "Operation pending",
                        details={"operation_id": str(existing.operation_id)},
                    )
                return BidResult(
                    bid_id=uuid.UUID(existing.response_json["id"]),
                    auction_id=auction_id,
                    amount_cents=int(existing.response_json["amount_cents"]),
                    sequence=int(existing.response_json["sequence"]),
                    version=int(existing.response_json["version"]),
                    ends_at=existing.response_json["ends_at"],
                    response=existing.response_json,
                )

        try:
            session.execute(text("SET LOCAL lock_timeout = '5s'"))
            auction = session.scalar(
                select(Auction).where(Auction.id == auction_id).with_for_update()
            )
            if auction is None:
                raise AppError(404, ErrorCode.NOT_FOUND, "Auction not found")
            if auction.seller_id == bidder_id:
                raise AppError(403, ErrorCode.FORBIDDEN, "Seller cannot bid")

            now = _db_now(session)
            _auction_live(auction, now)

            if auction.current_leader_id == bidder_id:
                raise AppError(409, ErrorCode.ALREADY_LEADING, "Already leading")

            min_bid = _min_required_bid(auction)
            if amount_cents < min_bid:
                raise AppError(409, ErrorCode.BID_TOO_LOW, "Bid too low")

            if now >= auction.ends_at:
                raise AppError(409, ErrorCode.AUCTION_NOT_LIVE, "Auction not live")

            wallet_ids: list[uuid.UUID] = [bidder_id]
            prev_leader_id = auction.current_leader_id
            if prev_leader_id is not None and prev_leader_id != bidder_id:
                wallet_ids.append(prev_leader_id)
            wallet_ids.sort()

            wallets: dict[uuid.UUID, Wallet] = {}
            for uid in wallet_ids:
                wallet = session.scalar(
                    select(Wallet).where(Wallet.user_id == uid).with_for_update()
                )
                if wallet is None:
                    raise AppError(404, ErrorCode.NOT_FOUND, "Wallet not found")
                wallets[uid] = wallet

            bidder_wallet = wallets[bidder_id]
            if available(bidder_wallet.total_cents, bidder_wallet.committed_cents) < amount_cents:
                raise AppError(409, ErrorCode.INSUFFICIENT_FUNDS, "Insufficient funds")

            old_ends_at = auction.ends_at
            new_ends_at = old_ends_at
            remaining = (old_ends_at - now).total_seconds()
            if 0 < remaining <= 120:
                new_ends_at = old_ends_at + timedelta(minutes=2)

            await asyncio.to_thread(
                journal.append_prepare,
                {
                    "operation_id": str(operation_id),
                    "fingerprint": fingerprint,
                    "event": {"type": "BID_ACCEPTED"},
                },
            )

            reserve_deltas: list[dict[str, Any]] = []
            if prev_leader_id is not None and prev_leader_id in wallets:
                prev_wallet = wallets[prev_leader_id]
                release = int(auction.current_bid_cents or 0)
                prev_wallet.committed_cents -= release
                session.add(
                    Ledger(
                        wallet_id=prev_wallet.id,
                        operation_id=operation_id,
                        type="OUTBID_RELEASE",
                        auction_id=auction_id,
                        total_delta_cents=0,
                        committed_delta_cents=-release,
                    )
                )
                reserve_deltas.append(
                    {
                        "alias": display_alias(auction_id, prev_leader_id, "BIDDER"),
                        "committed_delta_cents": -release,
                        "total_delta_cents": 0,
                        "type": "OUTBID_RELEASE",
                    }
                )

            bidder_wallet.committed_cents += amount_cents
            session.add(
                Ledger(
                    wallet_id=bidder_wallet.id,
                    operation_id=operation_id,
                    type="BID_RESERVE",
                    auction_id=auction_id,
                    total_delta_cents=0,
                    committed_delta_cents=amount_cents,
                )
            )
            reserve_deltas.append(
                {
                    "alias": display_alias(auction_id, bidder_id, bidder.role),
                    "committed_delta_cents": amount_cents,
                    "total_delta_cents": 0,
                    "type": "BID_RESERVE",
                }
            )

            bid_sequence = _next_bid_sequence(session, auction_id)
            event_sequence = _next_event_sequence(session, auction_id)
            prev_hash = _prev_event_hash(session, auction_id)
            prev_version = auction.version
            auction.version += 1
            auction.current_bid_cents = amount_cents
            auction.current_leader_id = bidder_id
            auction.ends_at = new_ends_at

            bid = Bid(
                id=bid_id,
                auction_id=auction_id,
                bidder_id=bidder_id,
                amount_cents=amount_cents,
                accepted_at=now,
                sequence=bid_sequence,
                operation_id=operation_id,
            )
            session.add(bid)
            session.flush()

            alias = display_alias(auction_id, bidder_id, bidder.role)
            occurred_at = datetime.now(UTC)
            payload = audit_module.build_event_payload(
                deployment_id=settings.deployment_id,
                operation_id=operation_id,
                auction_id=auction_id,
                sequence=event_sequence,
                event_type="BID_ACCEPTED",
                prev_event_hash=prev_hash,
                prev_auction_version=prev_version,
                auction_version=auction.version,
                actor_id=bidder_id,
                actor_alias=alias,
                occurred_at=occurred_at,
                extra={
                    "amount_cents": amount_cents,
                    "bid_id": str(bid_id),
                    "bid_sequence": bid_sequence,
                    "ends_at": new_ends_at,
                    "previous_ends_at": old_ends_at,
                    "reserve_deltas": reserve_deltas,
                },
            )
            event_hash = audit_module.sign_event(payload, prev_hash)
            audit_module.persist_event(
                session,
                auction_id=auction_id,
                sequence=event_sequence,
                event_type="BID_ACCEPTED",
                operation_id=operation_id,
                payload=payload,
                prev_hash=prev_hash,
                event_hash=event_hash,
                bid_id=bid_id,
            )

            response = _bid_response(session, auction, bid, bidder)
            session.add(
                Key(
                    actor_id=bidder_id,
                    idempotency_key=idempotency_key,
                    fingerprint=fingerprint,
                    operation_id=operation_id,
                    status_code=200,
                    response_json=response,
                )
            )
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                await asyncio.to_thread(journal.append_abort, operation_id)
                raise AppError(
                    409, ErrorCode.IDEMPOTENCY_KEY_REUSED, "Idempotency key reused"
                ) from exc
            await asyncio.to_thread(journal.append_commit, operation_id)
            session.refresh(auction)
            session.refresh(bid)
            return BidResult(
                bid_id=bid.id,
                auction_id=auction_id,
                amount_cents=bid.amount_cents,
                sequence=bid.sequence,
                version=auction.version,
                ends_at=auction.ends_at,
                response=response,
            )
        except AppError:
            session.rollback()
            if journal.pending_prepare() is not None:
                await asyncio.to_thread(journal.append_abort, operation_id)
            raise
        except Exception:
            session.rollback()
            if journal.pending_prepare() is not None:
                await asyncio.to_thread(journal.append_abort, operation_id)
            raise


def list_bids(
    session: Session,
    journal: Journal,
    auction_id: uuid.UUID,
    *,
    before_sequence: int | None,
    after_sequence: int | None,
    limit: int,
) -> dict[str, Any]:
    from src.modules import audit as audit_module

    auction = session.get(Auction, auction_id)
    if auction is None:
        raise AppError(404, ErrorCode.NOT_FOUND, "Auction not found")
    integrity = audit_module.verify_auction(session, journal, auction_id)
    if integrity["status"] == "TAMPERED":
        raise AppError(409, ErrorCode.INTEGRITY_CONFLICT, "Bid history integrity conflict")

    stmt = select(Bid).where(Bid.auction_id == auction_id)
    if after_sequence is not None:
        stmt = stmt.where(Bid.sequence > after_sequence).order_by(Bid.sequence.asc())
    elif before_sequence is not None:
        stmt = stmt.where(Bid.sequence < before_sequence).order_by(Bid.sequence.desc())
    else:
        stmt = stmt.order_by(Bid.sequence.desc())
    rows = session.scalars(stmt.limit(limit)).all()
    if not after_sequence:
        rows = list(rows)

    items: list[dict[str, Any]] = []
    for bid in rows:
        user = session.get(User, bid.bidder_id)
        role = user.role if user else "BIDDER"
        items.append(
            {
                "accepted_at": bid.accepted_at,
                "amount_cents": bid.amount_cents,
                "bidder_alias": display_alias(auction_id, bid.bidder_id, role),
                "currency": "USD",
                "sequence": bid.sequence,
            }
        )
    return {"items": items, "limit": limit}


def participant_position(session: Session, user_id: uuid.UUID, auction_id: uuid.UUID) -> dict[str, Any]:
    auction = session.get(Auction, auction_id)
    if auction is None:
        raise AppError(404, ErrorCode.NOT_FOUND, "Auction not found")
    participated = session.scalar(
        select(func.count()).select_from(Bid).where(
            Bid.auction_id == auction_id,
            Bid.bidder_id == user_id,
        )
    )
    if not participated:
        position: Position = "NOT_PARTICIPATING"
    elif auction.status == "CANCELLED":
        position = "CANCELLED"
    elif auction.status == "CLOSED":
        if auction.current_leader_id == user_id:
            position = "WON"
        else:
            position = "LOST"
    elif auction.current_leader_id == user_id:
        position = "LEADING"
    else:
        position = "OUTBID"
    reserved_cents = None
    if position == "LEADING" and auction.current_bid_cents is not None:
        reserved_cents = auction.current_bid_cents
    return {
        "auction_id": str(auction_id),
        "position": position,
        "reserved_cents": reserved_cents,
    }
