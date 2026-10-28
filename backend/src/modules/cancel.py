import asyncio
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.errors import AppError, ErrorCode
from src.db.tables import Auction, Bid, Event, Key, Ledger, User, Wallet
from src.modules import auctions as auctions_module
from src.modules import audit as audit_module
from src.modules.alias import display_alias
from src.modules.journal import Journal


def _db_now(session: Session) -> datetime:
    return session.scalar(select(func.clock_timestamp()))


def _next_event_sequence(session: Session, auction_id: uuid.UUID) -> int:
    current = session.scalar(select(func.coalesce(func.max(Event.sequence), 0)).where(Event.auction_id == auction_id))
    return int(current) + 1


def _prev_event_hash(session: Session, auction_id: uuid.UUID) -> str:
    row = session.scalar(
        select(Event.event_hash).where(Event.auction_id == auction_id).order_by(Event.sequence.desc()).limit(1)
    )
    return row if row else audit_module.genesis_event_hash()


def _validate_reason(session: Session, auction_id: uuid.UUID, reason: str | None) -> str | None:
    has_bids = session.scalar(select(func.count()).select_from(Bid).where(Bid.auction_id == auction_id))
    if not has_bids:
        if reason is None or not reason.strip():
            return None
        trimmed = reason.strip()
        return trimmed if trimmed else None
    if reason is None or len(reason.strip()) < 10 or len(reason.strip()) > 500:
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "Cancellation reason required")
    return reason.strip()


def _idempotency_check(
    session: Session, seller_id: uuid.UUID, idempotency_key: uuid.UUID, fingerprint: str
) -> dict[str, Any] | None:
    existing = session.scalar(select(Key).where(Key.actor_id == seller_id, Key.idempotency_key == idempotency_key))
    if existing is None:
        return None
    if existing.fingerprint != fingerprint:
        raise AppError(409, ErrorCode.IDEMPOTENCY_KEY_REUSED, "Idempotency key reused")
    if existing.response_json:
        return existing.response_json
    raise AppError(202, ErrorCode.OPERATION_PENDING, "Operation pending")


