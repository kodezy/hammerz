from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    hmac_secret: str
    alias_secret: str
    deployment_id: str = "hammerz-eval"
    audit_dir: str = "/var/lib/hammerz/audit"
    max_deposit_cents: int = 10_000_000
    max_bidder_total_cents: int = 100_000_000
    max_bid_cents: int = 100_000_000
    settle_interval_seconds: int = 2
    cors_origins: list[str] = ["http://localhost:5173"]
    currency: str = "USD"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value  # type: ignore[return-value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
