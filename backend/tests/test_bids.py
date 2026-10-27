import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func, select

from src.db.tables import Auction, Bid, Ledger
from tests.conftest import auth_headers


def _mock_met(respx_mock, object_id: int = 436535):
    respx_mock.get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}").mock(
        return_value=httpx.Response(
            200,
            json={
                "objectID": object_id,
                "title": "Test Lot",
                "primaryImage": "https://example.com/img.jpg",
                "isPublicDomain": True,
                "artistDisplayName": "Artist",
            },
        )
    )


def _deposit(client, token: str, cents: int) -> None:
    client.post(
        "/api/v1/wallet/deposits",
        headers={**auth_headers(token), "Idempotency-Key": str(uuid.uuid4())},
        json={"amount_cents": cents},
    )


def _make_live_auction(
    client,
    db_session,
    seller_token,
    respx_mock,
    *,
    object_id: int = 436535,
    opening: int = 10_000,
    increment: int = 500,
    ends_in_seconds: int = 180,
) -> str:
    _mock_met(respx_mock, object_id)
    starts = datetime.now(UTC) + timedelta(hours=1)
    ends = starts + timedelta(hours=2)
    created = client.post(
        "/api/v1/auctions",
        headers=auth_headers(seller_token),
        json={
            "external_id": str(object_id),
            "opening_bid_cents": opening,
            "minimum_increment_cents": increment,
            "starts_at": starts.isoformat().replace("+00:00", "Z"),
            "ends_at": ends.isoformat().replace("+00:00", "Z"),
        },
    )
    assert created.status_code == 201
    auction_id = created.json()["id"]
    auction = db_session.get(Auction, uuid.UUID(auction_id))
    now = db_session.scalar(select(func.clock_timestamp()))
    auction.starts_at = now - timedelta(seconds=1)
    auction.ends_at = now + timedelta(seconds=ends_in_seconds)
    db_session.flush()
    return auction_id


def _bid(client, token: str, auction_id: str, amount: int, key: str | None = None):
    headers = {**auth_headers(token), "Idempotency-Key": key or str(uuid.uuid4())}
    return client.post(f"/api/v1/auctions/{auction_id}/bids", headers=headers, json={"amount_cents": amount})


