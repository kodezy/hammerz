import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.db.tables import Auction, Bid, Deal, Item, Slip, User
from app.modules import audit as audit_module
from app.modules.alias import display_alias
from app.modules.catalog import fetch_object
from app.modules.journal import Journal

DisplayFilter = Literal["LIVE", "SCHEDULED", "ENDED"]


def _db_now(session: Session) -> datetime:
    return session.scalar(select(func.clock_timestamp()))


def derive_display_status(auction: Auction, now: datetime) -> str:
    if auction.status == "CANCELLED":
        return "CANCELLED"
    if auction.status == "CLOSED":
        return "CLOSED"
    if now < auction.starts_at:
        return "SCHEDULED"
    if now >= auction.ends_at:
        return "FINALIZING"
    return "LIVE"


def _money(cents: int | None) -> dict[str, Any] | None:
    if cents is None:
        return None
    return {"cents": cents, "currency": "USD"}


def auction_snapshot(
    session: Session,
    auction: Auction,
    item: Item,
    seller: User,
    now: datetime | None = None,
) -> dict[str, Any]:
    if now is None:
        now = _db_now(session)
    display_status = derive_display_status(auction, now)
    bid_count = session.scalar(
        select(func.count()).select_from(Bid).where(Bid.auction_id == auction.id)
    ) or 0
    leader_alias = None
    if auction.current_leader_id is not None:
        leader = session.get(User, auction.current_leader_id)
        if leader is not None:
            leader_alias = display_alias(auction.id, leader.id, leader.role)
    receipt_id = None
    if auction.status == "CLOSED":
        deal = session.scalar(select(Deal).where(Deal.auction_id == auction.id))
        if deal is not None:
            slip = session.scalar(select(Slip).where(Slip.settlement_id == deal.id))
            if slip is not None:
                receipt_id = str(slip.id)
    return {
        "bid_count": int(bid_count),
        "cancel_reason": auction.cancel_reason,
        "currency": "USD",
        "current_bid": _money(auction.current_bid_cents),
        "leader_alias": leader_alias,
        "display_no": auction.display_no,
        "display_status": display_status,
        "ends_at": auction.ends_at,
        "id": str(auction.id),
        "item": {
            "artist": item.artist,
            "attribution": item.attribution,
            "description": item.description,
            "external_id": item.external_id,
            "image_url": item.image_url,
            "is_public_domain": item.is_public_domain,
            "object_begin_date": (item.metadata_json or {}).get("object_begin_date"),
            "object_url": item.object_url,
            "provider": item.provider,
            "title": item.title,
        },
        "minimum_increment": _money(auction.minimum_increment_cents),
        "opening_bid": _money(auction.opening_bid_cents),
        "receipt_id": receipt_id,
        "seller_alias": display_alias(auction.id, seller.id, seller.role),
        "server_time": now,
        "starts_at": auction.starts_at,
        "status": auction.status,
        "version": auction.version,
    }


