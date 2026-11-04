# VANA Phase 6 — Field Monitoring & Follow-up Management: Database Schema & Migration Design

> **Document Status:** Final Gate Approved with Database Integrity Corrections  
> **Target Release:** VANA Phase 6 (Milestone 6)  
> **Migration ID:** `0002_field_monitoring`  
> **Down Revision:** `0001_initial_schema` (Empirically verified on live database)  
> **Database Engine:** PostgreSQL 17.0  
> **Traceability:** Aligns with `AGENTS.md` (Rules 1, 2, 3, 6, 7, 8, 9), `docs/PHASE_6_FINAL_IMPLEMENTATION_GATE.md`.

---

## 1. Migration History & Verified Parity

Direct verification executed on PostgreSQL instances (port 15432):
* `vana_dev`: `SELECT version_num FROM alembic_version;` $\longrightarrow$ `0001_initial_schema`
* `vana_test`: `SELECT version_num FROM alembic_version;` $\longrightarrow$ `0001_initial_schema`

The migration `0002_field_monitoring.py` is configured with:
* `revision = "0002_field_monitoring"`
* `down_revision = "0001_initial_schema"`

---

## 2. Table Specifications & Database Constraints

### 2.1 Table: `field_activities` (Alteration for Composite Foreign Keys)
Adds composite unique constraint to allow composite foreign key references from child monitoring entities:
```sql
ALTER TABLE field_activities ADD CONSTRAINT uq_field_activities_id_project UNIQUE (id, project_id);
```

### 2.2 Table: `field_inspections`
```sql
CREATE TABLE field_inspections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    linked_activity_id UUID NULL,
    scheduled_date DATE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'SCHEDULED',
    inspection_type VARCHAR(32) NOT NULL DEFAULT 'ROUTINE',
    assigned_to_id UUID REFERENCES users(id) ON DELETE SET NULL,
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    findings TEXT NULL,
    vegetation_health_score INTEGER NULL,
    canopy_condition VARCHAR(32) NULL,
    soil_moisture_condition VARCHAR(32) NULL,
    threats_detected JSONB NULL DEFAULT '[]'::jsonb,
    addenda JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inspections_id_project UNIQUE (id, project_id),
    CONSTRAINT fk_inspections_linked_activity FOREIGN KEY (linked_activity_id, project_id)
        REFERENCES field_activities(id, project_id) ON DELETE SET NULL (linked_activity_id),
    CONSTRAINT chk_inspection_status CHECK (status IN ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    CONSTRAINT chk_inspection_type CHECK (inspection_type IN ('ROUTINE', 'SURVIVAL_CHECK', 'MAINTENANCE_AUDIT', 'EMERGENCY')),
    CONSTRAINT chk_vegetation_health_score CHECK (vegetation_health_score IS NULL OR (vegetation_health_score >= 1 AND vegetation_health_score <= 5)),
    CONSTRAINT chk_canopy_condition CHECK (canopy_condition IS NULL OR canopy_condition IN ('EXCELLENT', 'HEALTHY', 'STRESSED', 'CRITICAL')),
    CONSTRAINT chk_soil_moisture CHECK (soil_moisture_condition IS NULL OR soil_moisture_condition IN ('SATURATED', 'ADEQUATE', 'DRY', 'SEVERELY_PARCHED'))
);

CREATE INDEX idx_inspections_project_status_date ON field_inspections (project_id, status, scheduled_date);
CREATE INDEX idx_inspections_assigned ON field_inspections (assigned_to_id, status);
```

### 2.3 Table: `maintenance_tasks`
```sql
CREATE TABLE maintenance_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    inspection_id UUID NULL,
    activity_id UUID NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    category VARCHAR(32) NOT NULL,
    priority VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(32) NOT NULL DEFAULT 'TODO',
    due_date DATE NOT NULL,
    assigned_to_id UUID REFERENCES users(id) ON DELETE SET NULL,
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    completion_notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tasks_id_project UNIQUE (id, project_id),
    CONSTRAINT fk_tasks_inspection FOREIGN KEY (inspection_id, project_id)
        REFERENCES field_inspections(id, project_id) ON DELETE SET NULL (inspection_id),
    CONSTRAINT fk_tasks_activity FOREIGN KEY (activity_id, project_id)
        REFERENCES field_activities(id, project_id) ON DELETE SET NULL (activity_id),
    CONSTRAINT chk_task_category CHECK (category IN ('IRRIGATION', 'WEEDING', 'MULCHING', 'FENCING_REPAIR', 'REPLANTING_PREP', 'PEST_CONTROL', 'SOIL_ENRICHMENT', 'OTHER')),
    CONSTRAINT chk_task_priority CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')),
    CONSTRAINT chk_task_status CHECK (status IN ('TODO', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'))
);

CREATE INDEX idx_tasks_project_status_due ON maintenance_tasks (project_id, status, due_date);
CREATE INDEX idx_tasks_assigned ON maintenance_tasks (assigned_to_id, status);
```

