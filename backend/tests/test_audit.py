
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
                "title": "Audit Lot",
                "primaryImage": "https://example.com/img.jpg",
            },
        )
    )


def test_audit_verified_after_create(client, seller_token, respx_mock):
    from datetime import UTC, datetime, timedelta

    _mock_met(respx_mock)
    starts = datetime.now(UTC) + timedelta(hours=1)
    ends = starts + timedelta(hours=2)
    lot = client.post(
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
    r = client.get(f"/api/v1/auctions/{lot['id']}/audit")
    assert r.status_code == 200
    assert r.json()["verification"]["status"] == "VERIFIED"
    assert "actor_id" not in str(r.json()["items"])
