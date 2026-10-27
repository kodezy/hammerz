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
