"""Demo data seed — idempotent provisioning via domain services."""

import argparse
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from src.core.canon import request_fingerprint
from src.core.config import get_settings
from src.db.session import get_session_factory
from src.db.tables import Auction, Ledger, User, Wallet
from src.modules import auctions as auctions_module
from src.modules import bids as bids_module
from src.modules import cancel as cancel_module
from src.modules import settle as settle_module
from src.modules.auth import provision
from src.modules.journal import Journal

SEED_SELLER = "seller@hammerz.test"
SEED_BIDDER1 = "bidder1@hammerz.test"
SEED_BIDDER2 = "bidder2@hammerz.test"
DEMO_PASSWORDS = {
    SEED_SELLER: "Seller-Demo-2026!",
    SEED_BIDDER1: "Bidder1-Demo-2026!",
    SEED_BIDDER2: "Bidder2-Demo-2026!",
}
OPENING = {
    SEED_BIDDER1: 1_240_000,
    SEED_BIDDER2: 1_000_000,
    SEED_SELLER: 0,
}
SEED_KEY_NS = uuid.UUID("00000000-0000-4000-8000-000000000001")


def _journal() -> Journal:
    settings = get_settings()
    journal = Journal(
        settings.audit_dir,
        settings.hmac_secret.encode(),
        settings.deployment_id,
    )
    with get_session_factory()() as session:
        has = session.scalar(select(func.count()).select_from(Auction)) or 0
    journal.open(db_has_auctions=has > 0)
    return journal


async def _ensure_user(session, email: str, role: str) -> User:
    user = session.scalar(select(User).where(User.email == email))
    if user:
        return user
    return await provision(session, email, DEMO_PASSWORDS[email], role)


async def _create_auction_window(
    session,
    journal: Journal,
    seller_id: uuid.UUID,
    object_id: int,
    opening_bid_cents: int,
    minimum_increment_cents: int,
    starts_at: datetime,
    ends_at: datetime,
    *,
    apply_window: bool = True,
) -> Auction:
    now_db = auctions_module._db_now(session)
    create_starts = starts_at if starts_at >= now_db else now_db + timedelta(seconds=1)
    create_ends = ends_at if ends_at > create_starts else create_starts + timedelta(hours=1)
    auction = await auctions_module.create_auction(
        session,
        journal,
        seller_id,
        object_id,
        opening_bid_cents,
        minimum_increment_cents,
        create_starts,
        create_ends,
        catalog_fallback=True,
    )
    if apply_window:
        _apply_auction_window(session, auction, starts_at, ends_at)
    return auction


def _apply_auction_window(session, auction: Auction, starts_at: datetime, ends_at: datetime) -> None:
    if auction.starts_at == starts_at and auction.ends_at == ends_at:
        return
    auction.starts_at = starts_at
    auction.ends_at = ends_at
    session.commit()
    session.refresh(auction)


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


async def run_seed(*, ensure_live: bool = False) -> None:
    journal = _journal()
    with get_session_factory()() as session:
        seller = await _ensure_user(session, SEED_SELLER, "SELLER")
        bidder1 = await _ensure_user(session, SEED_BIDDER1, "BIDDER")
        bidder2 = await _ensure_user(session, SEED_BIDDER2, "BIDDER")
        _ensure_opening(session, seller, OPENING[SEED_SELLER])
        _ensure_opening(session, bidder1, OPENING[SEED_BIDDER1])
        _ensure_opening(session, bidder2, OPENING[SEED_BIDDER2])
        session.commit()
        seller_id = seller.id
        bidder1_id = bidder1.id
        bidder2_id = bidder2.id

    async def _seed_bids(
        session,
        auction_id: uuid.UUID,
        label: str,
        pairs: list[tuple[User, int]],
    ) -> None:
        for i, (bidder, amount) in enumerate(pairs):
            fp = request_fingerprint(
                "POST",
                f"/api/v1/auctions/{auction_id}/bids",
                {"amount_cents": amount},
            )
            await bids_module.place_bid(
                session,
                journal,
                bidder.id,
                auction_id,
                amount,
                uuid.uuid5(SEED_KEY_NS, f"{label}-bid:{i}"),
                fp,
            )

    now = datetime.now(UTC)
    windows = [
        (1, 436535, 95_000, 5_000, now - timedelta(minutes=5), now + timedelta(minutes=30), "live"),
        (2, 436532, 145_000, 5_000, now - timedelta(minutes=2), now + timedelta(minutes=45), "live"),
        (3, 436535, 230_000, 5_000, now - timedelta(hours=2), now - timedelta(minutes=10), "settled"),
        (4, 436532, 100_000, 5_000, now + timedelta(hours=2), now + timedelta(hours=4), "future"),
        (5, 436535, 100_000, 5_000, now - timedelta(minutes=30), now + timedelta(hours=1), "cancel"),
    ]

    with get_session_factory()() as session:
        seller = session.get(User, seller_id)
        bidder1 = session.get(User, bidder1_id)
        bidder2 = session.get(User, bidder2_id)
        if seller is None or bidder1 is None or bidder2 is None:
            raise RuntimeError("seed users missing after provisioning")

        if (session.scalar(select(func.count()).select_from(Auction)) or 0) >= 5:
            pass
        else:
            for display_no, met_id, opening, increment, starts, ends, kind in windows:
                defer_window = kind == "settled"
                auction = await _create_auction_window(
                    session,
                    journal,
                    seller_id,
                    met_id,
                    opening,
                    increment,
                    starts,
                    ends,
                    apply_window=not defer_window,
                )
                if kind == "live" and auction.status == "OPEN":
                    if display_no == 1:
                        lot1: list[tuple[User, int]] = []
                        amount = 95_000
                        for i in range(12):
                            bidder = bidder1 if i % 2 == 0 else bidder2
                            lot1.append((bidder, amount))
                            amount += 5_000
                        await _seed_bids(session, auction.id, "lot1", lot1)
                    elif display_no == 2:
                        await _seed_bids(
                            session,
                            auction.id,
                            "lot2",
                            [(bidder2, 145_000), (bidder1, 150_000)],
                        )
                if kind == "settled" and auction.status == "OPEN":
                    await _seed_bids(
                        session,
                        auction.id,
                        "lot3",
                        [
                            (bidder1, 230_000),
                            (bidder2, 235_000),
                            (bidder1, 240_000),
                        ],
                    )
                    await settle_module.close_one(session, journal, auction.id)
                    _apply_auction_window(session, auction, starts, ends)
                if kind == "cancel" and auction.status == "OPEN":
                    await _seed_bids(
                        session,
                        auction.id,
                        "lot5",
                        [
                            (bidder2, 100_000),
                            (bidder1, 105_000),
                            (bidder2, 110_000),
                        ],
                    )
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
            now_db = auctions_module._db_now(session)
            live = session.scalars(select(Auction).where(Auction.status == "OPEN")).all()
            if not any(auctions_module.derive_display_status(a, now_db) == "LIVE" for a in live):
                await _create_auction_window(
                    session,
                    journal,
                    seller_id,
                    436535,
                    100_000,
                    5_000,
                    now_db - timedelta(seconds=1),
                    now_db + timedelta(minutes=60),
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ensure-live", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_seed(ensure_live=args.ensure_live))


if __name__ == "__main__":
    main()
