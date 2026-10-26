from datetime import UTC, datetime, timedelta

import httpx
import pytest

from tests.conftest import auth_headers


def _mock_met(respx_mock):
    respx_mock.get(
        "https://collectionapi.metmuseum.org/public/collection/v1/objects/436535"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "objectID": 436535,
                "title": "Settle Lot",
                "primaryImage": "https://example.com/img.jpg",
            },
        )
    )


@pytest.mark.asyncio
async def test_close_without_bids(db_session, tmp_path, monkeypatch, respx_mock, seller_token):
    monkeypatch.setenv("AUDIT_DIR", str(tmp_path / "audit"))
    from app.core.config import get_settings
    from app.modules import auctions as auctions_module
    from app.modules import settle as settle_module
    from app.modules.journal import Journal

    get_settings.cache_clear()
    settings = get_settings()
    journal = Journal(settings.audit_dir, settings.hmac_secret.encode(), settings.deployment_id)
    journal.open(db_has_auctions=False)
    _mock_met(respx_mock)
    import asyncio

    from app.modules.auth import provision

    seller = asyncio.run(
        provision(db_session, "settle-seller@test.com", "password123!", "SELLER")
    )
    starts = datetime.now(UTC) - timedelta(hours=1)
    ends = datetime.now(UTC) - timedelta(seconds=1)
    auction = asyncio.run(
        auctions_module.create_auction(
            db_session,
            journal,
            seller.id,
            436535,
            10_000,
            500,
            starts,
            ends,
        )
    )
    await settle_module.close_one(db_session, journal, auction.id)
    db_session.refresh(auction)
    assert auction.status == "CLOSED"


def test_finalizing_display(client, seller_token, respx_mock):
    _mock_met(respx_mock)
    starts = datetime.now(UTC) - timedelta(seconds=1)
    ends = datetime.now(UTC) - timedelta(seconds=1)
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
    r = client.get(f"/api/v1/auctions/{lot['id']}")
    assert r.json()["display_status"] == "FINALIZING"
