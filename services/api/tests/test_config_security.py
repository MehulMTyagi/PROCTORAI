import pytest
from pydantic import ValidationError

from app.core.config import DEV_JWT_SECRET, Settings


def production_settings(**overrides) -> Settings:
    values = {
        "app_env": "production",
        "jwt_secret": "s" * 48,
        "jwt_issuer": "proctorai-test-api",
        "jwt_audience": "proctorai-test-clients",
        "cors_origins": ["https://portal.example.edu"],
        "trusted_hosts": ["api.example.edu"],
        "database_url": (
            "postgresql+psycopg://app:password@db.example.edu/proctorai?sslmode=verify-full"
        ),
        "smtp_host": "smtp.example.edu",
        "smtp_from_email": "no-reply@example.edu",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_config_accepts_exact_secure_origins_and_tls_database() -> None:
    settings = production_settings()
    assert settings.app_env == "production"


@pytest.mark.parametrize(
    "overrides",
    [
        {"jwt_secret": DEV_JWT_SECRET},
        {"cors_origins": ["https://*.example.edu"]},
        {"cors_origin_regex": "https://.*"},
        {"trusted_hosts": ["*"]},
        {"database_url": "postgresql+psycopg://app:password@db/proctorai"},
        {"smtp_host": None},
    ],
)
def test_production_config_rejects_unsafe_settings(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        production_settings(**overrides)
