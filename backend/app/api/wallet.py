from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import parse_idempotency_key, require_bidder
from app.core.canon import request_fingerprint
from app.core.money import MoneyCents
from app.db.session import get_db
from app.db.tables import User
from app.modules import wallet as wallet_module

router = APIRouter(prefix="/api/v1/wallet", tags=["wallet"])


class DepositBody(BaseModel):
    amount_cents: MoneyCents = Field(gt=0)


@router.get("")
def get_wallet(
    user: User = Depends(require_bidder),
    session: Session = Depends(get_db),
) -> dict:
    return wallet_module.get_wallet_for_user(session, user.id)


@router.post("/deposits")
def create_deposit(
    body: DepositBody,
    request: Request,
    idempotency_key=Depends(parse_idempotency_key),
    user: User = Depends(require_bidder),
    session: Session = Depends(get_db),
) -> dict:
    fingerprint = request_fingerprint(
        request.method,
        request.url.path,
        {"amount_cents": body.amount_cents},
    )
    return wallet_module.deposit(
        session,
        user.id,
        int(body.amount_cents),
        idempotency_key,
        fingerprint,
    )
