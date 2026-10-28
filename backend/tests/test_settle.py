import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func, select

from src.db.tables import Auction


def _mock_met(respx_mock):
    respx_mock.get("https://collectionapi.metmuseum.org/public/collection/v1/objects/436535").mock(
        return_value=httpx.Response(
            200, json={"objectID": 436535, "title": "Settle Lot", "primaryImage": "https://example.com/img.jpg"}
        )
    )


def test_close_without_bids(db_session, tmp_path, monkeypatch, respx_mock):
    monkeypatch.setenv("AUDIT_DIR", str(tmp_path / "audit"))
    from src.core.config import get_settings
    from src.modules import auctions as auctions_module
    from src.modules import settle as settle_module
    from src.modules.auth import provision
    from src.modules.journal import Journal

    get_settings.cache_clear()
    settings = get_settings()
    journal = Journal(settings.audit_dir, settings.hmac_secret.encode(), settings.deployment_id)
    journal.open(db_has_auctions=False)
    _mock_met(respx_mock)
    seller = asyncio.run(provision(db_session, "settle-seller@test.com", "password123!", "SELLER"))
    starts = datetime.now(UTC) + timedelta(hours=1)
    ends = starts + timedelta(hours=2)
    auction = asyncio.run(
        auctions_module.create_auction(db_session, journal, seller.id, 436535, 10_000, 500, starts, ends)
    )
    now = db_session.scalar(select(func.clock_timestamp()))
    auction.starts_at = now - timedelta(seconds=5)
    auction.ends_at = now - timedelta(seconds=1)
    db_session.flush()
    asyncio.run(settle_module.close_one(db_session, journal, auction.id))
    db_session.refresh(auction)
    assert auction.status == "CLOSED"


def test_finalizing_display(client, db_session, seller_token, respx_mock):
    from tests.test_bids import _make_live_auction

    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    auction = db_session.get(Auction, uuid.UUID(aid))
    now = db_session.scalar(select(func.clock_timestamp()))
    auction.ends_at = now - timedelta(seconds=1)
    db_session.flush()
    r = client.get(f"/api/v1/auctions/{aid}")
    assert r.json()["display_status"] == "FINALIZING"


def test_close_with_winner_transfers_once(db_session, tmp_path, monkeypatch, respx_mock):
    monkeypatch.setenv("AUDIT_DIR", str(tmp_path / "audit"))
    from src.core.canon import request_fingerprint
    from src.core.config import get_settings
    from src.db.tables import Deal, Ledger, Slip, Wallet
    from src.modules import auctions as auctions_module
    from src.modules import bids as bids_module
    from src.modules import settle as settle_module
    from src.modules.auth import provision
    from src.modules.journal import Journal

    get_settings.cache_clear()
    settings = get_settings()
    journal = Journal(settings.audit_dir, settings.hmac_secret.encode(), settings.deployment_id)
    journal.open(db_has_auctions=False)
    _mock_met(respx_mock)
    seller = asyncio.run(provision(db_session, "settle-seller2@test.com", "password123!", "SELLER"))
    bidder = asyncio.run(provision(db_session, "settle-bidder@test.com", "password123!", "BIDDER"))
    db_session.flush()
    bidder_wallet = db_session.scalar(select(Wallet).where(Wallet.user_id == bidder.id))
    seller_wallet = db_session.scalar(select(Wallet).where(Wallet.user_id == seller.id))
    assert bidder_wallet and seller_wallet
    bidder_wallet.total_cents = 50_000
    db_session.flush()

    starts = datetime.now(UTC) + timedelta(hours=1)
    ends = starts + timedelta(hours=2)
    auction = asyncio.run(
        auctions_module.create_auction(db_session, journal, seller.id, 436535, 10_000, 500, starts, ends)
    )
    now = db_session.scalar(select(func.clock_timestamp()))
    auction.starts_at = now - timedelta(seconds=5)
    auction.ends_at = now + timedelta(minutes=5)
    db_session.flush()
    fp = request_fingerprint("POST", f"/api/v1/auctions/{auction.id}/bids", {"amount_cents": 12_000})
    asyncio.run(bids_module.place_bid(db_session, journal, bidder.id, auction.id, 12_000, uuid.uuid4(), fp))
    auction.ends_at = now - timedelta(seconds=1)
    db_session.flush()
    asyncio.run(settle_module.close_one(db_session, journal, auction.id))
    db_session.refresh(auction)
    db_session.refresh(bidder_wallet)
    db_session.refresh(seller_wallet)
    assert auction.status == "CLOSED"
    assert db_session.scalar(select(func.count()).select_from(Deal).where(Deal.auction_id == auction.id)) == 1
    slip_count = db_session.scalar(
        select(func.count())
        .select_from(Slip)
        .join(Deal, Slip.settlement_id == Deal.id)
        .where(Deal.auction_id == auction.id)
    )
    assert slip_count == 1
    assert bidder_wallet.total_cents == 50_000 - 12_000
    assert bidder_wallet.committed_cents == 0
    assert seller_wallet.total_cents == 12_000
    debits = db_session.scalars(
        select(Ledger).where(Ledger.type == "SETTLEMENT_DEBIT", Ledger.auction_id == auction.id)
    ).all()
    credits = db_session.scalars(
        select(Ledger).where(Ledger.type == "SETTLEMENT_CREDIT", Ledger.auction_id == auction.id)
    ).all()
    assert len(debits) == 1
    assert len(credits) == 1
    asyncio.run(settle_module.close_one(db_session, journal, auction.id))
    assert db_session.scalar(select(func.count()).select_from(Deal).where(Deal.auction_id == auction.id)) == 1
