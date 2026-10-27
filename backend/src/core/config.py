from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _validate_secret(value: str) -> str:
    if value.strip().lower() == "change-me":
        raise ValueError("Replace placeholder secrets in .env (must not be change-me)")
    if len(value) < 32:
        raise ValueError("Secret must be at least 32 characters")
    return value


def parse_cors_origins(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    hmac_secret: str
    alias_secret: str
    deployment_id: str = "hammerz"
    audit_dir: str = "/var/lib/hammerz/audit"
    max_deposit_cents: int = 10_000_000
    max_bidder_total_cents: int = 100_000_000
    max_bid_cents: int = 100_000_000
    settle_interval_seconds: int = 2
    cors_origins: str = "http://localhost,http://localhost:5173"
    currency: str = "USD"

    @field_validator("jwt_secret", "hmac_secret", "alias_secret")
    @classmethod
    def validate_secrets(cls, value: str) -> str:
        return _validate_secret(value)


@lru_cache
def get_settings() -> Settings:
    return Settings()
