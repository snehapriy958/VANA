"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-02 21:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("role IN ('ADMIN', 'PROJECT_MANAGER', 'FIELD_OFFICER')", name="chk_user_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_index("idx_users_role", "users", ["role"], unique=False)

    # 2. projects
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("boundary_geojson", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'COMPLETED', 'ARCHIVED')", name="chk_project_status"),
        sa.CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="chk_project_latitude"),
        sa.CheckConstraint("longitude >= -180.0 AND longitude <= 180.0", name="chk_project_longitude"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("idx_projects_status", "projects", ["status"], unique=False)
    op.create_index("idx_projects_coordinates", "projects", ["latitude", "longitude"], unique=False)

    # 3. project_assignments
    op.create_table(
        "project_assignments",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_role", sa.String(length=32), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("assigned_role IN ('PROJECT_MANAGER', 'FIELD_OFFICER')", name="chk_assignment_role"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_user_assignment"),
    )
    op.create_index("idx_project_assignments_user", "project_assignments", ["user_id"], unique=False)
    op.create_index("idx_project_assignments_project", "project_assignments", ["project_id"], unique=False)

    # 4. project_targets
    op.create_table(
        "project_targets",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("metric_code", sa.String(length=64), nullable=False),
        sa.Column("target_quantity", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("target_unit", sa.String(length=32), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("milestone_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("target_quantity > 0", name="chk_target_quantity_positive"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_project_targets_no_milestone",
        "project_targets",
        ["project_id", "metric_code"],
        unique=True,
        postgresql_where=sa.text("milestone_id IS NULL"),
    )
    op.create_index(
        "uq_project_targets_with_milestone",
        "project_targets",
        ["project_id", "metric_code", "milestone_id"],
        unique=True,
        postgresql_where=sa.text("milestone_id IS NOT NULL"),
    )
    op.create_index("idx_project_targets_project", "project_targets", ["project_id"], unique=False)

    # 5. field_activities
    op.create_table(
        "field_activities",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("metric_code", sa.String(length=64), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("current_revision_id", sa.Uuid(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_field_activities_project", "field_activities", ["project_id"], unique=False)
    op.create_index("idx_field_activities_creator", "field_activities", ["created_by_id"], unique=False)
    op.create_index("idx_field_activities_metric", "field_activities", ["metric_code"], unique=False)
    op.create_index("idx_field_activities_archived", "field_activities", ["is_archived"], unique=False)

    # 6. activity_revisions
    op.create_table(
        "activity_revisions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("gps_accuracy_meters", sa.Float(), nullable=True),
        sa.Column("field_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("is_active_ledger_entry", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("verifier_id", sa.Uuid(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason_code", sa.String(length=64), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("revision_number >= 1", name="chk_revision_number_positive"),
        sa.CheckConstraint("quantity > 0", name="chk_revision_quantity_positive"),
        sa.CheckConstraint("status IN ('PENDING', 'VERIFIED', 'REJECTED')", name="chk_revision_status"),
        sa.CheckConstraint("latitude IS NULL OR (latitude >= -90.0 AND latitude <= 90.0)", name="chk_revision_latitude"),
        sa.CheckConstraint("longitude IS NULL OR (longitude >= -180.0 AND longitude <= 180.0)", name="chk_revision_longitude"),
        sa.CheckConstraint("gps_accuracy_meters IS NULL OR gps_accuracy_meters >= 0", name="chk_revision_gps_accuracy"),
        sa.CheckConstraint(
            "(is_active_ledger_entry = FALSE) OR (is_active_ledger_entry = TRUE AND status = 'VERIFIED')",
            name="chk_active_ledger_verified",
        ),
        sa.CheckConstraint(
            "(status != 'REJECTED') OR (status = 'REJECTED' AND rejection_reason_code IS NOT NULL AND review_notes IS NOT NULL)",
            name="chk_rejection_reason_required",
        ),
        sa.CheckConstraint(
            "(status != 'VERIFIED') OR (status = 'VERIFIED' AND verifier_id IS NOT NULL AND verified_at IS NOT NULL)",
            name="chk_verification_signature_required",
        ),
        sa.CheckConstraint(
            "rejection_reason_code IS NULL OR rejection_reason_code IN ('INSUFFICIENT_EVIDENCE', 'COORDINATES_MISMATCH', 'INCORRECT_UNIT_OR_QUANTITY', 'DUPLICATE_SUBMISSION', 'DATA_ENTRY_ERROR')",
            name="chk_rejection_reason_code_valid",
        ),
        sa.ForeignKeyConstraint(["activity_id"], ["field_activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verifier_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("activity_id", "revision_number", name="uq_activity_revision_number"),
    )
    # The crucial partial unique index preventing double-counting
    op.create_index(
        "uq_activity_single_active_ledger",
        "activity_revisions",
        ["activity_id"],
        unique=True,
        postgresql_where=sa.text("is_active_ledger_entry = TRUE"),
    )
    op.create_index("idx_activity_revisions_activity", "activity_revisions", ["activity_id"], unique=False)
    op.create_index("idx_activity_revisions_status", "activity_revisions", ["status"], unique=False)
    op.create_index("idx_activity_revisions_active_ledger", "activity_revisions", ["is_active_ledger_entry"], unique=False)
    op.create_index("idx_activity_revisions_verifier", "activity_revisions", ["verifier_id"], unique=False)

    # 7. Add foreign key from field_activities.current_revision_id to activity_revisions.id
    op.create_foreign_key(
        "fk_field_activities_current_revision",
        "field_activities",
        "activity_revisions",
        ["current_revision_id"],
        ["id"],
        ondelete="SET NULL",
        deferrable=True,
        initially="DEFERRED",
    )

    # 8. evidence_files
    op.create_table(
        "evidence_files",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("file_storage_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("file_size_bytes > 0", name="chk_evidence_file_size_positive"),
        sa.ForeignKeyConstraint(["activity_id"], ["field_activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["revision_id"], ["activity_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_evidence_files_activity", "evidence_files", ["activity_id"], unique=False)
    op.create_index("idx_evidence_files_revision", "evidence_files", ["revision_id"], unique=False)

    # 9. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("previous_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"], unique=False)
    op.create_index("idx_audit_logs_actor", "audit_logs", ["actor_id"], unique=False)
    op.create_index("idx_audit_logs_created_at_desc", "audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    # 1. Drop foreign key circular reference
    op.drop_constraint("fk_field_activities_current_revision", "field_activities", type_="foreignkey")

    # 2. Drop audit_logs
    op.drop_index("idx_audit_logs_created_at_desc", table_name="audit_logs")
    op.drop_index("idx_audit_logs_actor", table_name="audit_logs")
    op.drop_index("idx_audit_logs_entity", table_name="audit_logs")
    op.drop_table("audit_logs")

    # 3. Drop evidence_files
    op.drop_index("idx_evidence_files_revision", table_name="evidence_files")
    op.drop_index("idx_evidence_files_activity", table_name="evidence_files")
    op.drop_table("evidence_files")

    # 4. Drop activity_revisions
    op.drop_index("idx_activity_revisions_verifier", table_name="activity_revisions")
    op.drop_index("idx_activity_revisions_active_ledger", table_name="activity_revisions")
    op.drop_index("idx_activity_revisions_status", table_name="activity_revisions")
    op.drop_index("idx_activity_revisions_activity", table_name="activity_revisions")
    op.drop_index("uq_activity_single_active_ledger", table_name="activity_revisions")
    op.drop_table("activity_revisions")

    # 5. Drop field_activities
    op.drop_index("idx_field_activities_archived", table_name="field_activities")
    op.drop_index("idx_field_activities_metric", table_name="field_activities")
    op.drop_index("idx_field_activities_creator", table_name="field_activities")
    op.drop_index("idx_field_activities_project", table_name="field_activities")
    op.drop_table("field_activities")

    # 6. Drop project_targets
    op.drop_index("idx_project_targets_project", table_name="project_targets")
    op.drop_index("uq_project_targets_with_milestone", table_name="project_targets")
    op.drop_index("uq_project_targets_no_milestone", table_name="project_targets")
    op.drop_table("project_targets")

    # 7. Drop project_assignments
    op.drop_index("idx_project_assignments_project", table_name="project_assignments")
    op.drop_index("idx_project_assignments_user", table_name="project_assignments")
    op.drop_table("project_assignments")

    # 8. Drop projects
    op.drop_index("idx_projects_coordinates", table_name="projects")
    op.drop_index("idx_projects_status", table_name="projects")
    op.drop_table("projects")

    # 9. Drop users
    op.drop_index("idx_users_role", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