async def cancel_auction(
    session: Session,
    journal: Journal,
    seller_id: uuid.UUID,
    auction_id: uuid.UUID,
    reason: str | None,
    idempotency_key: uuid.UUID,
    fingerprint: str,
) -> Auction:
    if journal.blocked:
        raise AppError(503, ErrorCode.AUDIT_UNAVAILABLE, "Audit journal unavailable")
    if journal.pending_prepare() is not None:
        raise AppError(503, ErrorCode.AUDIT_UNAVAILABLE, "Audit journal has pending prepare")

    cached = _idempotency_check(session, seller_id, idempotency_key, fingerprint)
    if cached is not None:
        return session.get(Auction, auction_id)

    settings = get_settings()
    operation_id = uuid.uuid4()

    async with journal._async_lock:
        existing = session.scalar(select(Key).where(Key.actor_id == seller_id, Key.idempotency_key == idempotency_key))
        if existing and existing.response_json:
            return session.get(Auction, auction_id)

        await asyncio.to_thread(
            journal.append_prepare,
            {"operation_id": str(operation_id), "fingerprint": fingerprint, "event": {"type": "AUCTION_CANCELLED"}},
        )
        try:
            session.execute(text("SET LOCAL lock_timeout = '5s'"))
            auction = session.scalar(select(Auction).where(Auction.id == auction_id).with_for_update())
            if auction is None:
                raise AppError(404, ErrorCode.NOT_FOUND, "Auction not found")
            if auction.seller_id != seller_id:
                raise AppError(403, ErrorCode.FORBIDDEN, "Not auction owner")
            if auction.status == "CANCELLED":
                snap = audit_module.json_safe_payload(auctions_module.get_auction(session, auction_id))
                session.add(
                    Key(
                        actor_id=seller_id,
                        idempotency_key=idempotency_key,
                        fingerprint=fingerprint,
                        operation_id=operation_id,
                        status_code=200,
                        response_json=snap,
                    )
                )
                session.commit()
                await asyncio.to_thread(journal.append_commit, operation_id)
                return auction
            if auction.status == "CLOSED":
                raise AppError(409, ErrorCode.AUCTION_CLOSED, "Auction closed")
            now = _db_now(session)
            if now >= auction.ends_at:
                raise AppError(409, ErrorCode.AUCTION_NOT_LIVE, "Auction finalizing or ended")

            stored_reason = _validate_reason(session, auction_id, reason)
            leader_id = auction.current_leader_id
            release: dict[str, Any] | None = None
            wallet_ids: list[uuid.UUID] = []
            if leader_id is not None:
                wallet_ids.append(leader_id)
            for uid in sorted(wallet_ids):
                wallet = session.scalar(select(Wallet).where(Wallet.user_id == uid).with_for_update())
                if wallet is None:
                    continue
                if uid == leader_id and auction.current_bid_cents:
                    amount = int(auction.current_bid_cents)
                    wallet.committed_cents -= amount
                    session.add(
                        Ledger(
                            wallet_id=wallet.id,
                            operation_id=operation_id,
                            type="CANCELLATION_RELEASE",
                            auction_id=auction_id,
                            total_delta_cents=0,
                            committed_delta_cents=-amount,
                        )
                    )
                    user = session.get(User, uid)
                    release = {
                        "alias": display_alias(auction_id, uid, user.role if user else "BIDDER"),
                        "amount_cents": amount,
                    }

            last_bid = session.scalar(
                select(Bid).where(Bid.auction_id == auction_id).order_by(Bid.sequence.desc()).limit(1)
            )
            prev_version = auction.version
            auction.version += 1
            auction.status = "CANCELLED"
            auction.cancelled_at = now
            auction.cancel_reason = stored_reason
            auction.cancelled_by_id = seller_id
            auction.current_bid_cents = None
            auction.current_leader_id = None

            event_sequence = _next_event_sequence(session, auction_id)
            prev_hash = _prev_event_hash(session, auction_id)
            seller = session.get(User, seller_id)
            alias = display_alias(auction_id, seller_id, seller.role if seller else "SELLER")
            from datetime import UTC

            occurred_at = datetime.now(UTC)
            extra: dict[str, Any] = {"last_bid_id": str(last_bid.id) if last_bid else None, "reason": stored_reason}
            if release:
                extra["release"] = release
            payload = audit_module.build_event_payload(
                deployment_id=settings.deployment_id,
                operation_id=operation_id,
                auction_id=auction_id,
                sequence=event_sequence,
                event_type="AUCTION_CANCELLED",
                prev_event_hash=prev_hash,
                prev_auction_version=prev_version,
                auction_version=auction.version,
                actor_id=seller_id,
                actor_alias=alias,
                occurred_at=occurred_at,
                extra=extra,
            )
            event_hash = audit_module.sign_event(payload, prev_hash)
            audit_module.persist_event(
                session,
                auction_id=auction_id,
                sequence=event_sequence,
                event_type="AUCTION_CANCELLED",
                operation_id=operation_id,
                payload=payload,
                prev_hash=prev_hash,
                event_hash=event_hash,
            )

            session.refresh(auction)
            snap = audit_module.json_safe_payload(auctions_module.get_auction(session, auction_id))
            session.add(
                Key(
                    actor_id=seller_id,
                    idempotency_key=idempotency_key,
                    fingerprint=fingerprint,
                    operation_id=operation_id,
                    status_code=200,
                    response_json=snap,
                )
            )
            session.commit()
            await asyncio.to_thread(journal.append_commit, operation_id)
            session.refresh(auction)
            return auction
        except AppError:
            session.rollback()
            await asyncio.to_thread(journal.append_abort, operation_id)
            raise
        except Exception:
            session.rollback()
            await asyncio.to_thread(journal.append_abort, operation_id)
            raise