async def create_auction(
    session: Session,
    journal: Journal,
    seller_id: uuid.UUID,
    object_id: int,
    opening_bid_cents: int,
    minimum_increment_cents: int,
    starts_at: datetime,
    ends_at: datetime,
    *,
    catalog_fallback: bool = False,
) -> Auction:
    if journal.blocked:
        raise AppError(503, ErrorCode.AUDIT_UNAVAILABLE, "Audit journal unavailable")
    settings = get_settings()
    if opening_bid_cents <= 0 or minimum_increment_cents <= 0:
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "Bid amounts must be positive")
    if opening_bid_cents > settings.max_bid_cents or minimum_increment_cents > settings.max_bid_cents:
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "Amount exceeds maximum")
    if starts_at >= ends_at:
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "Invalid auction window")
    now = _db_now(session)
    if starts_at < now:
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "starts_at must not be in the past")

    catalog = await fetch_object(object_id, allow_demo_snapshot=catalog_fallback)
    operation_id = uuid.uuid4()
    auction_id = uuid.uuid4()

    item = session.scalar(
        select(Item).where(
            Item.provider == catalog["provider"],
            Item.external_id == catalog["external_id"],
        )
    )
    new_item = item is None
    if item is None:
        item = Item(
            provider=catalog["provider"],
            external_id=catalog["external_id"],
            title=catalog["title"],
            artist=catalog.get("artist"),
            description=catalog.get("description"),
            image_url=catalog.get("image_url"),
            object_url=catalog.get("object_url"),
            is_public_domain=catalog.get("is_public_domain"),
            attribution=catalog.get("attribution"),
            metadata_json=catalog,
        )

    display_no = session.scalar(select(func.coalesce(func.max(Auction.display_no), 0))) + 1
    seller = session.get(User, seller_id)
    if seller is None:
        raise AppError(403, ErrorCode.FORBIDDEN, "Seller not found")

    alias = display_alias(auction_id, seller_id, seller.role)
    occurred_at = datetime.now(UTC)
    rules = {
        "minimum_increment_cents": minimum_increment_cents,
        "opening_bid_cents": opening_bid_cents,
    }
    item_snapshot = {
        "artist": item.artist,
        "external_id": item.external_id,
        "image_url": item.image_url,
        "provider": item.provider,
        "title": item.title,
    }
    payload = audit_module.build_event_payload(
        deployment_id=settings.deployment_id,
        operation_id=operation_id,
        auction_id=auction_id,
        sequence=1,
        event_type="AUCTION_CREATED",
        prev_event_hash=audit_module.genesis_event_hash(),
        prev_auction_version=0,
        auction_version=1,
        actor_id=seller_id,
        actor_alias=alias,
        occurred_at=occurred_at,
        extra={"item_snapshot": item_snapshot, "rules": rules},
    )
    event_hash = audit_module.sign_event(payload, audit_module.genesis_event_hash())

    import asyncio

    async with journal._async_lock:
        await asyncio.to_thread(
            journal.append_prepare,
            {
                "operation_id": str(operation_id),
                "event": {"payload": payload, "type": "AUCTION_CREATED"},
            },
        )
        try:
            session.execute(text("SET LOCAL lock_timeout = '5s'"))
            if new_item:
                session.add(item)
            session.flush()
            auction = Auction(
                id=auction_id,
                display_no=display_no,
                seller_id=seller_id,
                item_id=item.id,
                status="OPEN",
                version=1,
                opening_bid_cents=opening_bid_cents,
                minimum_increment_cents=minimum_increment_cents,
                starts_at=starts_at,
                ends_at=ends_at,
            )
            session.add(auction)
            audit_module.persist_event(
                session,
                auction_id=auction_id,
                sequence=1,
                event_type="AUCTION_CREATED",
                operation_id=operation_id,
                payload=payload,
                prev_hash=audit_module.genesis_event_hash(),
                event_hash=event_hash,
            )
            session.commit()
            await asyncio.to_thread(journal.append_commit, operation_id)
            session.refresh(auction)
            return auction
        except Exception:
            session.rollback()
            await asyncio.to_thread(journal.append_abort, operation_id)
            raise


def list_auctions(
    session: Session,
    status_filter: DisplayFilter | None,
    offset: int,
    limit: int,
) -> dict[str, Any]:
    now = _db_now(session)
    stmt = select(Auction).where(Auction.status != "CANCELLED")

    rows = session.scalars(stmt.order_by(Auction.display_no.desc())).all()

    snapshots: list[dict[str, Any]] = []
    counts = {"ended": 0, "live": 0, "scheduled": 0}
    for auction in rows:
        item = session.get(Item, auction.item_id)
        seller = session.get(User, auction.seller_id)
        if item is None or seller is None:
            continue
        snap = auction_snapshot(session, auction, item, seller, now)
        ds = snap["display_status"]
        if ds == "SCHEDULED":
            counts["scheduled"] += 1
        elif ds == "LIVE":
            counts["live"] += 1
        elif ds in ("FINALIZING", "CLOSED"):
            counts["ended"] += 1
        if status_filter == "SCHEDULED" and ds != "SCHEDULED":
            continue
        if status_filter == "LIVE" and ds != "LIVE":
            continue
        if status_filter == "ENDED" and ds not in ("FINALIZING", "CLOSED"):
            continue
        snapshots.append(snap)

    total = len(snapshots)
    page = snapshots[offset : offset + limit]
    return {
        "counts": counts,
        "has_more": offset + limit < total,
        "items": page,
        "limit": limit,
        "offset": offset,
        "total": total,
    }


def get_auction(session: Session, auction_id: uuid.UUID) -> dict[str, Any]:
    auction = session.get(Auction, auction_id)
    if auction is None:
        raise AppError(404, ErrorCode.NOT_FOUND, "Auction not found")
    item = session.get(Item, auction.item_id)
    seller = session.get(User, auction.seller_id)
    if item is None or seller is None:
        raise AppError(404, ErrorCode.NOT_FOUND, "Auction not found")
    return auction_snapshot(session, auction, item, seller)
