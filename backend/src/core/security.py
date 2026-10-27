import asyncio
import unicodedata
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.core.config import get_settings

_ph = PasswordHasher()
JWT_ALG = "HS256"
JWT_TTL = timedelta(minutes=30)


def normalize_email(raw: str) -> str:
    return unicodedata.normalize("NFC", raw.strip()).lower()


async def hash_password(plain: str) -> str:
    return await asyncio.to_thread(_ph.hash, plain)


async def verify_password(plain: str, hashed: str) -> bool:
    def _verify() -> bool:
        try:
            return _ph.verify(hashed, plain)
        except VerifyMismatchError:
            return False

    return await asyncio.to_thread(_verify)


def issue_token(user_id: uuid.UUID, role: str) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "role": role, "iat": now, "exp": now + JWT_TTL}
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=JWT_ALG)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=[JWT_ALG], options={"require": ["exp", "sub"]})
    except jwt.InvalidTokenError as exc:
        raise ValueError("invalid token") from exc
