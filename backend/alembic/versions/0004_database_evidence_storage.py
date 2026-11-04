"""database_evidence_storage

Revision ID: 0004_database_evidence_storage
Revises: 0003_audit_immutability_ledger
Create Date: 2026-11-04 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_database_evidence_storage"
down_revision: Union[str, None] = "0003_audit_immutability_ledger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create evidence_blobs table for database-backed evidence storage (Render Free / Neon zero-cost)
    op.create_table(
        "evidence_blobs",
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("file_data", sa.LargeBinary(), nullable=False),
        sa.Column("sha256_checksum", sa.String(length=64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("storage_key", name="pk_evidence_blobs"),
    )
    op.create_index("ix_evidence_blobs_sha256_checksum", "evidence_blobs", ["sha256_checksum"], unique=False)

    # 2. Add sha256_checksum column to evidence_files for explicit cryptographic integrity tracking
    op.add_column("evidence_files", sa.Column("sha256_checksum", sa.String(length=64), nullable=True))
    op.create_index("ix_evidence_files_sha256_checksum", "evidence_files", ["sha256_checksum"], unique=False)


def downgrade() -> None:
    # 1. Drop index and column from evidence_files
    op.drop_index("ix_evidence_files_sha256_checksum", table_name="evidence_files")
    op.drop_column("evidence_files", "sha256_checksum")

    # 2. Drop evidence_blobs table and index
    op.drop_index("ix_evidence_blobs_sha256_checksum", table_name="evidence_blobs")
    op.drop_table("evidence_blobs")
