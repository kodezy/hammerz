import uuid
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.db.session import get_db
from app.db.tables import User
from app.modules.auth import current_user

bearer = HTTPBearer(auto_error=False)


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def db_session(session: Session = Depends(get_db)) -> Session:
    return session


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(401, ErrorCode.UNAUTHORIZED, "Authentication required")
    return current_user(session, credentials.credentials)


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Session = Depends(get_db),
) -> User | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        return current_user(session, credentials.credentials)
    except AppError:
        return None


async def require_seller(user: User = Depends(get_current_user)) -> User:
    if user.role != "SELLER":
        raise AppError(403, ErrorCode.FORBIDDEN, "Seller access required")
    return user


async def require_bidder(user: User = Depends(get_current_user)) -> User:
    if user.role != "BIDDER":
        raise AppError(403, ErrorCode.FORBIDDEN, "Bidder access required")
    return user


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def parse_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> uuid.UUID:
    if not idempotency_key:
        raise AppError(422, ErrorCode.IDEMPOTENCY_KEY_REQUIRED, "Idempotency-Key header required")
    try:
        return uuid.UUID(idempotency_key)
    except ValueError as exc:
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "Invalid Idempotency-Key") from exc
