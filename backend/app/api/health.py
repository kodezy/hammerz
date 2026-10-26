from fastapi import APIRouter, Request, Response

from app.core.errors import ErrorCode
from app.db.session import check_database

router = APIRouter(tags=["health"])


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(request: Request, response: Response) -> dict[str, str]:
    if not check_database():
        response.status_code = 503
        return {"status": "not_ready", "code": ErrorCode.DATABASE_UNAVAILABLE}
    journal = getattr(request.app.state, "journal", None)
    if journal is None or journal.blocked:
        response.status_code = 503
        return {"status": "not_ready", "code": ErrorCode.AUDIT_UNAVAILABLE}
    return {"status": "ok"}
