from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.deps import require_seller
from src.db.session import get_db
from src.db.tables import Auction, Item, Ledger, User, Wallet
from src.modules import auctions as auctions_module

router = APIRouter(prefix="/api/v1/seller", tags=["seller"])

SellerFilter = Literal["ALL", "SCHEDULED", "LIVE", "ENDED", "CANCELLED"]


@router.get("/auctions")
def list_seller_auctions(
    status: SellerFilter = Query("ALL"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    seller: User = Depends(require_seller),
    session: Session = Depends(get_db),
) -> dict:
    now = session.scalar(select(func.clock_timestamp()))
    rows = session.scalars(
        select(Auction).where(Auction.seller_id == seller.id).order_by(Auction.display_no.desc())
    ).all()
    wallet = session.scalar(select(Wallet).where(Wallet.user_id == seller.id))
    total_received = 0
    if wallet:
        total_received = (
            session.scalar(
                select(func.coalesce(func.sum(Ledger.total_delta_cents), 0)).where(
                    Ledger.wallet_id == wallet.id, Ledger.type == "SETTLEMENT_CREDIT"
                )
            )
            or 0
        )

    snapshots: list[dict] = []
    counts = {"all": 0, "cancelled": 0, "ended": 0, "live": 0, "scheduled": 0}
    for auction in rows:
        item = session.get(Item, auction.item_id)
        user = session.get(User, auction.seller_id)
        if item is None or user is None:
            continue
        snap = auctions_module.auction_snapshot(session, auction, item, user, now)
        ds = snap["display_status"]
        counts["all"] += 1
        if ds == "SCHEDULED":
            counts["scheduled"] += 1
        elif ds == "LIVE":
            counts["live"] += 1
        elif ds in ("FINALIZING", "CLOSED"):
            counts["ended"] += 1
        elif ds == "CANCELLED":
            counts["cancelled"] += 1
        if (
            status == "ALL"
            or (status == "CANCELLED" and ds == "CANCELLED")
            or (status == "SCHEDULED" and ds == "SCHEDULED")
            or (status == "LIVE" and ds == "LIVE")
            or (status == "ENDED" and ds in ("FINALIZING", "CLOSED"))
        ):
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
        "total_received_cents": int(total_received),
    }
