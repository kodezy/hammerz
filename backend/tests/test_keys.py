import uuid
from unittest.mock import patch

from sqlalchemy import func, select

from src.core.errors import AppError, ErrorCode
from src.db.tables import Bid
from tests.conftest import auth_headers
from tests.test_bids import _bid, _deposit, _make_live_auction


def test_bid_key_reused_different_body(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    key = str(uuid.uuid4())
    headers = {**auth_headers(bidder_token), "Idempotency-Key": key}
    client.post(f"/api/v1/auctions/{aid}/bids", headers=headers, json={"amount_cents": 10_000})
    r = client.post(f"/api/v1/auctions/{aid}/bids", headers=headers, json={"amount_cents": 10_500})
    assert r.status_code == 409
    assert r.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_same_key_two_auctions(client, db_session, seller_token, bidder_token, respx_mock):
    aid1 = _make_live_auction(client, db_session, seller_token, respx_mock, object_id=436535)
    aid2 = _make_live_auction(client, db_session, seller_token, respx_mock, object_id=436532)
    _deposit(client, bidder_token, 100_000)
    key = str(uuid.uuid4())
    first = _bid(client, bidder_token, aid1, 10_000, key)
    assert first.status_code == 200
    second = _bid(client, bidder_token, aid2, 10_000, key)
    assert second.status_code == 409
    assert second.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_journal_failure_before_prepare_no_bid_row(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)

    def fail_prepare(*_args, **_kwargs):
        raise AppError(503, ErrorCode.AUDIT_UNAVAILABLE, "Audit journal unavailable")

    journal = client.app.state.journal
    with patch.object(journal, "append_prepare", side_effect=fail_prepare):
        r = _bid(client, bidder_token, aid, 10_000)
    assert r.status_code == 503
    assert r.json()["code"] == "AUDIT_UNAVAILABLE"
    assert db_session.scalar(select(func.count()).select_from(Bid)) == 0
