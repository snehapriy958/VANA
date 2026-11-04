import asyncio
import concurrent.futures
from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings, validate_production_database_url
from app.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Resolve database URL in strict priority order:
# 1. ALEMBIC_DATABASE_URL (environment override)
# 2. settings.DATABASE_URL (application settings, normalized)
# 3. Fallback from alembic.ini (development only)
target_url = os.environ.get("ALEMBIC_DATABASE_URL") or settings.DATABASE_URL or config.get_main_option("sqlalchemy.url")

# Normalize URL for asyncpg / Neon
if target_url:
    target_url = target_url.strip()
    if target_url.startswith("postgres://"):
        target_url = target_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif target_url.startswith("postgresql://") and not target_url.startswith("postgresql+asyncpg://"):
        target_url = target_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "sslmode=" in target_url:
        target_url = target_url.replace("sslmode=", "ssl=")

# Production validation guard: fail immediately if production is configured with invalid/local/dev database
if settings.ENVIRONMENT.lower() in ("production", "prod"):
    validate_production_database_url(target_url)

if target_url:
    config.set_main_option("sqlalchemy.url", target_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with an AsyncEngine."""
    db_url = config.get_main_option("sqlalchemy.url")
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = db_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode, handling both CLI and active test event loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # An event loop is already running (e.g. within pytest-asyncio).
        # Execute run_async_migrations in a clean worker thread.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, run_async_migrations())
            future.result()
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
