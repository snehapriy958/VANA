import os
import pytest
from alembic import command
from alembic.config import Config
from app.core.config import settings


def test_alembic_two_way_migration_cycle():
    """Verifies that Alembic can upgrade to head, downgrade to base, and upgrade to head again without errors."""
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.TEST_DATABASE_URL)

    # 1. Downgrade to base
    command.downgrade(alembic_cfg, "base")

    # 2. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # 3. Downgrade to base again
    command.downgrade(alembic_cfg, "base")

    # 4. Upgrade to head again (clean final state)
    command.upgrade(alembic_cfg, "head")
