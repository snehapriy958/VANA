import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_direct_database_connection(db_session: AsyncSession):
    """Verifies that direct asynchronous connection to PostgreSQL executes queries."""
    result = await db_session.execute(text("SELECT 1 AS alive"))
    row = result.scalar()
    assert row == 1


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    """Verifies that the /health endpoint reports healthy status and connected database."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["platform"] == "VANA"
