from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class ErrorCode:
    AUDIT_UNAVAILABLE = "AUDIT_UNAVAILABLE"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    EMAIL_TAKEN = "EMAIL_TAKEN"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    AUCTION_NOT_LIVE = "AUCTION_NOT_LIVE"
    AUCTION_CLOSED = "AUCTION_CLOSED"
    AUCTION_CANCELLED = "AUCTION_CANCELLED"
    AUCTION_NOT_STARTED = "AUCTION_NOT_STARTED"
    BID_TOO_LOW = "BID_TOO_LOW"
    ALREADY_LEADING = "ALREADY_LEADING"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    IDEMPOTENCY_KEY_REUSED = "IDEMPOTENCY_KEY_REUSED"
    IDEMPOTENCY_KEY_REQUIRED = "IDEMPOTENCY_KEY_REQUIRED"
    OPERATION_PENDING = "OPERATION_PENDING"
    INTEGRITY_CONFLICT = "INTEGRITY_CONFLICT"
    CATALOG_UNAVAILABLE = "CATALOG_UNAVAILABLE"
    WALLET_LIMIT = "WALLET_LIMIT"
    RATE_LIMITED = "RATE_LIMITED"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
