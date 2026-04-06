"""Configuration management with validation for RFID monitor."""

import sys
from pathlib import Path
from typing import Optional

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    webhook_url: HttpUrl = Field(
        ...,
        description="Base URL for Home Assistant webhook (tag ID will be appended)",
    )

    uptime_kuma_push_url: Optional[HttpUrl] = Field(
        default=None,
        description="Optional Uptime Kuma push monitor URL for heartbeat checks",
    )

    heartbeat_interval: int = Field(
        default=60,
        description="Interval in seconds between heartbeat checks",
        ge=10,  # Minimum 10 seconds
        le=3600,  # Maximum 1 hour
    )

    health_file_path: Path = Field(
        default=Path("/tmp/rfid-monitor-health"),
        description="Path to health check status file for Docker monitoring",
    )

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: HttpUrl) -> HttpUrl:
        """Ensure webhook URL uses http or https scheme."""
        if v.scheme not in ("http", "https"):
            raise ValueError(f"Webhook URL must use http or https scheme, got: {v.scheme}")
        return v

    @field_validator("uptime_kuma_push_url")
    @classmethod
    def validate_uptime_kuma_url(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Ensure Uptime Kuma URL uses http or https scheme if provided."""
        if v is not None and v.scheme not in ("http", "https"):
            raise ValueError(f"Uptime Kuma URL must use http or https scheme, got: {v.scheme}")
        return v


def load_config() -> Config:
    """Load and validate configuration from environment variables.

    Returns:
        Validated Config object.

    Exits:
        Exits with code 1 if configuration is invalid, printing error details.
    """
    try:
        return Config()  # type: ignore[call-arg]
    except Exception as e:
        print(f"Configuration validation failed: {e}", file=sys.stderr)
        sys.exit(1)
