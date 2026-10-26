import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.canon import EVENT_DOMAIN, event_mac, secret_key_id
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
