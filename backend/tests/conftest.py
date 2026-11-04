import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from alembic import command
from alembic.config import Config

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app

# Test engine with NullPool to prevent connection reuse issues in tests
test_engine = create_async_engine(
    settings.TEST_DATABASE_URL,
    echo=False,
    future=True,
    poolclass=pool.NullPool,
    connect_args={
        "command_timeout": 30,
        "timeout": 10,
    },
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Apply Alembic migrations to the test database before running tests."""
    old_alembic_url = os.environ.get("ALEMBIC_DATABASE_URL")
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.TEST_DATABASE_URL)
    os.environ["ALEMBIC_DATABASE_URL"] = settings.TEST_DATABASE_URL
    
    try:
        # Run migration upgrade to head
        command.upgrade(alembic_cfg, "head")
        yield
    finally:
        if old_alembic_url is not None:
            os.environ["ALEMBIC_DATABASE_URL"] = old_alembic_url
        else:
            os.environ.pop("ALEMBIC_DATABASE_URL", None)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Provides an isolated transactional database session for a test with automatic rollback."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Provides an HTTPX AsyncClient with isolated database session per request."""
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
