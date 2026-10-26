"""Evaluation seed — idempotent provisioning via domain services."""

import argparse
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.canon import request_fingerprint
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.db.tables import Auction, Ledger, User, Wallet
from app.modules import auctions as auctions_module
from app.modules import bids as bids_module
from app.modules import cancel as cancel_module
from app.modules import settle as settle_module
from app.modules.auth import provision
from app.modules.journal import Journal

SEED_SELLER = "seller@hammerz.test"
SEED_BIDDER1 = "bidder1@hammerz.test"
SEED_BIDDER2 = "bidder2@hammerz.test"
SEED_PASSWORDS = {
    SEED_SELLER: "Seller-Eval-2026!",
    SEED_BIDDER1: "Bidder1-Eval-2026!",
    SEED_BIDDER2: "Bidder2-Eval-2026!",
}
OPENING = {
    SEED_BIDDER1: 1_240_000,
    SEED_BIDDER2: 1_000_000,
    SEED_SELLER: 0,
}
MET_OBJECTS = (436535, 436532)
SEED_KEY_NS = uuid.UUID("00000000-0000-4000-8000-000000000001")


def _journal() -> Journal:
    settings = get_settings()
    journal = Journal(
        settings.audit_dir,
        settings.hmac_secret.encode(),
        settings.deployment_id,
    )
    with get_session_factory()() as session:
        from sqlalchemy import func

        from app.db.tables import Auction as A

        has = session.scalar(select(func.count()).select_from(A)) or 0
    journal.open(db_has_auctions=has > 0)
    return journal


def _ensure_user(session, email: str, role: str) -> User:
    user = session.scalar(select(User).where(User.email == email))
    if user:
        return user
    return asyncio.run(provision(session, email, SEED_PASSWORDS[email], role))


def _ensure_opening(session, user: User, cents: int) -> None:
    wallet = session.scalar(select(Wallet).where(Wallet.user_id == user.id))
    if wallet is None:
        return
    existing = session.scalar(
        select(Ledger).where(
            Ledger.wallet_id == wallet.id,
            Ledger.type == "OPENING_BALANCE",
        )
    )
    if existing:
        return
    if cents <= 0:
        return
    op = uuid.uuid5(SEED_KEY_NS, f"opening:{user.email}")
    wallet.total_cents += cents
    session.add(
        Ledger(
            wallet_id=wallet.id,
            operation_id=op,
            type="OPENING_BALANCE",
            total_delta_cents=cents,
            committed_delta_cents=0,
        )
    )


async def seed-demo(*, ensure_live: bool = False) -> None:
    journal = _journal()
    with get_session_factory()() as session:
        seller = _ensure_user(session, SEED_SELLER, "SELLER")
        bidder1 = _ensure_user(session, SEED_BIDDER1, "BIDDER")
        bidder2 = _ensure_user(session, SEED_BIDDER2, "BIDDER")
        _ensure_opening(session, seller, OPENING[SEED_SELLER])
        _ensure_opening(session, bidder1, OPENING[SEED_BIDDER1])
        _ensure_opening(session, bidder2, OPENING[SEED_BIDDER2])
        session.commit()

    now = datetime.now(UTC)
    windows = [
        (1, 436535, now - timedelta(minutes=5), now + timedelta(minutes=30), "live"),
        (2, 436532, now - timedelta(minutes=2), now + timedelta(minutes=45), "live"),
        (3, 436535, now - timedelta(hours=2), now - timedelta(minutes=10), "settled"),
        (4, 436532, now + timedelta(hours=2), now + timedelta(hours=4), "future"),
        (5, 436535, now - timedelta(minutes=30), now + timedelta(hours=1), "cancel"),
    ]

    with get_session_factory()() as session:
        from sqlalchemy import func

        if (session.scalar(select(func.count()).select_from(Auction)) or 0) >= 5:
            pass
        else:
            for _display_no, met_id, starts, ends, kind in windows:
                auction = await auctions_module.create_auction(
                    session,
                    journal,
                    seller.id,
                    met_id,
                    10_000,
                    500,
                    starts,
                    ends,
                )
                if kind == "settled" and auction.status == "OPEN":
                    for i, (bidder, amount) in enumerate(
                        [(bidder1, 10_000), (bidder2, 10_500), (bidder1, 11_000)]
                    ):
                        fp = request_fingerprint(
                            "POST",
                            f"/api/v1/auctions/{auction.id}/bids",
                            {"amount_cents": amount},
                        )
                        await bids_module.place_bid(
                            session,
                            journal,
                            bidder.id,
                            auction.id,
                            amount,
                            uuid.uuid5(SEED_KEY_NS, f"lot3-bid:{i}"),
                            fp,
                        )
                    await settle_module.close_one(session, journal, auction.id)
                if kind == "cancel" and auction.status == "OPEN":
                    ckey = uuid.uuid5(SEED_KEY_NS, "lot5-cancel")
                    fp = request_fingerprint(
                        "POST",
                        f"/api/v1/auctions/{auction.id}/cancel",
                        {"reason": "The artwork is no longer available for this auction."},
                    )
                    await cancel_module.cancel_auction(
                        session,
                        journal,
                        seller.id,
                        auction.id,
                        "The artwork is no longer available for this auction.",
                        ckey,
                        fp,
                    )

    if ensure_live:
        with get_session_factory()() as session:
            from app.modules.auctions import _db_now, derive_display_status

            now_db = _db_now(session)
            live = session.scalars(select(Auction).where(Auction.status == "OPEN")).all()
            if not any(derive_display_status(a, now_db) == "LIVE" for a in live):
                await auctions_module.create_auction(
                    session,
                    journal,
                    seller.id,
                    436535,
                    10_000,
                    500,
                    now_db - timedelta(seconds=1),
                    now_db + timedelta(minutes=60),
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ensure-live", action="store_true")
    args = parser.parse_args()
    asyncio.run(seed-demo(ensure_live=args.ensure_live))


if __name__ == "__main__":
    main()