def test_first_bid_at_opening(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    r = _bid(client, bidder_token, aid, 10_000)
    assert r.status_code == 200
    body = r.json()
    assert body["amount_cents"] == 10_000
    assert body["sequence"] == 1
    assert db_session.scalar(select(func.count()).select_from(Bid)) == 1


def test_bid_below_opening_rejected(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    r = _bid(client, bidder_token, aid, 9_999)
    assert r.status_code == 409
    assert r.json()["code"] == "BID_TOO_LOW"
    assert db_session.scalar(select(func.count()).select_from(Bid)) == 0


def test_bid_respects_increment(client, db_session, seller_token, bidder_token, bidder2_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    _deposit(client, bidder2_token, 50_000)
    _bid(client, bidder_token, aid, 10_000)
    r = _bid(client, bidder2_token, aid, 10_400)
    assert r.status_code == 409
    assert r.json()["code"] == "BID_TOO_LOW"
    ok = _bid(client, bidder_token, aid, 10_500)
    assert ok.status_code == 409
    assert ok.json()["code"] == "ALREADY_LEADING"


def test_leader_cannot_raise(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    _bid(client, bidder_token, aid, 10_000)
    r = _bid(client, bidder_token, aid, 10_500)
    assert r.status_code == 409
    assert r.json()["code"] == "ALREADY_LEADING"


def test_insufficient_funds_no_ledger(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 5_000)
    before = db_session.scalar(select(func.count()).select_from(Ledger)) or 0
    r = _bid(client, bidder_token, aid, 10_000)
    assert r.status_code == 409
    assert r.json()["code"] == "INSUFFICIENT_FUNDS"
    after = db_session.scalar(select(func.count()).select_from(Ledger)) or 0
    assert after == before


def test_outbid_releases_previous_reserve(client, db_session, seller_token, bidder_token, bidder2_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    _deposit(client, bidder2_token, 50_000)
    _bid(client, bidder_token, aid, 10_000)
    w1 = client.get("/api/v1/wallet", headers=auth_headers(bidder_token)).json()
    assert w1["committed"]["cents"] == 10_000
    _bid(client, bidder2_token, aid, 10_500)
    w1 = client.get("/api/v1/wallet", headers=auth_headers(bidder_token)).json()
    assert w1["committed"]["cents"] == 0
    w2 = client.get("/api/v1/wallet", headers=auth_headers(bidder2_token)).json()
    assert w2["committed"]["cents"] == 10_500


def test_concurrent_bids_one_leader(client, db_session, seller_token, bidder_token, bidder2_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 100_000)
    _deposit(client, bidder2_token, 100_000)
    r1 = _bid(client, bidder_token, aid, 10_000)
    r2 = _bid(client, bidder2_token, aid, 10_500)
    assert r1.status_code == 200
    assert r2.status_code == 200
    auction = db_session.get(Auction, uuid.UUID(aid))
    assert auction.current_bid_cents == 10_500
    assert auction.current_leader_id is not None
    assert db_session.scalar(select(func.count()).select_from(Bid).where(Bid.auction_id == auction.id)) == 2


def test_anti_snipe_extends_end(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock, ends_in_seconds=90)
    auction = db_session.get(Auction, uuid.UUID(aid))
    old_end = auction.ends_at
    _deposit(client, bidder_token, 50_000)
    r = _bid(client, bidder_token, aid, 10_000)
    assert r.status_code == 200
    db_session.refresh(auction)
    assert auction.ends_at == old_end + timedelta(minutes=2)
    assert r.json()["ends_at"] == auction.ends_at.isoformat().replace("+00:00", "Z")


def test_refuse_bid_at_ends_at(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock, ends_in_seconds=3600)
    auction = db_session.get(Auction, uuid.UUID(aid))
    now = db_session.scalar(select(func.clock_timestamp()))
    auction.ends_at = now
    db_session.flush()
    _deposit(client, bidder_token, 50_000)
    r = _bid(client, bidder_token, aid, 10_000)
    assert r.status_code == 409
    assert r.json()["code"] == "AUCTION_NOT_LIVE"


def test_bid_idempotent_replay(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    key = str(uuid.uuid4())
    first = _bid(client, bidder_token, aid, 10_000, key)
    second = _bid(client, bidder_token, aid, 10_000, key)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert db_session.scalar(select(func.count()).select_from(Bid)) == 1


def test_available_considers_other_lot_reserves(client, db_session, seller_token, bidder_token, respx_mock):
    aid1 = _make_live_auction(client, db_session, seller_token, respx_mock, object_id=436535)
    aid2 = _make_live_auction(client, db_session, seller_token, respx_mock, object_id=436532)
    _deposit(client, bidder_token, 15_000)
    _bid(client, bidder_token, aid1, 10_000)
    r = _bid(client, bidder_token, aid2, 10_000)
    assert r.status_code == 409
    assert r.json()["code"] == "INSUFFICIENT_FUNDS"
    _deposit(client, bidder_token, 5_000)
    ok = _bid(client, bidder_token, aid2, 10_000)
    assert ok.status_code == 200


def test_seller_cannot_bid(client, db_session, seller_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    r = _bid(client, seller_token, aid, 10_000)
    assert r.status_code == 403


def test_list_bids_public_aliases(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    _bid(client, bidder_token, aid, 10_000)
    r = client.get(f"/api/v1/auctions/{aid}/bids")
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert "bidder_alias" in item
    assert "bidder_id" not in item


def test_participant_status_leading(client, db_session, seller_token, bidder_token, respx_mock):
    aid = _make_live_auction(client, db_session, seller_token, respx_mock)
    _deposit(client, bidder_token, 50_000)
    _bid(client, bidder_token, aid, 10_000)
    r = client.get(f"/api/v1/me/auctions/{aid}/status", headers=auth_headers(bidder_token))
    assert r.status_code == 200
    assert r.json()["position"] == "LEADING"
