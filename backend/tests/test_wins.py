from tests.conftest import auth_headers
from tests.test_bids import _bid, _deposit, _make_live_auction


def test_bids_and_wins_active_tab(client, db_session, seller_token, bidder_token, bidder2_token, respx_mock):
    aid1 = _make_live_auction(client, db_session, seller_token, respx_mock, object_id=436535)
    aid2 = _make_live_auction(client, db_session, seller_token, respx_mock, object_id=436532)
    _deposit(client, bidder_token, 100_000)
    _deposit(client, bidder2_token, 100_000)
    _bid(client, bidder_token, aid1, 10_000)
    _bid(client, bidder2_token, aid2, 10_000)

    r = client.get("/api/v1/me/bids-and-wins?tab=ACTIVE", headers=auth_headers(bidder_token))
    assert r.status_code == 200
    body = r.json()
    assert body["counts"]["active"] == 1
    assert body["total"] == 1
    assert body["items"][0]["id"] == aid1
    assert body["items"][0]["position"] == "LEADING"

    r2 = client.get("/api/v1/me/bids-and-wins?tab=ACTIVE", headers=auth_headers(bidder2_token))
    assert r2.json()["counts"]["active"] == 1
    assert r2.json()["items"][0]["id"] == aid2
