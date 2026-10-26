import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_seller
from app.core.money import MoneyCents
from app.db.session import get_db
from app.db.tables import User
from app.modules import auctions as auctions_module
from app.modules.journal import Journal

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
        from app.core.errors import AppError, ErrorCode

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
    status: Literal["LIVE", "SCHEDULED", "ENDED"] | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_db),
) -> dict:
    return auctions_module.list_auctions(session, status, offset, limit)


@router.get("/{auction_id}")
def get_auction_route(
    auction_id: uuid.UUID,
    session: Session = Depends(get_db),
) -> dict:
    return auctions_module.get_auction(session, auction_id)
