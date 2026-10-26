import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.security import hash_password, issue_token, normalize_email, verify_password
from app.db.tables import User, Wallet


def _validate_password(password: str) -> None:
    if len(password) < 8 or len(password) > 128:
        raise AppError(
            422,
            ErrorCode.VALIDATION_ERROR,
            "Password must be 8–128 characters",
        )


async def register(session: Session, email: str, password: str) -> User:
    _validate_password(password)
    normalized = normalize_email(email)
    user = User(
        email=normalized,
        password_hash=await hash_password(password),
        role="BIDDER",
    )
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


async def login(session: Session, email: str, password: str) -> str:
    normalized = normalize_email(email)
    user = session.scalar(select(User).where(User.email == normalized))
    if user is None or not await verify_password(password, user.password_hash):
        raise AppError(401, ErrorCode.INVALID_CREDENTIALS, "Invalid email or password")
    return issue_token(user.id, user.role)


def current_user(session: Session, token: str) -> User:
    from app.core.security import decode_token

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
    user = User(
        email=normalized,
        password_hash=await hash_password(password),
        role=role,
    )
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
