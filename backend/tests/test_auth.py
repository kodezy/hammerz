import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.core.config import get_settings
from app.core.errors import ErrorCode
from app.db.tables import Wallet
from app.main import app


def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def _register(client, email: str | None = None, password: str = "password1", **extra):
    payload = {"email": email or _unique_email(), "password": password, **extra}
    return client.post("/api/v1/auth/register", json=payload)


@pytest.mark.usefixtures("engine")
def test_register_creates_bidder_wallet_zero(client, db_session):
    suffix = uuid.uuid4().hex[:8]
    reg_email = f"A+{suffix}@B.COM"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": reg_email, "password": "password1"},
    )
    assert r.status_code == 201
    assert r.json()["email"] == reg_email.strip().lower()
    assert r.json()["role"] == "BIDDER"

    token = client.post(
        "/api/v1/auth/login",
        json={"email": reg_email.strip().lower(), "password": "password1"},
    ).json()["token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200

    user_id = UUID(me.json()["id"])
    total = db_session.scalar(select(Wallet.total_cents).where(Wallet.user_id == user_id))
    assert total == 0


@pytest.mark.usefixtures("engine")
def test_register_email_normalization(client):
    suffix = uuid.uuid4().hex[:6]
    raw = f"  User.{suffix}@Example.COM  "
    r = client.post("/api/v1/auth/register", json={"email": raw, "password": "password1"})
    assert r.status_code == 201
    assert r.json()["email"] == raw.strip().lower()


@pytest.mark.usefixtures("engine")
def test_register_duplicate_email_conflict(client):
    email = _unique_email("dup")
    assert _register(client, email=email).status_code == 201
    r2 = _register(client, email=email)
    assert r2.status_code == 409
    assert r2.json()["code"] == ErrorCode.EMAIL_TAKEN
    assert r2.json().get("request_id")


@pytest.mark.usefixtures("engine")
def test_concurrent_register_same_email_one_conflict():
    email = _unique_email("concurrent")

    def attempt() -> int:
        with TestClient(app) as c:
            return c.post(
                "/api/v1/auth/register",
                json={"email": email, "password": "password1"},
            ).status_code

    statuses: list[int] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt) for _ in range(2)]
        for fut in as_completed(futures):
            statuses.append(fut.result())

    assert sorted(statuses) == [201, 409]


@pytest.mark.usefixtures("engine")
def test_register_ignores_role_and_balance(client):
    email = _unique_email("role")
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password1", "role": "SELLER", "balance": 999},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "BIDDER"


def test_register_short_password_422(live_client):
    r = live_client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email("short"), "password": "short"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == ErrorCode.VALIDATION_ERROR


@pytest.mark.usefixtures("engine")
def test_login_and_me(client):
    email = _unique_email("login")
    _register(client, email=email)
    bad = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
    assert bad.status_code == 401
    assert bad.json()["code"] == ErrorCode.INVALID_CREDENTIALS

    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password1"}
    ).json()["token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["role"] == "BIDDER"


@pytest.mark.usefixtures("engine")
def test_me_rejects_jwt_alg_none(client):
    email = _unique_email("none")
    reg = _register(client, email=email)
    user_id = reg.json()["id"]
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": user_id, "role": "BIDDER", "iat": now, "exp": now + timedelta(minutes=30)},
        "",
        algorithm="none",
    )
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 401
    assert me.json()["code"] == ErrorCode.UNAUTHORIZED


@pytest.mark.usefixtures("engine")
def test_me_uses_db_role_not_jwt_claim(client):
    email = _unique_email("forge")
    reg = _register(client, email=email)
    user_id = reg.json()["id"]
    now = datetime.now(UTC)
    forged = jwt.encode(
        {
            "sub": user_id,
            "role": "SELLER",
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert me.status_code == 200
    assert me.json()["role"] == "BIDDER"


@pytest.mark.usefixtures("engine")
def test_register_rate_limit_sixth_request_429(client):
    for i in range(5):
        r = _register(client, email=_unique_email(f"rl{i}"))
        assert r.status_code == 201
    r6 = _register(client, email=_unique_email("rl-blocked"))
    assert r6.status_code == 429
    assert r6.json()["code"] == ErrorCode.RATE_LIMITED
