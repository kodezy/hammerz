import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://hammerz:hammerz@127.0.0.1:5432/hammerz",
)
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("HMAC_SECRET", "test-hmac-secret")
os.environ.setdefault("ALIAS_SECRET", "test-alias-secret")
os.environ.setdefault("DEPLOYMENT_ID", "hammerz-test")

import asyncio
from collections.abc import Generator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.limits import limiter
from app.core.security import issue_token
from app.db.session import get_db
from app.main import create_app
from app.modules.auth import provision


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def live_client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("AUDIT_DIR", str(tmp_path / "audit"))
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


@pytest.fixture
def client(db_session: Session, tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("AUDIT_DIR", str(tmp_path / "audit"))
    get_settings.cache_clear()
    application = create_app()
    application.dependency_overrides[get_db] = lambda: db_session
    with TestClient(application) as test_client:
        yield test_client
    application.dependency_overrides.clear()
    get_settings.cache_clear()


def _test_database_url() -> str | None:
    return os.environ.get("DATABASE_URL")


@pytest.fixture(scope="session")
def engine() -> Engine:
    url = _test_database_url()
    if not url:
        pytest.skip("DATABASE_URL not set")
    eng = create_engine(url, pool_pre_ping=True)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not available: {exc}")
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location", os.path.join(os.path.dirname(__file__), "..", "migrations")
    )
    command.upgrade(alembic_cfg, "head")
    return eng


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def seller_token(db_session: Session) -> str:
    user = asyncio.run(provision(db_session, "seller@hammerz.test", "Seller-Eval-2026!", "SELLER"))
    return issue_token(user.id, user.role)


@pytest.fixture
def bidder_token(db_session: Session) -> str:
    user = asyncio.run(provision(db_session, "bidder@hammerz.test", "Bidder1-Eval-2026!", "BIDDER"))
    return issue_token(user.id, user.role)


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
