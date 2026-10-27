import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.errors import AppError, ErrorCode
from src.core.limits import limiter
from src.core.money import available
from src.db.tables import Auction, Item, Key, Ledger, Wallet


def _money(cents: int) -> dict:
    return {"cents": cents, "currency": "USD"}


def wallet_view(session: Session, wallet: Wallet) -> dict:
    commitments: list[dict] = []
    rows = session.scalars(
        select(Auction).where(
            Auction.current_leader_id == wallet.user_id,
            Auction.status == "OPEN",
        )
    ).all()
    for auction in rows:
        item = session.get(Item, auction.item_id)
        if item is None or auction.current_bid_cents is None:
            continue
        commitments.append(
            {
                "auction_id": str(auction.id),
                "display_no": auction.display_no,
                "reserved": _money(auction.current_bid_cents),
                "title": item.title,
            }
        )
    return {
        "available": _money(available(wallet.total_cents, wallet.committed_cents)),
        "commitments": commitments,
        "committed": _money(wallet.committed_cents),
        "currency": "USD",
        "total": _money(wallet.total_cents),
    }


def get_wallet_for_user(session: Session, user_id: uuid.UUID) -> dict:
    wallet = session.scalar(select(Wallet).where(Wallet.user_id == user_id))
    if wallet is None:
        raise AppError(404, ErrorCode.NOT_FOUND, "Wallet not found")
    return wallet_view(session, wallet)


def deposit(
    session: Session,
    user_id: uuid.UUID,
    amount_cents: int,
    idempotency_key: uuid.UUID,
    fingerprint: str,
) -> dict:
    settings = get_settings()
    if not limiter.allow(f"deposit:{user_id}", 10):
        raise AppError(429, ErrorCode.RATE_LIMITED, "Too many deposits")
    if amount_cents <= 0:
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "amount_cents must be positive")
    if amount_cents > settings.max_deposit_cents:
        raise AppError(422, ErrorCode.WALLET_LIMIT, "Deposit exceeds single deposit limit")

    existing = session.scalar(
        select(Key).where(
            Key.actor_id == user_id,
            Key.idempotency_key == idempotency_key,
        )
    )
    if existing:
        if existing.fingerprint != fingerprint:
            raise AppError(409, ErrorCode.IDEMPOTENCY_KEY_REUSED, "Idempotency key reused")
        if existing.response_json:
            return existing.response_json
        raise AppError(202, ErrorCode.OPERATION_PENDING, "Deposit still pending")

    operation_id = uuid.uuid4()
    session.execute(text("SET LOCAL lock_timeout = '5s'"))
    wallet = session.scalar(
        select(Wallet).where(Wallet.user_id == user_id).with_for_update()
    )
    if wallet is None:
        raise AppError(404, ErrorCode.NOT_FOUND, "Wallet not found")
    new_total = wallet.total_cents + amount_cents
    if new_total > settings.max_bidder_total_cents:
        raise AppError(422, ErrorCode.WALLET_LIMIT, "Wallet total limit exceeded")

    wallet.total_cents = new_total
    session.add(
        Ledger(
            wallet_id=wallet.id,
            operation_id=operation_id,
            type="DEPOSIT_SIMULATED",
            total_delta_cents=amount_cents,
            committed_delta_cents=0,
        )
    )
    body = wallet_view(session, wallet)
    session.add(
        Key(
            actor_id=user_id,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
            operation_id=operation_id,
            status_code=200,
            response_json=body,
        )
    )
    session.commit()
    session.refresh(wallet)
    return wallet_view(session, wallet)
