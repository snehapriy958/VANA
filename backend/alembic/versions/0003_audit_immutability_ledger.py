"""audit_immutability_ledger

Revision ID: 0003_audit_immutability_ledger
Revises: 0002_field_monitoring
Create Date: 2026-11-04 13:15:00.000000

"""
import json
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.domains.audit.hashing import (
    CURRENT_HASH_VERSION,
    GENESIS_HASH,
    build_canonical_payload,
    compute_event_hash,
)

# revision identifiers, used by Alembic.
revision: str = "0003_audit_immutability_ledger"
down_revision: Union[str, None] = "0002_field_monitoring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create audit_chain_head anchor table for atomic row-locking concurrency
    op.create_table(
        "audit_chain_head",
        sa.Column("id", sa.Integer(), primary_key=True, server_default=sa.text("1")),
        sa.Column("last_sequence_number", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "last_event_hash",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'0000000000000000000000000000000000000000000000000000000000000000'"),
        ),
        sa.Column("total_events", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("id = 1", name="chk_audit_chain_head_single_row"),
    )

    # 2. Add columns to audit_logs (nullable initially to allow historical backfill)
    op.add_column("audit_logs", sa.Column("sequence_number", sa.BigInteger(), nullable=True))
    op.add_column("audit_logs", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.add_column("audit_logs", sa.Column("previous_hash", sa.String(length=64), nullable=True))
    op.add_column("audit_logs", sa.Column("current_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "audit_logs",
        sa.Column("hash_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column(
        "audit_logs",
        sa.Column("canonical_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("audit_logs", sa.Column("correlation_id", sa.String(length=64), nullable=True))
    op.add_column(
        "audit_logs",
        sa.Column("is_backfilled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    # 3. Add foreign key for project_id
    op.create_foreign_key(
        "fk_audit_logs_project",
        "audit_logs",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 4. Backfill existing records (if any exist) chronologically
    bind = op.get_bind()
    existing_rows = bind.execute(
        sa.text(
            "SELECT id, actor_id, action_type, entity_type, entity_id, previous_state, new_state, ip_address, created_at "
            "FROM audit_logs ORDER BY created_at ASC, id ASC"
        )
    ).fetchall()

    last_seq = 0
    last_hash = GENESIS_HASH

    if existing_rows:
        for idx, row in enumerate(existing_rows, start=1):
            row_id = row[0]
            actor_id = row[1]
            action_type = row[2]
            entity_type = row[3]
            entity_id = row[4]
            prev_state = row[5]
            new_state = row[6]
            ip_addr = row[7]
            created_at = row[8]

            # Resolve project_id if present in entity or states
            extracted_pid = None
            if entity_type.lower() == "project":
                extracted_pid = entity_id
            elif new_state and isinstance(new_state, dict) and new_state.get("project_id"):
                try:
                    extracted_pid = uuid.UUID(str(new_state["project_id"]))
                except (ValueError, TypeError):
                    extracted_pid = None
            elif prev_state and isinstance(prev_state, dict) and prev_state.get("project_id"):
                try:
                    extracted_pid = uuid.UUID(str(prev_state["project_id"]))
                except (ValueError, TypeError):
                    extracted_pid = None

            # Verify that extracted_pid actually exists in projects table to satisfy foreign key
            if extracted_pid:
                proj_exists = bind.execute(
                    sa.text("SELECT 1 FROM projects WHERE id = :pid"),
                    {"pid": str(extracted_pid)},
                ).scalar()
                if not proj_exists:
                    extracted_pid = None

            canonical_payload = build_canonical_payload(
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                actor_id=actor_id,
                project_id=extracted_pid,
                previous_state=prev_state,
                new_state=new_state,
                ip_address=ip_addr,
                correlation_id=None,
                is_backfilled=True,
            )

            current_hash = compute_event_hash(
                sequence_number=idx,
                event_id=row_id,
                timestamp=created_at,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                previous_hash=last_hash,
                canonical_payload=canonical_payload,
                actor_id=actor_id,
                project_id=extracted_pid,
                correlation_id=None,
                hash_version=CURRENT_HASH_VERSION,
            )

            bind.execute(
                sa.text(
                    "UPDATE audit_logs SET "
                    "sequence_number = :seq, "
                    "project_id = :pid, "
                    "previous_hash = :prev, "
                    "current_hash = :curr, "
                    "canonical_payload = CAST(:payload AS jsonb), "
                    "is_backfilled = true "
                    "WHERE id = :rid"
                ),
                {
                    "seq": idx,
                    "pid": str(extracted_pid) if extracted_pid else None,
                    "prev": last_hash,
                    "curr": current_hash,
                    "payload": json.dumps(canonical_payload),
                    "rid": str(row_id),
                },
            )
            last_seq = idx
            last_hash = current_hash

    # Initialize audit_chain_head checkpoint
    bind.execute(
        sa.text(
            "INSERT INTO audit_chain_head (id, last_sequence_number, last_event_hash, total_events, updated_at) "
            "VALUES (1, :seq, :hash, :total, CURRENT_TIMESTAMP) "
            "ON CONFLICT (id) DO UPDATE SET "
            "last_sequence_number = :seq, "
            "last_event_hash = :hash, "
            "total_events = :total, "
            "updated_at = CURRENT_TIMESTAMP"
        ),
        {"seq": last_seq, "hash": last_hash, "total": last_seq},
    )

    # 5. Enforce NOT NULL on backfilled columns
    op.alter_column("audit_logs", "sequence_number", nullable=False)
    op.alter_column("audit_logs", "previous_hash", nullable=False)
    op.alter_column("audit_logs", "current_hash", nullable=False)
    op.alter_column("audit_logs", "canonical_payload", nullable=False)

    # 6. Create indexes and unique constraints
    op.create_index("uq_audit_logs_sequence_number", "audit_logs", ["sequence_number"], unique=True)
    op.create_index("uq_audit_logs_current_hash", "audit_logs", ["current_hash"], unique=True)
    op.create_index("idx_audit_logs_project_id", "audit_logs", ["project_id"], unique=False)
    op.create_index(
        "idx_audit_logs_project_created", "audit_logs", ["project_id", "created_at"], unique=False
    )
    op.create_index("idx_audit_logs_correlation_id", "audit_logs", ["correlation_id"], unique=False)


def downgrade() -> None:
    # 1. Drop indexes
    op.drop_index("idx_audit_logs_correlation_id", table_name="audit_logs")
    op.drop_index("idx_audit_logs_project_created", table_name="audit_logs")
    op.drop_index("idx_audit_logs_project_id", table_name="audit_logs")
    op.drop_index("uq_audit_logs_current_hash", table_name="audit_logs")
    op.drop_index("uq_audit_logs_sequence_number", table_name="audit_logs")

    # 2. Drop foreign key
    op.drop_constraint("fk_audit_logs_project", "audit_logs", type_="foreignkey")

    # 3. Drop columns
    op.drop_column("audit_logs", "is_backfilled")
    op.drop_column("audit_logs", "correlation_id")
    op.drop_column("audit_logs", "canonical_payload")
    op.drop_column("audit_logs", "hash_version")
    op.drop_column("audit_logs", "current_hash")
    op.drop_column("audit_logs", "previous_hash")
    op.drop_column("audit_logs", "project_id")
    op.drop_column("audit_logs", "sequence_number")

    # 4. Drop audit_chain_head table
    op.drop_table("audit_chain_head")
