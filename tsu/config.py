from decimal import Decimal
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from tsu.native_profile import native_profile


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    admin_token: SecretStr = SecretStr("")
    database_url: SecretStr = SecretStr("sqlite:///./development.db")
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    tz: str = "Africa/Casablanca"
    daily_budget_usd: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=6)
    monthly_budget_usd: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=6)
    spending_authorized: bool = False
    publishing_authorized: bool = False
    enable_daily_scheduler: bool = False
    production_times: tuple[str, ...] = ()
    youtube_long_lived_grant_confirmed: bool = False
    production_live_validated: bool = False
    offhost_backup_confirmed: bool = False
    outbound_alerts_confirmed: bool = False
    public_information_approved: bool = False
    alert_email_enabled: bool = False
    alert_email_to: str = "admin.technoinno@gmail.com"
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_security: Literal["starttls", "ssl"] = "starttls"
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = ""
    openrouter_api_key: SecretStr = SecretStr("")
    creative_model: str = ""
    quality_model: str = ""
    video_model: str = ""
    data_root: Path = Path(".")
    public_origin: str = ""
    youtube_client_id: SecretStr = SecretStr("")
    youtube_client_secret: SecretStr = SecretStr("")
    youtube_login_hint: str = "admin.technoinno@gmail.com"
    youtube_channel_id: str = ""
    youtube_handle: str = "@techno-inno"
    token_encryption_key: SecretStr = SecretStr("")

    @field_validator("alert_email_to", "smtp_from")
    @classmethod
    def valid_mailbox(cls, value):
        from email.utils import parseaddr

        if value and (
            any(c in value for c in "\r\n") or parseaddr(value)[1] != value or value.count("@") != 1
        ):
            raise ValueError("Use a single plain email address")
        return value

    @field_validator("public_origin")
    @classmethod
    def valid_origin(cls, value: str) -> str:
        if not value:
            return value
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("PUBLIC_ORIGIN must be an HTTPS origin without path or credentials")
        return value.rstrip("/")

    @field_validator("tz")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @field_validator("production_times")
    @classmethod
    def valid_production_times(cls, values):
        from datetime import time

        if values and (len(values) != 2 or len(set(values)) != 2):
            raise ValueError("Select exactly two distinct daily production times")
        for value in values:
            if len(value) != 5 or time.fromisoformat(value).strftime("%H:%M") != value:
                raise ValueError("Use local times in HH:MM format")
        return tuple(sorted(values))

    @field_validator("admin_token")
    @classmethod
    def adequate_token(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value() and len(value.get_secret_value()) < 32:
            raise ValueError("ADMIN_TOKEN must have at least 32 characters")
        return value

    def gates(self) -> dict:
        return {
            "milestone": "production_workflow_prepared",
            "generation_available": bool(
                self.spending_authorized
                and self.daily_budget_usd > 0
                and self.monthly_budget_usd > 0
            ),
            "publishing_available": self.publishing_authorized,
            "production_workflow_implemented": True,
            "spending_authorized": self.spending_authorized,
            "publishing_authorized": self.publishing_authorized,
            "openrouter_key_configured": bool(self.openrouter_api_key.get_secret_value()),
            "reason": (
                "Execution requires authorized budgets and account permissions. "
                "Scheduled operation additionally requires validated prerequisites."
            ),
            "youtube_oauth_configured": all(
                (
                    self.public_origin,
                    self.youtube_client_id.get_secret_value(),
                    self.youtube_client_secret.get_secret_value(),
                    self.youtube_channel_id,
                    self.token_encryption_key.get_secret_value(),
                )
            ),
            "instagram": "paused by owner",
            "tiktok": "paused by owner",
            "production_profile": native_profile(),
        }
