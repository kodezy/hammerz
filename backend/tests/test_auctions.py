import uuid
from datetime import UTC, datetime, timedelta

import httpx

from tests.conftest import auth_headers


def _mock_met_object(respx_mock, object_id: int = 436535):
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


def test_create_auction_as_seller(client, seller_token, respx_mock, db_session):
    _mock_met_object(respx_mock)
    starts = datetime.now(UTC) + timedelta(hours=1)
    ends = starts + timedelta(hours=2)
    r = client.post(
        "/api/v1/auctions",
        headers=auth_headers(seller_token),
        json={
            "external_id": "436535",
            "opening_bid_cents": 10000,
            "minimum_increment_cents": 500,
            "starts_at": starts.isoformat().replace("+00:00", "Z"),
            "ends_at": ends.isoformat().replace("+00:00", "Z"),
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["item"]["title"] == "Test Lot"
    assert "seller_alias" in body
    assert body["opening_bid"]["cents"] == 10000


def test_bidder_cannot_create(client, bidder_token, respx_mock):
    _mock_met_object(respx_mock)
    starts = datetime.now(UTC) + timedelta(hours=1)
    ends = starts + timedelta(hours=2)
    r = client.post(
        "/api/v1/auctions",
        headers=auth_headers(bidder_token),
        json={
            "external_id": "436535",
            "opening_bid_cents": 10000,
            "minimum_increment_cents": 500,
            "starts_at": starts.isoformat().replace("+00:00", "Z"),
            "ends_at": ends.isoformat().replace("+00:00", "Z"),
        },
    )
    assert r.status_code == 403


def test_starts_at_past_422(client, seller_token, respx_mock):
    _mock_met_object(respx_mock)
    starts = datetime.now(UTC) - timedelta(hours=1)
    ends = datetime.now(UTC) + timedelta(hours=2)
    r = client.post(
        "/api/v1/auctions",
        headers=auth_headers(seller_token),
        json={
            "external_id": "436535",
            "opening_bid_cents": 10000,
            "minimum_increment_cents": 500,
            "starts_at": starts.isoformat().replace("+00:00", "Z"),
            "ends_at": ends.isoformat().replace("+00:00", "Z"),
        },
    )
    assert r.status_code == 422


def test_vitrine_lists_created(client, seller_token, respx_mock):
    _mock_met_object(respx_mock)
    starts = datetime.now(UTC) + timedelta(hours=1)
    ends = starts + timedelta(hours=2)
    client.post(
        "/api/v1/auctions",
        headers=auth_headers(seller_token),
        json={
            "external_id": "436535",
            "opening_bid_cents": 10000,
            "minimum_increment_cents": 500,
            "starts_at": starts.isoformat().replace("+00:00", "Z"),
            "ends_at": ends.isoformat().replace("+00:00", "Z"),
        },
    )
    r = client.get("/api/v1/auctions?status=SCHEDULED")
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    assert "counts" in r.json()


def test_get_by_id(client, seller_token, respx_mock):
    _mock_met_object(respx_mock)
    starts = datetime.now(UTC) + timedelta(hours=1)
    ends = starts + timedelta(hours=2)
    created = client.post(
        "/api/v1/auctions",
        headers=auth_headers(seller_token),
        json={
            "external_id": "436535",
            "opening_bid_cents": 10000,
            "minimum_increment_cents": 500,
            "starts_at": starts.isoformat().replace("+00:00", "Z"),
            "ends_at": ends.isoformat().replace("+00:00", "Z"),
        },
    ).json()
    r = client.get(f"/api/v1/auctions/{created['id']}")
    assert r.status_code == 200
    assert "server_time" in r.json()


def test_get_missing_404(client):
    r = client.get(f"/api/v1/auctions/{uuid.uuid4()}")
    assert r.status_code == 404
