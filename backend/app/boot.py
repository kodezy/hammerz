import os
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse

from sqlalchemy import create_engine, text

from app.core.config import get_settings


def _database_host_port(database_url: str) -> tuple[str, int]:
    parsed = urlparse(database_url.replace("+psycopg", ""))
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    return host, port


def wait_for_tcp(host: str, port: int, timeout_seconds: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            time.sleep(1)
    raise RuntimeError(f"database TCP not ready at {host}:{port}")


def wait_for_select_one(database_url: str, timeout_seconds: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    engine = create_engine(database_url, pool_pre_ping=True)
    while time.monotonic() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("database SELECT 1 not ready")


def run_alembic() -> None:
    alembic_ini = os.path.join(os.getcwd(), "alembic.ini")
    if not os.path.isfile(alembic_ini):
        return
    subprocess.run(["alembic", "-c", alembic_ini, "upgrade", "head"], check=True)


def main() -> None:
    settings = get_settings()
    host, port = _database_host_port(settings.database_url)
    wait_for_tcp(host, port)
    wait_for_select_one(settings.database_url)
    run_alembic()
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, workers=1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"boot failed: {exc}", file=sys.stderr)
        raise
