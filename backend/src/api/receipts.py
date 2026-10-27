import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.core.errors import AppError, ErrorCode
from src.db.session import get_db
from src.modules import audit as audit_module
from src.modules.journal import Journal

router = APIRouter(prefix="/api/v1/receipts", tags=["receipts"])


def get_journal(request: Request) -> Journal:
    return request.app.state.journal


@router.get("/{receipt_id}")
async def get_receipt(
    receipt_id: uuid.UUID,
    session: Session = Depends(get_db),
    journal: Journal = Depends(get_journal),
) -> dict:
    from src.db.tables import Deal, Slip

    slip = session.get(Slip, receipt_id)
    if slip is None:
        raise AppError(404, ErrorCode.NOT_FOUND, "Receipt not found")
    deal = session.get(Deal, slip.settlement_id)
    if deal is None:
        raise AppError(404, ErrorCode.NOT_FOUND, "Receipt not found")
    integrity = audit_module.verify_auction(session, journal, deal.auction_id)
    return {
        **slip.snapshot_json,
        "close_event_hash": slip.close_event_hash,
        "created_at": slip.created_at,
        "id": str(slip.id),
        "integrity": integrity,
        "receipt_id": str(slip.id),
    }
