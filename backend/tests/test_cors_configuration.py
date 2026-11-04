"""
VANA — CORS & Production Security Configuration Tests
Module: tests.test_cors_configuration
Verifies:
- Configured origins receive correct Access-Control-Allow-Origin header
- Credentialed CORS returns Access-Control-Allow-Credentials: true
- Unauthorized / untrusted origins are rejected without CORS headers
- Preflight OPTIONS requests handled correctly for authorized origins
- Production Settings validator rejects wildcard origins (* and *.vercel.app)
- Production Settings validator rejects localhost in CORS_ORIGINS
- Production Settings validator rejects localhost in DATABASE_URL
- Production Settings validator rejects weak JWT secrets
"""

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app


@pytest.mark.asyncio
async def test_cors_valid_origin_allowed():
    """Verifies that an explicitly configured origin receives Access-Control headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # http://localhost:5173 is in default CORS_ORIGINS
        response = await client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_invalid_origin_rejected():
    """Verifies that an untrusted origin does NOT receive Access-Control headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Untrusted external origins
        for untrusted_origin in [
            "https://malicious-site.com",
            "https://arbitrary-untrusted-preview.vercel.app",
            "http://evil-localhost:5173",
        ]:
            response = await client.get(
                "/health",
                headers={"Origin": untrusted_origin},
            )
            assert response.status_code == 200
            # Under CORS spec, unauthorized origins must NOT have Access-Control-Allow-Origin matching their origin
            assert response.headers.get("access-control-allow-origin") is None


@pytest.mark.asyncio
async def test_cors_preflight_options_request():
    """Verifies that CORS preflight OPTIONS requests are handled for valid vs invalid origins."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Valid origin preflight
        preflight_valid = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert preflight_valid.status_code == 200
        assert preflight_valid.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert preflight_valid.headers.get("access-control-allow-credentials") == "true"

        # Invalid origin preflight
        preflight_invalid = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://unauthorized-attacker.org",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert preflight_invalid.headers.get("access-control-allow-origin") is None


def test_production_settings_rejects_wildcard_cors():
    """Verifies that Settings refuses to initialize in production with wildcard CORS."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@ep-remote.neon.tech/neondb?ssl=require",
            JWT_SECRET_KEY="a-very-long-production-cryptographic-secret-key-32-chars",
            CORS_ORIGINS=["*"],
        )
    assert "Wildcard origin '*' is forbidden in production" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@ep-remote.neon.tech/neondb?ssl=require",
            JWT_SECRET_KEY="a-very-long-production-cryptographic-secret-key-32-chars",
            CORS_ORIGINS=["https://*.vercel.app"],
        )
    assert "Wildcard origin pattern" in str(exc_info.value)


def test_production_settings_rejects_localhost_cors():
    """Verifies that Settings refuses to initialize in production if localhost is in CORS_ORIGINS."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@ep-remote.neon.tech/neondb?ssl=require",
            JWT_SECRET_KEY="a-very-long-production-cryptographic-secret-key-32-chars",
            CORS_ORIGINS=["http://localhost:5173"],
        )
    assert "Production CORS_ORIGINS must not include local development origins" in str(exc_info.value)


def test_production_settings_rejects_local_database():
    """Verifies that Settings refuses to initialize in production with a localhost database."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://postgres@127.0.0.1:15432/vana_dev",
            JWT_SECRET_KEY="a-very-long-production-cryptographic-secret-key-32-chars",
            CORS_ORIGINS=["https://vana.earth"],
        )
    assert "cannot target localhost or loopback hostname" in str(exc_info.value)


def test_production_settings_rejects_weak_jwt():
    """Verifies that Settings refuses to initialize in production with an insecure or short JWT secret."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@ep-remote.neon.tech/neondb?ssl=require",
            JWT_SECRET_KEY="short-key",
            CORS_ORIGINS=["https://vana.earth"],
        )
    assert "JWT_SECRET_KEY with at least 32 characters" in str(exc_info.value)
