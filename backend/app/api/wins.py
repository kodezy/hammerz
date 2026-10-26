import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_bidder
from app.db.session import get_db
from app.db.tables import Auction, Bid, Deal, Item, Slip, User
from app.modules import auctions as auctions_module
from app.modules.bids import participant_position

router = APIRouter(prefix="/api/v1/me", tags=["me"])

Tab = Literal["ACTIVE", "WON", "PAST"]


def _user_auction_ids(session: Session, user_id: uuid.UUID) -> set[uuid.UUID]:
    rows = session.scalars(select(Bid.auction_id).where(Bid.bidder_id == user_id).distinct())
    return set(rows)


def _tab_match(session: Session, auction: Auction, user_id: uuid.UUID, tab: Tab, now) -> bool:
    pos = participant_position(session, user_id, auction.id)["position"]
    if tab == "ACTIVE":
        if auction.status == "CANCELLED":
            return False
        if auction.status == "CLOSED":
            return False
        if auction.status == "OPEN" and now >= auction.ends_at:
            return True
        return pos in ("LEADING", "OUTBID")
    if tab == "WON":
        if auction.status != "CLOSED" or auction.current_leader_id != user_id:
            return False
        deal = session.scalar(select(Deal).where(Deal.auction_id == auction.id))
        if deal is None:
            return False
        slip = session.scalar(select(Slip).where(Slip.settlement_id == deal.id))
        return slip is not None
    if tab == "PAST":
        if pos == "NOT_PARTICIPATING":
            return False
        if tab == "PAST" and pos == "CANCELLED":
            return True
        if auction.status == "CANCELLED":
            return True
        if auction.status == "CLOSED" and auction.current_leader_id != user_id:
            return True
        return False
    return False


def bids_and_wins(
    session: Session,
    user_id: uuid.UUID,
    tab: Tab,
    offset: int,
    limit: int,
) -> dict:
    now = session.scalar(select(func.clock_timestamp()))
    auction_ids = _user_auction_ids(session, user_id)
    snapshots: list[dict] = []
    counts = {"active": 0, "past": 0, "won": 0}

    for aid in auction_ids:
        auction = session.get(Auction, aid)
        if auction is None:
            continue
        item = session.get(Item, auction.item_id)
        seller = session.get(User, auction.seller_id)
        if item is None or seller is None:
            continue
        snap = auctions_module.auction_snapshot(session, auction, item, seller, now)
        snap["position"] = participant_position(session, user_id, aid)["position"]
        if _tab_match(session, auction, user_id, "ACTIVE", now):
            counts["active"] += 1
        if _tab_match(session, auction, user_id, "WON", now):
            counts["won"] += 1
        if _tab_match(session, auction, user_id, "PAST", now):
            counts["past"] += 1
        if _tab_match(session, auction, user_id, tab, now):
            snapshots.append(snap)

    snapshots.sort(key=lambda s: s["display_no"], reverse=True)
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


@router.get("/auctions/{auction_id}/status")
def auction_status(
    auction_id: uuid.UUID,
    user: User = Depends(require_bidder),
    session: Session = Depends(get_db),
) -> dict:
    return participant_position(session, user.id, auction_id)


@router.get("/auctions/{auction_id}/status")
def auction_participant_status(
    auction_id: uuid.UUID,
    user: User = Depends(require_bidder),
    session: Session = Depends(get_db),
) -> dict:
    return participant_position(session, user.id, auction_id)


@router.get("/bids-and-wins")
def list_bids_and_wins(
    tab: Tab = Query("ACTIVE"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(require_bidder),
    session: Session = Depends(get_db),
) -> dict:
    return bids_and_wins(session, user.id, tab, offset, limit)
