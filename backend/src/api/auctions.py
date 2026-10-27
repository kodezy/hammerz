import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import get_optional_user, parse_idempotency_key, require_bidder, require_seller
from src.core.canon import request_fingerprint
from src.core.money import MoneyCents
from src.db.session import get_db
from src.db.tables import User
from src.modules import auctions as auctions_module
from src.modules import audit as audit_module
from src.modules import bids as bids_module
from src.modules import cancel as cancel_module
from src.modules.journal import Journal

router = APIRouter(prefix="/api/v1/auctions", tags=["auctions"])


class CreateAuctionBody(BaseModel):
    external_id: str
    opening_bid_cents: MoneyCents = Field(gt=0)
    minimum_increment_cents: MoneyCents = Field(gt=0)
    starts_at: datetime
    ends_at: datetime


def get_journal(request: Request) -> Journal:
    return request.app.state.journal


@router.post("", status_code=201)
async def create_auction_route(
    body: CreateAuctionBody,
    session: Session = Depends(get_db),
    seller: User = Depends(require_seller),
    journal: Journal = Depends(get_journal),
) -> dict:
    try:
        object_id = int(body.external_id)
    except ValueError as exc:
        from src.core.errors import AppError, ErrorCode

        raise AppError(422, ErrorCode.VALIDATION_ERROR, "Invalid external_id") from exc
    auction = await auctions_module.create_auction(
        session,
        journal,
        seller.id,
        object_id,
        int(body.opening_bid_cents),
        int(body.minimum_increment_cents),
        body.starts_at,
        body.ends_at,
    )
    return auctions_module.get_auction(session, auction.id)


@router.get("")
def list_auctions_route(
    status: Literal["LIVE", "SCHEDULED", "ENDED"] = Query("LIVE"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_db),
) -> dict:
    return auctions_module.list_auctions(session, status, offset, limit)


@router.get("/{auction_id}")
def get_auction_route(
    auction_id: uuid.UUID,
    session: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
) -> dict:
    from src.db.tables import Auction

    snap = auctions_module.get_auction(session, auction_id)
    if viewer is not None and viewer.role == "SELLER":
        auction = session.get(Auction, auction_id)
        if auction is not None and auction.seller_id == viewer.id:
            snap["viewer_is_owner"] = True
    return snap


class PlaceBidBody(BaseModel):
    amount_cents: MoneyCents = Field(gt=0)


class CancelBody(BaseModel):
    reason: str | None = None


@router.post("/{auction_id}/bids")
async def place_bid_route(
    auction_id: uuid.UUID,
    body: PlaceBidBody,
    request: Request,
    idempotency_key: uuid.UUID = Depends(parse_idempotency_key),
    bidder: User = Depends(require_bidder),
    session: Session = Depends(get_db),
    journal: Journal = Depends(get_journal),
) -> dict:
    path = f"/api/v1/auctions/{auction_id}/bids"
    fingerprint = request_fingerprint(
        request.method,
        path,
        {"amount_cents": body.amount_cents},
    )
    result = await bids_module.place_bid(
        session,
        journal,
        bidder.id,
        auction_id,
        int(body.amount_cents),
        idempotency_key,
        fingerprint,
    )
    hub = request.app.state.hub
    snap = auctions_module.get_auction(session, auction_id)
    await hub.publish(
        str(auction_id),
        {
            "auction_id": str(auction_id),
            "bid": result.response,
            "server_time": snap["server_time"],
            "snapshot": snap,
            "type": "bid.accepted",
            "version": snap["version"],
        },
    )
    return result.response


@router.post("/{auction_id}/cancel")
async def cancel_auction_route(
    auction_id: uuid.UUID,
    body: CancelBody,
    request: Request,
    idempotency_key: uuid.UUID = Depends(parse_idempotency_key),
    seller: User = Depends(require_seller),
    session: Session = Depends(get_db),
    journal: Journal = Depends(get_journal),
) -> dict:
    path = f"/api/v1/auctions/{auction_id}/cancel"
    fingerprint = request_fingerprint(request.method, path, body.model_dump())
    auction = await cancel_module.cancel_auction(
        session,
        journal,
        seller.id,
        auction_id,
        body.reason,
        idempotency_key,
        fingerprint,
    )
    hub = request.app.state.hub
    snap = auctions_module.get_auction(session, auction_id)
    await hub.publish(
        str(auction_id),
        {
            "auction_id": str(auction_id),
            "server_time": snap["server_time"],
            "snapshot": snap,
            "type": "auction.cancelled",
            "version": snap["version"],
        },
    )
    return auctions_module.get_auction(session, auction.id)


@router.get("/{auction_id}/bids")
def list_bids_route(
    auction_id: uuid.UUID,
    before_sequence: int | None = Query(None, ge=1),
    after_sequence: int | None = Query(None, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_db),
    journal: Journal = Depends(get_journal),
) -> dict:
    return bids_module.list_bids(
        session,
        journal,
        auction_id,
        before_sequence=before_sequence,
        after_sequence=after_sequence,
        limit=limit,
    )


@router.get("/{auction_id}/audit")
def audit_route(
    auction_id: uuid.UUID,
    before_sequence: int | None = Query(None, ge=1),
    after_sequence: int | None = Query(None, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_db),
    journal: Journal = Depends(get_journal),
) -> dict:
    summary = audit_module.verify_auction(session, journal, auction_id)
    events = audit_module.list_audit_events(
        session,
        auction_id,
        before_sequence=before_sequence,
        after_sequence=after_sequence,
        limit=limit,
    )
    from sqlalchemy import func, select

    from src.db.tables import Bid

    bid_count = session.scalar(
        select(func.count()).select_from(Bid).where(Bid.auction_id == auction_id)
    ) or 0
    return {**events, "bid_count": int(bid_count), "verification": summary}