### 2.4 Table: `survival_observations`
Stores empirical ground-truth counts. `survival_rate` is derived on query to maintain normalization and avoid client trust. Includes partial unique index for append-only corrections.
```sql
CREATE TABLE survival_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    activity_id UUID NULL,
    inspection_id UUID NULL,
    plot_identifier VARCHAR(64) NOT NULL,
    cohort_identifier VARCHAR(64) NOT NULL,
    methodology VARCHAR(32) NOT NULL DEFAULT 'SAMPLE_PLOT',
    coverage_area_sqm FLOAT NULL,
    observation_date DATE NOT NULL,
    sample_size INTEGER NOT NULL,
    alive_count INTEGER NOT NULL,
    dead_count INTEGER NOT NULL,
    mortality_causes JSONB NULL DEFAULT '[]'::jsonb,
    is_definitive BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    superseded_by_id UUID NULL,
    correction_notes TEXT NULL,
    notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_survival_obs_id_project UNIQUE (id, project_id),
    CONSTRAINT fk_survival_inspection FOREIGN KEY (inspection_id, project_id)
        REFERENCES field_inspections(id, project_id) ON DELETE SET NULL (inspection_id),
    CONSTRAINT fk_survival_activity FOREIGN KEY (activity_id, project_id)
        REFERENCES field_activities(id, project_id) ON DELETE RESTRICT,
    CONSTRAINT fk_survival_superseded FOREIGN KEY (superseded_by_id)
        REFERENCES survival_observations(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT chk_survival_methodology CHECK (methodology IN ('SAMPLE_PLOT', 'TRANSECT', 'FULL_CENSUS')),
    CONSTRAINT chk_survival_counts_positive CHECK (sample_size > 0 AND alive_count >= 0 AND dead_count >= 0),
    CONSTRAINT chk_survival_sum_valid CHECK ((alive_count + dead_count) <= sample_size),
    CONSTRAINT chk_survival_no_self_supersede CHECK (superseded_by_id IS NULL OR superseded_by_id != id)
);

-- Partial Unique Index: allows historical corrections while ensuring only 1 active observation per cohort/plot/date
CREATE UNIQUE INDEX uq_active_survival_observation ON survival_observations (
    project_id,
    plot_identifier,
    cohort_identifier,
    observation_date
) WHERE is_active = TRUE;

CREATE INDEX idx_survival_project_plot_cohort ON survival_observations (project_id, plot_identifier, cohort_identifier, observation_date);
CREATE INDEX idx_survival_active ON survival_observations (project_id, is_active);
```

### 2.5 Table: `evidence_files` (Alteration)
```sql
ALTER TABLE evidence_files ALTER COLUMN activity_id DROP NOT NULL;
ALTER TABLE evidence_files ALTER COLUMN revision_id DROP NOT NULL;
ALTER TABLE evidence_files ADD COLUMN inspection_id UUID REFERENCES field_inspections(id) ON DELETE RESTRICT;
ALTER TABLE evidence_files ADD COLUMN latitude FLOAT NULL;
ALTER TABLE evidence_files ADD COLUMN longitude FLOAT NULL;
ALTER TABLE evidence_files ADD COLUMN caption VARCHAR(255) NULL;

ALTER TABLE evidence_files ADD CONSTRAINT chk_evidence_target CHECK (
    (activity_id IS NOT NULL AND revision_id IS NOT NULL AND inspection_id IS NULL)
    OR
    (inspection_id IS NOT NULL AND activity_id IS NULL AND revision_id IS NULL)
);

CREATE INDEX idx_evidence_inspection ON evidence_files (inspection_id);
```

---

## 3. Reversible Migration Plan (`0002_field_monitoring.py`)

### `upgrade()` Execution Sequence
1. Add constraint `uq_field_activities_id_project` on `field_activities`.
2. Create table `field_inspections` with column-specific `ON DELETE SET NULL (linked_activity_id)`.
3. Create table `maintenance_tasks` with column-specific `ON DELETE SET NULL (inspection_id)` and `(activity_id)`.
4. Create table `survival_observations` with `ON DELETE SET NULL (inspection_id)`, `ON DELETE RESTRICT` for baseline activity, and `DEFERRABLE INITIALLY DEFERRED` self-referential `superseded_by_id`.
5. Create partial unique index `uq_active_survival_observation` on `survival_observations WHERE is_active = TRUE`.
6. Alter `evidence_files` adding `inspection_id` with `ON DELETE RESTRICT`, coordinates, caption, and target check constraint.

### `downgrade()` Execution Sequence
1. Drop check constraint `chk_evidence_target` and index `idx_evidence_inspection` on `evidence_files`.
2. Delete rows in `evidence_files` where `inspection_id IS NOT NULL`.
3. Drop columns `inspection_id`, `latitude`, `longitude`, `caption` on `evidence_files`.
4. Restore `NOT NULL` on `activity_id` and `revision_id` on `evidence_files`.
5. Drop partial index `uq_active_survival_observation` and table `survival_observations`.
6. Drop table `maintenance_tasks`.
7. Drop table `field_inspections`.
8. Drop `uq_field_activities_id_project` on `field_activities`.
