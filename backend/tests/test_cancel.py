import uuid

from tests.conftest import auth_headers
from tests.test_bids import _bid, _deposit, _make_live_auction


def test_cancel_without_bids(client, db_session, seller_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    key = str(uuid.uuid4())
    r = client.post(
        f"/api/v1/auctions/{aid}/cancel", headers={**auth_headers(seller_token), "Idempotency-Key": key}, json={}
    )
    assert r.status_code == 200
    got = client.get(f"/api/v1/auctions/{aid}")
    assert got.status_code == 200
    assert got.json()["status"] == "CANCELLED"


def test_cancel_with_bids_requires_reason(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    _bid(client, bidder_token, aid, 10_000)
    r = client.post(
        f"/api/v1/auctions/{aid}/cancel",
        headers={**auth_headers(seller_token), "Idempotency-Key": str(uuid.uuid4())},
        json={},
    )
    assert r.status_code == 422


def test_cancel_short_reason_422(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    _bid(client, bidder_token, aid, 10_000)
    r = client.post(
        f"/api/v1/auctions/{aid}/cancel",
        headers={**auth_headers(seller_token), "Idempotency-Key": str(uuid.uuid4())},
        json={"reason": "too short"},
    )
    assert r.status_code == 422


def test_cancel_wrong_seller_403(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    r = client.post(
        f"/api/v1/auctions/{aid}/cancel",
        headers={**auth_headers(bidder_token), "Idempotency-Key": str(uuid.uuid4())},
        json={"reason": "This lot should not be cancelled by a bidder."},
    )
    assert r.status_code == 403


def test_cancel_idempotent(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    _bid(client, bidder_token, aid, 10_000)
    key = str(uuid.uuid4())
    headers = {**auth_headers(seller_token), "Idempotency-Key": key}
    reason = "Scheduling conflict — this lot is withdrawn from the sale."
    r1 = client.post(f"/api/v1/auctions/{aid}/cancel", headers=headers, json={"reason": reason})
    r2 = client.post(f"/api/v1/auctions/{aid}/cancel", headers=headers, json={"reason": reason})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json() == r2.json()
