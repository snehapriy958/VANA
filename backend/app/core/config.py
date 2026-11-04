from typing import List, Optional, Union
from urllib.parse import urlsplit
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def validate_production_database_url(url: Optional[str]) -> None:
    """
    Validates that a production database URL targets a remote host and valid production database.
    Uses structured URL parsing (hostname and path) rather than simple substring matching.
    """
    if not url or not str(url).strip():
        raise ValueError(
            "CRITICAL CONFIGURATION ERROR: Production environment requires a valid, non-empty database URL."
        )

    clean_url = str(url).strip()
    try:
        parsed = urlsplit(clean_url)
    except Exception as exc:
        raise ValueError(
            f"CRITICAL CONFIGURATION ERROR: Malformed database URL ({clean_url}): {exc}"
        )

    if not parsed.scheme or not parsed.hostname:
        raise ValueError(
            f"CRITICAL CONFIGURATION ERROR: Invalid database URL format without hostname ({clean_url})."
        )

    # 1. Hostname validation: reject localhost, loopback, and local IPs
    hostname = (parsed.hostname or "").lower()
    if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise ValueError(
            f"CRITICAL CONFIGURATION ERROR: Production database URL cannot target localhost or loopback hostname ({hostname}). "
            "Please provide a valid remote production database connection."
        )

    # 2. Database name validation: reject development database names
    db_name = (parsed.path or "").lstrip("/").lower()
    if not db_name:
        raise ValueError(
            f"CRITICAL CONFIGURATION ERROR: Database URL is missing database name ({clean_url})."
        )
    if db_name in ("vana_dev", "vana_test", "dev", "test"):
        raise ValueError(
            f"CRITICAL CONFIGURATION ERROR: Production environment cannot connect to a development database ({db_name}). "
            "Please provide a production database name (e.g. vana_production, neondb)."
        )


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "VANA Environmental Operations Platform"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres@127.0.0.1:15432/vana_dev"
    TEST_DATABASE_URL: str = "postgresql+asyncpg://postgres@127.0.0.1:15432/vana_test"

    # Security
    JWT_SECRET_KEY: str = "dev-secret-key-must-be-changed-in-production-at-least-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Storage
    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_ROOT: str = "uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB configurable ceiling for free tier

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("STORAGE_BACKEND", mode="before")
    @classmethod
    def normalize_storage_backend(cls, v: str) -> str:
        if isinstance(v, str):
            clean = v.strip().lower()
            if clean in ("postgres", "postgresql", "db"):
                return "database"
            return clean
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        """Normalizes standard postgresql:// URLs and sslmode parameters for asyncpg and Neon."""
        if isinstance(v, str):
            url = v.strip()
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            # asyncpg accepts ssl= instead of sslmode=
            if "sslmode=" in url:
                url = url.replace("sslmode=", "ssl=")
            return url
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Refuses to start in production if insecure default secrets or invalid configurations are detected."""
        if self.ENVIRONMENT.lower() in ("production", "prod"):
            # 1. Validate JWT secret
            insecure_defaults = (
                "dev-secret-key-must-be-changed-in-production-at-least-32-chars",
                "dev-vana-secret-key-32-chars-long-minimum-secure",
                "secret",
                "changeme",
                "password",
            )
            if self.JWT_SECRET_KEY in insecure_defaults or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError(
                    "CRITICAL SECURITY ERROR: Production environment requires a secure, non-default "
                    "JWT_SECRET_KEY with at least 32 characters."
                )

            # 2. Validate Database URL does not target localhost/development DB using parsed URL validation
            validate_production_database_url(self.DATABASE_URL)

            # 3. Validate CORS origins in production
            if not self.CORS_ORIGINS:
                raise ValueError(
                    "CRITICAL CONFIGURATION ERROR: Production environment requires at least one explicit CORS origin in CORS_ORIGINS."
                )
            for origin in self.CORS_ORIGINS:
                if origin == "*":
                    raise ValueError(
                        "CRITICAL SECURITY ERROR: Wildcard origin '*' is forbidden in production when credentials are enabled."
                    )
                if "*" in origin:
                    raise ValueError(
                        f"CRITICAL SECURITY ERROR: Wildcard origin pattern '{origin}' is not supported by standard credentialed CORS. Provide exact origins."
                    )
                if any(dev_host in origin.lower() for dev_host in ("localhost", "127.0.0.1")):
                    raise ValueError(
                        f"CRITICAL CONFIGURATION ERROR: Production CORS_ORIGINS must not include local development origins ({origin})."
                    )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
