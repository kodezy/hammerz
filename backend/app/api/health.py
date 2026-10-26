import os

from fastapi import APIRouter, Response

from app.core.config import get_settings
from app.core.errors import ErrorCode
from app.db.session import check_database

router = APIRouter(tags=["health"])


def _audit_ready() -> bool:
    audit_dir = get_settings().audit_dir
    try:
        os.makedirs(audit_dir, exist_ok=True)
        probe = os.path.join(audit_dir, ".ready_probe")
        with open(probe, "w", encoding="utf-8") as handle:
            handle.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(response: Response) -> dict[str, str]:
    if not check_database():
        response.status_code = 503
        return {"status": "not_ready", "code": ErrorCode.DATABASE_UNAVAILABLE}
    if not _audit_ready():
        response.status_code = 503
        return {"status": "not_ready", "code": ErrorCode.AUDIT_UNAVAILABLE}
    return {"status": "ok"}
