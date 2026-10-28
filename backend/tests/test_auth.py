import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.core.config import get_settings
from src.core.errors import ErrorCode
from src.db.tables import Wallet
from src.main import create_app


def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def _register(client, email: str | None = None, password: str = "password1", **extra):
    payload = {"email": email or _unique_email(), "password": password, **extra}
    return client.post("/api/v1/auth/register", json=payload)


@pytest.mark.usefixtures("engine")
def test_register_creates_bidder_wallet_zero(client, db_session):
    suffix = uuid.uuid4().hex[:8]
    reg_email = f"A+{suffix}@B.COM"
    r = client.post("/api/v1/auth/register", json={"email": reg_email, "password": "password1"})
    assert r.status_code == 201
    assert r.json()["email"] == reg_email.strip().lower()
    assert r.json()["role"] == "BIDDER"

    token = client.post(
        "/api/v1/auth/login", json={"email": reg_email.strip().lower(), "password": "password1"}
    ).json()["token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200

    user_id = UUID(me.json()["id"])
    total = db_session.scalar(select(Wallet.total_cents).where(Wallet.user_id == user_id))
    assert total == 0


def test_login_body_accepts_reserved_test_tld():
    from src.api.auth import LoginBody

    body = LoginBody(email="bidder1@hammerz.test", password="password1")
    assert body.email == "bidder1@hammerz.test"


@pytest.mark.usefixtures("engine")
def test_login_accepts_reserved_test_tld(client):
    email = f"demo-{uuid.uuid4().hex[:8]}@hammerz.test"
    assert _register(client, email=email).status_code == 201
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "password1"})
    assert r.status_code == 200
    assert r.json()["token"]


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
def test_concurrent_register_same_email_one_conflict(tmp_path):
    email = _unique_email("concurrent")
    audit_dir = str(tmp_path / "audit")

    def attempt() -> int:
        os.environ["AUDIT_DIR"] = audit_dir
        get_settings.cache_clear()
        with TestClient(create_app()) as c:
            return c.post("/api/v1/auth/register", json={"email": email, "password": "password1"}).status_code

    statuses: list[int] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt) for _ in range(2)]
        for fut in as_completed(futures):
            statuses.append(fut.result())

    assert sorted(statuses) == [201, 409]
    get_settings.cache_clear()


@pytest.mark.usefixtures("engine")
def test_register_ignores_role_and_balance(client):
    email = _unique_email("role")
    r = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password1", "role": "SELLER", "balance": 999}
    )
    assert r.status_code == 201
    assert r.json()["role"] == "BIDDER"


def test_register_short_password_422(live_client):
    r = live_client.post("/api/v1/auth/register", json={"email": _unique_email("short"), "password": "short"})
    assert r.status_code == 422
    assert r.json()["code"] == ErrorCode.VALIDATION_ERROR


@pytest.mark.usefixtures("engine")
def test_login_and_me(client):
    email = _unique_email("login")
    _register(client, email=email)
    bad = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
    assert bad.status_code == 401
    assert bad.json()["code"] == ErrorCode.INVALID_CREDENTIALS

    token = client.post("/api/v1/auth/login", json={"email": email, "password": "password1"}).json()["token"]
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
        {"sub": user_id, "role": "BIDDER", "iat": now, "exp": now + timedelta(minutes=30)}, "", algorithm="none"
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
        {"sub": user_id, "role": "SELLER", "iat": now, "exp": now + timedelta(minutes=30)},
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


@pytest.mark.usefixtures("engine")
def test_login_sets_refresh_cookie(client):
    email = _unique_email("cookie")
    _register(client, email=email)
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "password1"})
    assert r.status_code == 200
    assert r.json()["token"]
    cookie = r.headers.get("set-cookie", "")
    assert "hammerz_refresh=" in cookie
    assert "HttpOnly" in cookie
    assert "Path=/api/v1/auth" in cookie


@pytest.mark.usefixtures("engine")
def test_refresh_twice_same_cookie(client):
    email = _unique_email("refresh2")
    _register(client, email=email)
    client.post("/api/v1/auth/login", json={"email": email, "password": "password1"})
    r1 = client.post("/api/v1/auth/refresh")
    r2 = client.post("/api/v1/auth/refresh")
    assert r1.status_code == 200
    assert r2.status_code == 200
    for r in (r1, r2):
        token = r.json()["token"]
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200


@pytest.mark.usefixtures("engine")
def test_refresh_without_cookie_401(client):
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 401
    assert r.json()["code"] == ErrorCode.UNAUTHORIZED


@pytest.mark.usefixtures("engine")
def test_logout_revokes_refresh(client):
    email = _unique_email("logout")
    _register(client, email=email)
    client.post("/api/v1/auth/login", json={"email": email, "password": "password1"})
    out = client.post("/api/v1/auth/logout")
    assert out.status_code == 204
    assert "hammerz_refresh=" in out.headers.get("set-cookie", "")
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 401


@pytest.mark.usefixtures("engine")
def test_refresh_expired_clears_cookie(client, db_session):
    from src.db.tables import RefreshToken

    email = _unique_email("expired")
    _register(client, email=email)
    client.post("/api/v1/auth/login", json={"email": email, "password": "password1"})
    row = db_session.scalar(select(RefreshToken))
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 401
    assert "hammerz_refresh=" in r.headers.get("set-cookie", "")
