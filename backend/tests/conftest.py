import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _test_database_url() -> str | None:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://hammerz:hammerz@localhost:5432/hammerz",
    )


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
    alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "migrations"))
    command.upgrade(alembic_cfg, "head")
    return eng


@pytest.fixture
def db_session(engine: Engine):
    from sqlalchemy.orm import Session, sessionmaker

    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
