import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.errors import AppError, ErrorCode
from src.core.security import (
    REFRESH_TTL,
    hash_password,
    hash_refresh,
    issue_token,
    new_refresh_secret,
    normalize_email,
    verify_password,
)
from src.db.tables import RefreshToken, User, Wallet


def _validate_password(password: str) -> None:
    if len(password) < 8 or len(password) > 128:
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "Password must be 8–128 characters")


def _now() -> datetime:
    return datetime.now(UTC)


def issue_session(session: Session, user: User) -> tuple[str, str]:
    access = issue_token(user.id, user.role)
    refresh_raw = new_refresh_secret()
    session.add(RefreshToken(user_id=user.id, token_hash=hash_refresh(refresh_raw), expires_at=_now() + REFRESH_TTL))
    session.commit()
    return access, refresh_raw


async def register(session: Session, email: str, password: str) -> User:
    _validate_password(password)
    normalized = normalize_email(email)
    user = User(email=normalized, password_hash=await hash_password(password), role="BIDDER")
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise AppError(409, ErrorCode.EMAIL_TAKEN, "Email already registered") from exc
    session.add(Wallet(user_id=user.id))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise AppError(409, ErrorCode.EMAIL_TAKEN, "Email already registered") from exc
    session.refresh(user)
    return user


async def login(session: Session, email: str, password: str) -> tuple[str, str]:
    normalized = normalize_email(email)
    user = session.scalar(select(User).where(User.email == normalized))
    if user is None or not await verify_password(password, user.password_hash):
        raise AppError(401, ErrorCode.INVALID_CREDENTIALS, "Invalid email or password")
    return issue_session(session, user)


def refresh_session(session: Session, refresh_raw: str) -> str:
    token_hash = hash_refresh(refresh_raw)
    row = session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if row is None:
        raise AppError(401, ErrorCode.UNAUTHORIZED, "Invalid or expired session")
    if row.expires_at <= _now():
        session.execute(delete(RefreshToken).where(RefreshToken.id == row.id))
        session.commit()
        raise AppError(401, ErrorCode.UNAUTHORIZED, "Invalid or expired session")
    user = session.get(User, row.user_id)
    if user is None:
        session.execute(delete(RefreshToken).where(RefreshToken.id == row.id))
        session.commit()
        raise AppError(401, ErrorCode.UNAUTHORIZED, "Invalid or expired session")
    row.expires_at = _now() + REFRESH_TTL
    session.commit()
    return issue_token(user.id, user.role)


def revoke_refresh(session: Session, refresh_raw: str) -> None:
    token_hash = hash_refresh(refresh_raw)
    session.execute(delete(RefreshToken).where(RefreshToken.token_hash == token_hash))
    session.commit()


def current_user(session: Session, token: str) -> User:
    from src.core.security import decode_token

    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise AppError(401, ErrorCode.UNAUTHORIZED, "Invalid or expired token") from exc
    user_id = uuid.UUID(payload["sub"])
    user = session.get(User, user_id)
    if user is None:
        raise AppError(401, ErrorCode.UNAUTHORIZED, "Invalid or expired token")
    return user


async def provision(session: Session, email: str, password: str, role: str) -> User:
    if role not in ("SELLER", "BIDDER"):
        raise ValueError("invalid role")
    _validate_password(password)
    normalized = normalize_email(email)
    user = User(email=normalized, password_hash=await hash_password(password), role=role)
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise AppError(409, ErrorCode.EMAIL_TAKEN, "Email already registered") from exc
    session.add(Wallet(user_id=user.id))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise AppError(409, ErrorCode.EMAIL_TAKEN, "Email already registered") from exc
    session.refresh(user)
    return user
