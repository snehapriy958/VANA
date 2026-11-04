"""field_monitoring

Revision ID: 0002_field_monitoring
Revises: 0001_initial_schema
Create Date: 2026-11-03 23:38:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_field_monitoring"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add composite unique constraint on field_activities for composite foreign keys
    op.create_unique_constraint(
        "uq_field_activities_id_project",
        "field_activities",
        ["id", "project_id"],
    )

    # 2. Table: field_inspections
    op.create_table(
        "field_inspections",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("linked_activity_id", sa.Uuid(), nullable=True),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'SCHEDULED'"), nullable=False),
        sa.Column("inspection_type", sa.String(length=32), server_default=sa.text("'ROUTINE'"), nullable=False),
        sa.Column("assigned_to_id", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("vegetation_health_score", sa.Integer(), nullable=True),
        sa.Column("canopy_condition", sa.String(length=32), nullable=True),
        sa.Column("soil_moisture_condition", sa.String(length=32), nullable=True),
        sa.Column("threats_detected", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("addenda", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_to_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("id", "project_id", name="uq_inspections_id_project"),
        sa.CheckConstraint("status IN ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')", name="chk_inspection_status"),
        sa.CheckConstraint("inspection_type IN ('ROUTINE', 'SURVIVAL_CHECK', 'MAINTENANCE_AUDIT', 'EMERGENCY')", name="chk_inspection_type"),
        sa.CheckConstraint("vegetation_health_score IS NULL OR (vegetation_health_score >= 1 AND vegetation_health_score <= 5)", name="chk_vegetation_health_score"),
        sa.CheckConstraint("canopy_condition IS NULL OR canopy_condition IN ('EXCELLENT', 'HEALTHY', 'STRESSED', 'CRITICAL')", name="chk_canopy_condition"),
        sa.CheckConstraint("soil_moisture_condition IS NULL OR soil_moisture_condition IN ('SATURATED', 'ADEQUATE', 'DRY', 'SEVERELY_PARCHED')", name="chk_soil_moisture"),
    )
    # Composite foreign key with column-specific SET NULL for linked_activity_id
    op.execute(
        "ALTER TABLE field_inspections ADD CONSTRAINT fk_inspections_linked_activity "
        "FOREIGN KEY (linked_activity_id, project_id) REFERENCES field_activities(id, project_id) "
        "ON DELETE SET NULL (linked_activity_id);"
    )
    op.create_index("idx_inspections_project_status_date", "field_inspections", ["project_id", "status", "scheduled_date"], unique=False)
    op.create_index("idx_inspections_assigned", "field_inspections", ["assigned_to_id", "status"], unique=False)

    # 3. Table: maintenance_tasks
    op.create_table(
        "maintenance_tasks",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("inspection_id", sa.Uuid(), nullable=True),
        sa.Column("activity_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), server_default=sa.text("'MEDIUM'"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'TODO'"), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("assigned_to_id", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_to_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("id", "project_id", name="uq_tasks_id_project"),
        sa.CheckConstraint("category IN ('IRRIGATION', 'WEEDING', 'MULCHING', 'FENCING_REPAIR', 'REPLANTING_PREP', 'PEST_CONTROL', 'SOIL_ENRICHMENT', 'OTHER')", name="chk_task_category"),
        sa.CheckConstraint("priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')", name="chk_task_priority"),
        sa.CheckConstraint("status IN ('TODO', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')", name="chk_task_status"),
    )
    # Composite foreign keys with column-specific SET NULL
    op.execute(
        "ALTER TABLE maintenance_tasks ADD CONSTRAINT fk_tasks_inspection "
        "FOREIGN KEY (inspection_id, project_id) REFERENCES field_inspections(id, project_id) "
        "ON DELETE SET NULL (inspection_id);"
    )
    op.execute(
        "ALTER TABLE maintenance_tasks ADD CONSTRAINT fk_tasks_activity "
        "FOREIGN KEY (activity_id, project_id) REFERENCES field_activities(id, project_id) "
        "ON DELETE SET NULL (activity_id);"
    )
    op.create_index("idx_tasks_project_status_due", "maintenance_tasks", ["project_id", "status", "due_date"], unique=False)
    op.create_index("idx_tasks_assigned", "maintenance_tasks", ["assigned_to_id", "status"], unique=False)

    # 4. Table: survival_observations
    op.create_table(
        "survival_observations",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=True),
        sa.Column("inspection_id", sa.Uuid(), nullable=True),
        sa.Column("plot_identifier", sa.String(length=64), nullable=False),
        sa.Column("cohort_identifier", sa.String(length=64), nullable=False),
        sa.Column("methodology", sa.String(length=32), server_default=sa.text("'SAMPLE_PLOT'"), nullable=False),
        sa.Column("coverage_area_sqm", sa.Float(), nullable=True),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("alive_count", sa.Integer(), nullable=False),
        sa.Column("dead_count", sa.Integer(), nullable=False),
        sa.Column("mortality_causes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("is_definitive", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("superseded_by_id", sa.Uuid(), nullable=True),
        sa.Column("correction_notes", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("id", "project_id", name="uq_survival_obs_id_project"),
        sa.CheckConstraint("methodology IN ('SAMPLE_PLOT', 'TRANSECT', 'FULL_CENSUS')", name="chk_survival_methodology"),
        sa.CheckConstraint("sample_size > 0 AND alive_count >= 0 AND dead_count >= 0", name="chk_survival_counts_positive"),
        sa.CheckConstraint("(alive_count + dead_count) <= sample_size", name="chk_survival_sum_valid"),
        sa.CheckConstraint("superseded_by_id IS NULL OR superseded_by_id != id", name="chk_survival_no_self_supersede"),
    )
    # Composite foreign keys and self-referential superseding key
    op.execute(
        "ALTER TABLE survival_observations ADD CONSTRAINT fk_survival_inspection "
        "FOREIGN KEY (inspection_id, project_id) REFERENCES field_inspections(id, project_id) "
        "ON DELETE SET NULL (inspection_id);"
    )
    op.execute(
        "ALTER TABLE survival_observations ADD CONSTRAINT fk_survival_activity "
        "FOREIGN KEY (activity_id, project_id) REFERENCES field_activities(id, project_id) "
        "ON DELETE RESTRICT;"
    )
    op.execute(
        "ALTER TABLE survival_observations ADD CONSTRAINT fk_survival_superseded "
        "FOREIGN KEY (superseded_by_id) REFERENCES survival_observations(id) "
        "ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;"
    )
    # Partial unique index enforcing only 1 active observation per population unit on any date
    op.execute(
        "CREATE UNIQUE INDEX uq_active_survival_observation ON survival_observations "
        "(project_id, plot_identifier, cohort_identifier, observation_date) "
        "WHERE is_active = TRUE;"
    )
    op.create_index("idx_survival_project_plot_cohort", "survival_observations", ["project_id", "plot_identifier", "cohort_identifier", "observation_date"], unique=False)
    op.create_index("idx_survival_active", "survival_observations", ["project_id", "is_active"], unique=False)

    # 5. Alter table: evidence_files (reusing existing file storage)
    op.alter_column("evidence_files", "activity_id", existing_type=sa.Uuid(), nullable=True)
    op.alter_column("evidence_files", "revision_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("evidence_files", sa.Column("inspection_id", sa.Uuid(), nullable=True))
    op.add_column("evidence_files", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("evidence_files", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("evidence_files", sa.Column("caption", sa.String(length=255), nullable=True))
    op.create_foreign_key(
        "fk_evidence_inspection",
        "evidence_files",
        "field_inspections",
        ["inspection_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "chk_evidence_target",
        "evidence_files",
        "(activity_id IS NOT NULL AND revision_id IS NOT NULL AND inspection_id IS NULL) OR "
        "(inspection_id IS NOT NULL AND activity_id IS NULL AND revision_id IS NULL)",
    )
    op.create_index("idx_evidence_inspection", "evidence_files", ["inspection_id"], unique=False)


def downgrade() -> None:
    # 5. Revert evidence_files alterations
    op.drop_index("idx_evidence_inspection", table_name="evidence_files")
    op.drop_constraint("chk_evidence_target", "evidence_files", type_="check")
    op.drop_constraint("fk_evidence_inspection", "evidence_files", type_="foreignkey")
    op.execute("DELETE FROM evidence_files WHERE inspection_id IS NOT NULL;")
    op.drop_column("evidence_files", "caption")
    op.drop_column("evidence_files", "longitude")
    op.drop_column("evidence_files", "latitude")
    op.drop_column("evidence_files", "inspection_id")
    op.alter_column("evidence_files", "revision_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("evidence_files", "activity_id", existing_type=sa.Uuid(), nullable=False)

    # 4. Drop survival_observations
    op.drop_index("idx_survival_active", table_name="survival_observations")
    op.drop_index("idx_survival_project_plot_cohort", table_name="survival_observations")
    op.execute("DROP INDEX IF EXISTS uq_active_survival_observation;")
    op.drop_table("survival_observations")

    # 3. Drop maintenance_tasks
    op.drop_index("idx_tasks_assigned", table_name="maintenance_tasks")
    op.drop_index("idx_tasks_project_status_due", table_name="maintenance_tasks")
    op.drop_table("maintenance_tasks")

    # 2. Drop field_inspections
    op.drop_index("idx_inspections_assigned", table_name="field_inspections")
    op.drop_index("idx_inspections_project_status_date", table_name="field_inspections")
    op.drop_table("field_inspections")

    # 1. Drop uq_field_activities_id_project on field_activities
    op.drop_constraint("uq_field_activities_id_project", "field_activities", type_="unique")
