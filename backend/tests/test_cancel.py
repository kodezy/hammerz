import uuid
from datetime import UTC, datetime, timedelta

import httpx

from tests.conftest import auth_headers


def _mock_met(respx_mock):
    respx_mock.get(
        "https://collectionapi.metmuseum.org/public/collection/v1/objects/436535"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "objectID": 436535,
                "title": "Cancel Lot",
                "primaryImage": "https://example.com/img.jpg",
            },
        )
    )


def _live_lot(client, seller_token, respx_mock):
    _mock_met(respx_mock)
    starts = datetime.now(UTC) - timedelta(seconds=1)
    ends = datetime.now(UTC) + timedelta(seconds=180)
    return client.post(
        "/api/v1/auctions",
        headers=auth_headers(seller_token),
        json={
            "external_id": "436535",
            "opening_bid_cents": 10_000,
            "minimum_increment_cents": 500,
            "starts_at": starts.isoformat().replace("+00:00", "Z"),
            "ends_at": ends.isoformat().replace("+00:00", "Z"),
        },
    ).json()


def test_cancel_without_bids(client, seller_token, respx_mock):
    lot = _live_lot(client, seller_token, respx_mock)
    key = str(uuid.uuid4())
    r = client.post(
        f"/api/v1/auctions/{lot['id']}/cancel",
        headers={**auth_headers(seller_token), "Idempotency-Key": key},
        json={},
    )
    assert r.status_code == 200
    got = client.get(f"/api/v1/auctions/{lot['id']}")
    assert got.status_code == 200
    assert got.json()["status"] == "CANCELLED"


def test_cancel_with_bids_requires_reason(client, seller_token, bidder_token, respx_mock):
    lot = _live_lot(client, seller_token, respx_mock)
    client.post(
        "/api/v1/wallet/deposits",
        headers={**auth_headers(bidder_token), "Idempotency-Key": str(uuid.uuid4())},
        json={"amount_cents": 50_000},
    )
    client.post(
        f"/api/v1/auctions/{lot['id']}/bids",
        headers={**auth_headers(bidder_token), "Idempotency-Key": str(uuid.uuid4())},
        json={"amount_cents": 10_000},
    )
    r = client.post(
        f"/api/v1/auctions/{lot['id']}/cancel",
        headers={**auth_headers(seller_token), "Idempotency-Key": str(uuid.uuid4())},
        json={},
    )
    assert r.status_code == 422
