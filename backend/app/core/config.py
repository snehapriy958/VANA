from typing import List, Union
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

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
        """Refuses to start in production if insecure default secrets are detected."""
        if self.ENVIRONMENT.lower() in ("production", "prod"):
            insecure_defaults = (
                "dev-secret-key-must-be-changed-in-production-at-least-32-chars",
                "secret",
                "changeme",
                "password",
            )
            if self.JWT_SECRET_KEY in insecure_defaults or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError(
                    "CRITICAL SECURITY ERROR: Production environment requires a secure, non-default "
                    "JWT_SECRET_KEY with at least 32 characters."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
