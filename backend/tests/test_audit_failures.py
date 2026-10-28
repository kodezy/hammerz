import uuid

from sqlalchemy import select, text

from src.db.tables import Bid, User
from tests.test_bids import _bid, _deposit, _make_live_auction


def test_audit_tampered_extra_bid_row(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    _bid(client, bidder_token, aid, 10_000)
    bidder2 = db_session.scalar(select(User).where(User.email == "bidder2@hammerz.test"))
    assert bidder2 is not None
    db_session.add(
        Bid(
            id=uuid.uuid4(),
            auction_id=uuid.UUID(aid),
            bidder_id=bidder2.id,
            amount_cents=10_500,
            accepted_at=db_session.scalar(text("SELECT clock_timestamp()")),
            sequence=99,
            operation_id=uuid.uuid4(),
        )
    )
    db_session.commit()

    r = client.get(f"/api/v1/auctions/{aid}/audit")
    assert r.json()["verification"]["status"] == "TAMPERED"
    assert "BID_COUNT_MISMATCH" in r.json()["verification"]["reason_codes"]


def test_audit_tampered_deleted_bid_row(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    _bid(client, bidder_token, aid, 10_000)
    db_session.execute(text("DELETE FROM bids WHERE auction_id = :aid"), {"aid": uuid.UUID(aid)})
    db_session.commit()

    body = client.get(f"/api/v1/auctions/{aid}/audit").json()
    assert body["verification"]["status"] == "TAMPERED"
    codes = body["verification"]["reason_codes"]
    assert "BID_COUNT_MISMATCH" in codes or "BID_ROW_MISSING" in codes
