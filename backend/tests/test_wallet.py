import uuid

from tests.conftest import auth_headers


def test_get_wallet_bidder(client, bidder_token):
    r = client.get("/api/v1/wallet", headers=auth_headers(bidder_token))
    assert r.status_code == 200
    assert r.json()["currency"] == "USD"
    assert r.json()["total_cents"] == 0


def test_seller_forbidden(client, seller_token):
    r = client.get("/api/v1/wallet", headers=auth_headers(seller_token))
    assert r.status_code == 403


def test_deposit_increases_balance(client, bidder_token):
    key = str(uuid.uuid4())
    r = client.post(
        "/api/v1/wallet/deposits",
        headers={**auth_headers(bidder_token), "Idempotency-Key": key},
        json={"amount_cents": 5000},
    )
    assert r.status_code == 200
    assert r.json()["total_cents"] == 5000
    assert r.json()["available_cents"] == 5000


def test_deposit_idempotent_retry(client, bidder_token):
    key = str(uuid.uuid4())
    headers = {**auth_headers(bidder_token), "Idempotency-Key": key}
    first = client.post("/api/v1/wallet/deposits", headers=headers, json={"amount_cents": 1000})
    second = client.post("/api/v1/wallet/deposits", headers=headers, json={"amount_cents": 1000})
    assert first.json() == second.json()
    assert second.json()["total_cents"] == 1000


def test_deposit_key_reused_different_body(client, bidder_token):
    key = str(uuid.uuid4())
    headers = {**auth_headers(bidder_token), "Idempotency-Key": key}
    client.post("/api/v1/wallet/deposits", headers=headers, json={"amount_cents": 1000})
    r = client.post("/api/v1/wallet/deposits", headers=headers, json={"amount_cents": 2000})
    assert r.status_code == 409
    assert r.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_deposit_missing_key_422(client, bidder_token):
    r = client.post(
        "/api/v1/wallet/deposits",
        headers=auth_headers(bidder_token),
        json={"amount_cents": 1000},
    )
    assert r.status_code == 422


def test_deposit_cap(client, bidder_token):
    key = str(uuid.uuid4())
    r = client.post(
        "/api/v1/wallet/deposits",
        headers={**auth_headers(bidder_token), "Idempotency-Key": key},
        json={"amount_cents": 10_000_001},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "WALLET_LIMIT"
