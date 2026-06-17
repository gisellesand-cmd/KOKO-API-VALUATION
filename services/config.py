from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://koko:koko@localhost:5432/koko_mls"
    )
    ENVIRONMENT: Literal["dev", "staging", "prod", "test"] = "dev"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    comparable_freshness_days: int = 90
    catalog_cache_ttl_seconds: int = 300
    min_comparables_high_confidence: int = 30
    min_comparables_medium_confidence: int = 15
    min_comparables_low_confidence: int = 5

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


__all__ = ["Settings", "get_settings"]
