import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.canon import event_mac, secret_key_id
from app.core.config import get_settings
from app.db.tables import Event
from app.modules.alias import display_alias


def build_event_payload(
    *,
    deployment_id: str,
    operation_id: uuid.UUID,
    auction_id: uuid.UUID,
    sequence: int,
    event_type: str,
    prev_event_hash: str,
    prev_auction_version: int,
    auction_version: int,
    actor_id: uuid.UUID,
    actor_alias: str,
    occurred_at: datetime,
    currency: str = "USD",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "actor_alias": actor_alias,
        "actor_id": str(actor_id),
        "auction_id": str(auction_id),
        "auction_version": auction_version,
        "currency": currency,
        "deployment_id": deployment_id,
        "occurred_at": occurred_at,
        "operation_id": str(operation_id),
        "prev_auction_version": prev_auction_version,
        "prev_event_hash": prev_event_hash,
        "schema_version": 1,
        "sequence": sequence,
        "type": event_type,
    }
    if extra:
        payload.update(extra)
    return payload


def sign_event(payload: dict[str, Any], prev_hash: str) -> str:
    settings = get_settings()
    key_id = secret_key_id(settings.hmac_secret.encode())
    return event_mac(
        settings.hmac_secret.encode(),
        settings.deployment_id,
        key_id,
        prev_hash,
        payload,
    )


def persist_event(
    session: Session,
    *,
    auction_id: uuid.UUID,
    sequence: int,
    event_type: str,
    operation_id: uuid.UUID,
    payload: dict[str, Any],
    prev_hash: str,
    event_hash: str,
    bid_id: uuid.UUID | None = None,
) -> Event:
    row = Event(
        auction_id=auction_id,
        sequence=sequence,
        type=event_type,
        operation_id=operation_id,
        bid_id=bid_id,
        payload=payload,
        prev_hash=prev_hash,
        event_hash=event_hash,
    )
    session.add(row)
    return row


def genesis_event_hash() -> str:
    return "0" * 64


def actor_alias_for(session: Session, auction_id: uuid.UUID, user_id: uuid.UUID, role: str) -> str:
    return display_alias(auction_id, user_id, role)


def _public_payload(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out.pop("actor_id", None)
    if "winner_id" in out:
        out.pop("winner_id", None)
    return out


def verify_auction(session: Session, journal, auction_id: uuid.UUID) -> dict[str, Any]:
    from sqlalchemy import select

    from app.core.errors import AppError, ErrorCode
    from app.db.tables import Auction, Bid, Event

    checked_at = datetime.now(UTC)
    if journal.blocked or journal.pending_prepare() is not None:
        return {
            "checked_at": checked_at,
            "head": None,
            "last_committed_seq": None,
            "reason_codes": ["JOURNAL_UNAVAILABLE"],
            "status": "UNVERIFIABLE",
        }

    auction = session.get(Auction, auction_id)
    events = session.scalars(
        select(Event).where(Event.auction_id == auction_id).order_by(Event.sequence.asc())
    ).all()

    if auction is None and not events:
        raise AppError(404, ErrorCode.NOT_FOUND, "Auction not found")
    if auction is None and events:
        return {
            "checked_at": checked_at,
            "head": events[-1].event_hash if events else None,
            "last_committed_seq": events[-1].sequence if events else None,
            "reason_codes": ["AUCTION_MISSING"],
            "status": "TAMPERED",
        }

    reason_codes: list[str] = []
    prev = genesis_event_hash()
    for ev in events:
        if ev.prev_hash != prev:
            reason_codes.append("EVENT_CHAIN_BREAK")
            break
        expected = sign_event(ev.payload, ev.prev_hash)
        if expected != ev.event_hash:
            reason_codes.append("EVENT_HASH_MISMATCH")
            break
        if not journal.has_commit(ev.operation_id):
            reason_codes.append("JOURNAL_COMMIT_MISSING")
        prev = ev.event_hash
        if ev.type == "BID_ACCEPTED":
            bid = session.get(Bid, ev.bid_id) if ev.bid_id else None
            if bid is None:
                reason_codes.append("BID_ROW_MISSING")
            elif bid.amount_cents != ev.payload.get("amount_cents"):
                reason_codes.append("BID_AMOUNT_MISMATCH")

    status = "VERIFIED" if not reason_codes else "TAMPERED"
    return {
        "checked_at": checked_at,
        "head": events[-1].event_hash if events else genesis_event_hash(),
        "last_committed_seq": events[-1].sequence if events else 0,
        "reason_codes": reason_codes,
        "status": status,
    }


def list_audit_events(
    session: Session,
    auction_id: uuid.UUID,
    *,
    before_sequence: int | None,
    after_sequence: int | None,
    limit: int,
) -> dict[str, Any]:
    from sqlalchemy import select

    from app.db.tables import Event

    stmt = select(Event).where(Event.auction_id == auction_id)
    if after_sequence is not None:
        stmt = stmt.where(Event.sequence > after_sequence).order_by(Event.sequence.asc())
    elif before_sequence is not None:
        stmt = stmt.where(Event.sequence < before_sequence).order_by(Event.sequence.desc())
    else:
        stmt = stmt.order_by(Event.sequence.desc())
    rows = session.scalars(stmt.limit(limit)).all()
    items = [
        {
            "event_hash": ev.event_hash,
            "payload": _public_payload(ev.payload),
            "sequence": ev.sequence,
            "type": ev.type,
        }
        for ev in rows
    ]
    return {"items": items, "limit": limit}
