from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "local-development-only-change-before-deployment"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ProctorAI API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://proctorai:proctorai@localhost:5432/proctorai"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "tauri://localhost",
            "http://tauri.localhost",
        ]
    )
    cors_origin_regex: str | None = None
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "tauri.localhost", "testserver"]
    )

    jwt_secret: str = DEV_JWT_SECRET
    jwt_access_minutes: int = 15
    jwt_issuer: str = "proctorai-api"
    jwt_audience: str = "proctorai-clients"
    student_email_domain: str = "bennett.edu.in"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None

    evidence_dir: str = "./data/evidence"
    identity_reference_dir: str = "./data/identity_references"
    max_evidence_mb: int = 25
    ws_heartbeat_seconds: int = 10

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("trusted_hosts", mode="before")
    @classmethod
    def parse_trusted_hosts(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [host.strip() for host in value.split(",") if host.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env.lower() in {"production", "prod"}:
            if (
                self.jwt_secret == DEV_JWT_SECRET
                or self.jwt_secret.lower() in {"changeme", "dev", "secret"}
                or len(self.jwt_secret) < 32
            ):
                raise ValueError("JWT_SECRET must be set to a strong 32+ character value in production")
            if not self.cors_origins or any(
                not (
                    origin.startswith("https://")
                    or origin in {"tauri://localhost", "http://tauri.localhost"}
                )
                or "*" in origin
                for origin in self.cors_origins
            ):
                raise ValueError("Production CORS_ORIGINS must be exact HTTPS origins")
            if self.cors_origin_regex:
                raise ValueError("CORS_ORIGIN_REGEX is not allowed in production")
            if not self.trusted_hosts or "*" in self.trusted_hosts:
                raise ValueError("Production TRUSTED_HOSTS must list exact hostnames")
            if self.jwt_access_minutes > 15:
                raise ValueError("JWT_ACCESS_MINUTES must be 15 or less in production")
            if not self.database_url.startswith("postgresql+psycopg://") or not any(
                mode in self.database_url.lower()
                for mode in ("sslmode=require", "sslmode=verify-ca", "sslmode=verify-full")
            ):
                raise ValueError(
                    "Production DATABASE_URL must use PostgreSQL with an explicit SSL mode"
                )
            if not self.smtp_host or not self.smtp_from_email:
                raise ValueError("SMTP_HOST and SMTP_FROM_EMAIL are required in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
