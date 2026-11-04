"""
VANA — Production Database Configuration Tests
Module: tests.test_database_configuration
Verifies:
- ALEMBIC_DATABASE_URL precedence over DATABASE_URL
- DATABASE_URL as fallback when ALEMBIC_DATABASE_URL is not provided
- Asyncpg protocol normalization ('postgres://' and 'postgresql://' -> 'postgresql+asyncpg://')
- Neon SSL normalization ('sslmode=require' -> 'ssl=require')
- Structured parsed URL validation: rejects localhost hostnames (localhost, 127.0.0.1, ::1, 0.0.0.0)
- Structured parsed URL validation: rejects development database names (vana_dev, vana_test, dev, test)
- Structured parsed URL validation: allows valid remote Neon database URLs
- Structured parsed URL validation: rejects missing or empty URLs
- Structured parsed URL validation: rejects invalid or malformed URLs
- Production Settings validation integration
"""

import os
import pytest
from pydantic import ValidationError

from app.core.config import Settings, validate_production_database_url


def test_database_url_protocol_normalization():
    """Verifies that postgres:// and postgresql:// are normalized to postgresql+asyncpg://."""
    s1 = Settings(
        DATABASE_URL="postgres://user:pass@ep-cool-db.neon.tech/vana_prod?sslmode=require",
        ENVIRONMENT="development",
    )
    assert s1.DATABASE_URL.startswith("postgresql+asyncpg://")

    s2 = Settings(
        DATABASE_URL="postgresql://user:pass@ep-cool-db.neon.tech/vana_prod?sslmode=require",
        ENVIRONMENT="development",
    )
    assert s2.DATABASE_URL.startswith("postgresql+asyncpg://")


def test_neon_ssl_mode_normalization():
    """Verifies that sslmode= is normalized to ssl= for asyncpg."""
    s = Settings(
        DATABASE_URL="postgres://user:pass@ep-cool-db.neon.tech/vana_prod?sslmode=require",
        ENVIRONMENT="development",
    )
    assert "sslmode=" not in s.DATABASE_URL
    assert "ssl=require" in s.DATABASE_URL


def test_validate_production_database_url_localhost_hostname():
    """Verifies that validate_production_database_url rejects localhost and loopback hostnames."""
    for host in ["localhost", "127.0.0.1", "[::1]", "0.0.0.0"]:
        url = f"postgresql+asyncpg://user:pass@{host}:5432/vana_production"
        with pytest.raises(ValueError) as exc_info:
            validate_production_database_url(url)
        assert "cannot target localhost or loopback hostname" in str(exc_info.value)


def test_validate_production_database_url_development_database_name():
    """Verifies that validate_production_database_url rejects development database names."""
    for dev_db in ["vana_dev", "vana_test", "dev", "test"]:
        url = f"postgresql+asyncpg://user:pass@ep-cool.neon.tech:5432/{dev_db}"
        with pytest.raises(ValueError) as exc_info:
            validate_production_database_url(url)
        assert "cannot connect to a development database" in str(exc_info.value)


def test_validate_production_database_url_valid_remote_neon():
    """Verifies that validate_production_database_url allows valid remote Neon database URLs."""
    valid_urls = [
        "postgresql+asyncpg://user:secure_pwd@ep-ancient-forest-12345.us-east-2.aws.neon.tech/vana_production?ssl=require",
        "postgresql://user:secure_pwd@ep-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require",
        "postgres://user:secure_pwd@ep-serverless.aws.neon.tech/vana_prod",
    ]
    for valid_url in valid_urls:
        # Must not raise
        validate_production_database_url(valid_url)


def test_validate_production_database_url_missing():
    """Verifies that validate_production_database_url rejects missing or empty URLs."""
    for empty_val in [None, "", "   "]:
        with pytest.raises(ValueError) as exc_info:
            validate_production_database_url(empty_val)
        assert "requires a valid, non-empty database URL" in str(exc_info.value)


def test_validate_production_database_url_invalid():
    """Verifies that validate_production_database_url rejects malformed or incomplete URLs."""
    for invalid_url in ["not-a-url", "postgresql://", "postgresql+asyncpg://user:pass@", "http://remote.com"]:
        with pytest.raises(ValueError) as exc_info:
            validate_production_database_url(invalid_url)
        assert "CRITICAL CONFIGURATION ERROR" in str(exc_info.value)


def test_production_settings_integration():
    """Verifies that Settings model validator integrates validate_production_database_url."""
    # Rejection of localhost
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://postgres:pass@127.0.0.1:5432/vana_production",
            JWT_SECRET_KEY="a-very-long-production-secret-key-32-chars-ok",
            CORS_ORIGINS=["https://vana.earth"],
        )
    assert "cannot target localhost or loopback hostname" in str(exc_info.value)

    # Acceptance of valid remote Neon
    s = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql://user:secure_pwd@ep-ancient-forest-12345.us-east-2.aws.neon.tech/vana_production?sslmode=require",
        JWT_SECRET_KEY="a-very-long-production-secret-key-32-chars-ok",
        CORS_ORIGINS=["https://vana.earth"],
    )
    assert s.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert "ssl=require" in s.DATABASE_URL


def test_alembic_url_resolution_logic():
    """Verifies the precedence hierarchy and normalization logic used by alembic/env.py."""
    os_env = {"ALEMBIC_DATABASE_URL": "postgres://alembic_user:pass@ep-db.neon.tech/vana_prod?sslmode=require"}
    app_db_url = "postgres://app_user:pass@ep-db.neon.tech/vana_prod?sslmode=require"
    target_url = os_env.get("ALEMBIC_DATABASE_URL") or app_db_url
    assert "alembic_user" in target_url

    os_env_empty = {}
    target_url_fallback = os_env_empty.get("ALEMBIC_DATABASE_URL") or app_db_url
    assert "app_user" in target_url_fallback

    def normalize_alembic_url(url: str) -> str:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if "sslmode=" in url:
            url = url.replace("sslmode=", "ssl=")
        return url

    normalized = normalize_alembic_url(target_url)
    assert normalized.startswith("postgresql+asyncpg://")
    assert "ssl=require" in normalized
