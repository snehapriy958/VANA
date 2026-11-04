# VANA Phase 6.1 — Database Schema & Migration: Completion Report

> **Document Status:** Complete & Verified  
> **Milestone:** Phase 6.1 (Field Monitoring & Follow-up Management — Database Schema & Migration)  
> **Date:** November 3, 2026  
> **Database Engine:** PostgreSQL 17.0  
> **Alembic Revision:** `0002_field_monitoring` (Revises: `0001_initial_schema`)  
> **Test Status:** 11/11 Phase 6.1 Tests Passed | 96/96 Full Backend Regression Suite Passed (100% Pass Rate)

---

## 1. Executive Summary

Phase 6.1 has successfully implemented the database schema, models, constraints, indexes, and migration for the **Field Monitoring & Follow-up Management** domain. All implementation safeguards mandated by the Phase 6 Final Pre-Implementation Gate have been physically enacted and validated:
1. **Physical Composite Foreign Keys:** Cross-project record associations are rejected at the database level.
2. **Column-Specific Deletion Actions:** PostgreSQL 17 `ON DELETE SET NULL (column_name)` guarantees that mandatory `project_id` columns can never be nullified.
3. **Restrictive Retention:** Deleting baseline planting activities and field inspections with evidence attachments is blocked under `ON DELETE RESTRICT`.
4. **Append-Only Observation Corrections:** Partial unique index `uq_active_survival_observation` enforces single active observation per population unit per date while preserving historical superseded records.
5. **Server-Side Derived Survival Rate:** Client-supplied survival rates are rejected; derived accurately on-demand without client trust.

---

## 2. Files Created and Modified

### Created Files
* [`backend/app/domains/monitoring/__init__.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/monitoring/__init__.py) — Domain module exports.
* [`backend/app/domains/monitoring/models.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/monitoring/models.py) — SQLAlchemy ORM models (`FieldInspection`, `MaintenanceTask`, `SurvivalObservation`) with composite foreign keys, checks, partial indexes, and derived survival rate.
* [`backend/alembic/versions/0002_field_monitoring.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/alembic/versions/0002_field_monitoring.py) — Symmetrical reversible Alembic migration script.
* [`backend/tests/domains/monitoring/test_monitoring_schema_and_migration.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/tests/domains/monitoring/test_monitoring_schema_and_migration.py) — 11 automated pytest tests verifying schema constraints, composite FKs, column-specific nullification, RESTRICT behavior, partial uniqueness, and evidence retention.

### Modified Files
* [`backend/app/domains/operations/models.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/operations/models.py) — Added composite unique constraint `uq_field_activities_id_project` to `FieldActivity`. Altered `EvidenceFile` to add `inspection_id` (`ON DELETE RESTRICT`), `latitude`, `longitude`, `caption`, relaxed nullability on `activity_id` and `revision_id`, and added `chk_evidence_target`.
* [`backend/app/models.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/models.py) — Registered and exported monitoring domain models and enums.
* [`backend/alembic/env.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/alembic/env.py) — Added support for `ALEMBIC_DATABASE_URL` override to permit seamless multi-database migrations (`vana_dev`, `vana_test`).

---

## 3. Migration Details & Two-Way Lifecycle Verification

### Migration Graph
```
0001_initial_schema (Base)
        │
        ▼
0002_field_monitoring (Revision: 0002_field_monitoring | Down Revision: 0001_initial_schema)
```

### Empirical Two-Way Verification Sequence (Executed on `vana_test`)
1. **Initial State Verification:**
   * Executed: `SELECT version_num FROM alembic_version;`
   * Result: `0002_field_monitoring`
2. **Downgrade Phase (`alembic downgrade -1`):**
   * Executed: `$env:ALEMBIC_DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:15432/vana_test"; alembic -c alembic.ini downgrade -1`
   * Output: `Running downgrade 0002_field_monitoring -> 0001_initial_schema, field_monitoring`
   * Table Count: Dropped from 12 tables to exactly 9 (8 domain tables + `alembic_version`).
   * Monitoring Tables: `field_inspections`, `maintenance_tasks`, and `survival_observations` completely dropped.
   * `evidence_files`: Columns `inspection_id`, `latitude`, `longitude`, `caption` removed; `activity_id` and `revision_id` restored to `NOT NULL`; `chk_evidence_target` removed; `chk_evidence_file_size_positive` preserved intact.
   * `field_activities`: Composite unique constraint `uq_field_activities_id_project` removed cleanly.
   * Revision confirmed: `0001_initial_schema`.
3. **Upgrade Phase (`alembic upgrade head`):**
   * Executed: `$env:ALEMBIC_DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:15432/vana_test"; alembic -c alembic.ini upgrade head`
   * Output: `Running upgrade 0001_initial_schema -> 0002_field_monitoring, field_monitoring`
   * Restored: All 3 monitoring tables, composite foreign keys with column-specific `ON DELETE SET NULL`, `ON DELETE RESTRICT` constraints, partial unique index `uq_active_survival_observation`, and polymorphic evidence constraints.
   * Revision confirmed: `0002_field_monitoring`.
4. **Environment Isolation Protection:**
   * `vana_dev` and production databases were strictly excluded from downgrade actions.
   * Verified `vana_dev` remained intact at `0002_field_monitoring`.

---

## 4. Test Isolation & Timeout Hardening

1. **Alembic Configuration Resolution (`backend/alembic/env.py`):**
   * Hardened URL resolution logic so that `config.get_main_option("sqlalchemy.url")` (set by tests) is never accidentally clobbered by `settings.DATABASE_URL`.
   * CLI overrides via `ALEMBIC_DATABASE_URL` take precedence when supplied.
2. **Fixture Isolation & Environment Restoration (`backend/tests/conftest.py`):**
   * The `setup_test_database` session fixture saves any pre-existing `ALEMBIC_DATABASE_URL` value and restores/unsets it in a `finally` block when the test session completes.
3. **Async Engine Timeouts:**
   * Configured `connect_args={"timeout": 10, "command_timeout": 30}` on `test_engine` in `conftest.py` to ensure fast-failure and prevent socket-level hangs.

---

## 4. Database Constraints & Indexes Verified

| Table | Constraint / Index Name | Type | Specification / Guard |
| :--- | :--- | :---: | :--- |
| `field_activities` | `uq_field_activities_id_project` | Unique | `UNIQUE (id, project_id)` — Anchor for composite foreign keys |
| `field_inspections` | `uq_inspections_id_project` | Unique | `UNIQUE (id, project_id)` |
| `field_inspections` | `fk_inspections_linked_activity` | Composite FK | `(linked_activity_id, project_id) REFERENCES field_activities(id, project_id) ON DELETE SET NULL (linked_activity_id)` |
| `field_inspections` | `chk_inspection_status` | Check | `status IN ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')` |
| `field_inspections` | `chk_inspection_type` | Check | `inspection_type IN ('ROUTINE', 'SURVIVAL_CHECK', 'MAINTENANCE_AUDIT', 'EMERGENCY')` |
| `field_inspections` | `chk_vegetation_health_score` | Check | `vegetation_health_score IS NULL OR (score >= 1 AND score <= 5)` |
| `field_inspections` | `chk_canopy_condition` | Check | `canopy_condition IS NULL OR canopy_condition IN ('EXCELLENT', 'HEALTHY', 'STRESSED', 'CRITICAL')` |
| `field_inspections` | `chk_soil_moisture` | Check | `soil_moisture_condition IS NULL OR soil_moisture_condition IN ('SATURATED', 'ADEQUATE', 'DRY', 'SEVERELY_PARCHED')` |
| `field_inspections` | `idx_inspections_project_status_date` | B-Tree Index | `(project_id, status, scheduled_date)` |
| `field_inspections` | `idx_inspections_assigned` | B-Tree Index | `(assigned_to_id, status)` |
| `maintenance_tasks` | `uq_tasks_id_project` | Unique | `UNIQUE (id, project_id)` |
| `maintenance_tasks` | `fk_tasks_inspection` | Composite FK | `(inspection_id, project_id) REFERENCES field_inspections(id, project_id) ON DELETE SET NULL (inspection_id)` |
| `maintenance_tasks` | `fk_tasks_activity` | Composite FK | `(activity_id, project_id) REFERENCES field_activities(id, project_id) ON DELETE SET NULL (activity_id)` |
| `maintenance_tasks` | `chk_task_category` | Check | 8 approved operational categories |
| `maintenance_tasks` | `chk_task_priority` | Check | `priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')` |
| `maintenance_tasks` | `chk_task_status` | Check | `status IN ('TODO', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')` |
| `maintenance_tasks` | `idx_tasks_project_status_due` | B-Tree Index | `(project_id, status, due_date)` |
| `survival_observations` | `uq_survival_obs_id_project` | Unique | `UNIQUE (id, project_id)` |
| `survival_observations` | `fk_survival_inspection` | Composite FK | `(inspection_id, project_id) REFERENCES field_inspections(id, project_id) ON DELETE SET NULL (inspection_id)` |
| `survival_observations` | `fk_survival_activity` | Composite FK | `(activity_id, project_id) REFERENCES field_activities(id, project_id) ON DELETE RESTRICT` |
| `survival_observations` | `fk_survival_superseded` | Foreign Key | `(superseded_by_id) REFERENCES survival_observations(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED` |
| `survival_observations` | `chk_survival_methodology` | Check | `methodology IN ('SAMPLE_PLOT', 'TRANSECT', 'FULL_CENSUS')` |
| `survival_observations` | `chk_survival_counts_positive` | Check | `sample_size > 0 AND alive_count >= 0 AND dead_count >= 0` |
| `survival_observations` | `chk_survival_sum_valid` | Check | `(alive_count + dead_count) <= sample_size` |
| `survival_observations` | `chk_survival_no_self_supersede` | Check | `superseded_by_id IS NULL OR superseded_by_id != id` |
| `survival_observations` | `uq_active_survival_observation` | Partial Unique Index | `UNIQUE (project_id, plot_identifier, cohort_identifier, observation_date) WHERE is_active = TRUE` |
| `survival_observations` | `idx_survival_project_plot_cohort`| B-Tree Index | `(project_id, plot_identifier, cohort_identifier, observation_date)` |
| `survival_observations` | `idx_survival_active` | B-Tree Index | `(project_id, is_active)` |
| `evidence_files` | `fk_evidence_inspection` | Foreign Key | `(inspection_id) REFERENCES field_inspections(id) ON DELETE RESTRICT` |
| `evidence_files` | `chk_evidence_target` | Check | Mutual exclusivity: `(activity_id, revision_id) XOR (inspection_id)` |
| `evidence_files` | `idx_evidence_inspection` | B-Tree Index | `(inspection_id)` |

---

## 5. Automated Test Results

### Phase 6.1 Dedicated Test Suite
File: [`backend/tests/domains/monitoring/test_monitoring_schema_and_migration.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/tests/domains/monitoring/test_monitoring_schema_and_migration.py)
* `test_schema_constraints_and_indexes` $\longrightarrow$ **PASSED**
* `test_composite_fk_inspection_activity_cross_project` $\longrightarrow$ **PASSED** (Rejects cross-project activity link)
* `test_composite_fk_task_inspection_cross_project` $\longrightarrow$ **PASSED** (Rejects cross-project inspection link)
* `test_composite_fk_survival_activity_cross_project` $\longrightarrow$ **PASSED** (Rejects cross-project activity link)
* `test_column_specific_set_null_behavior` $\longrightarrow$ **PASSED** (Sets only reference column to NULL; preserves `project_id`)
* `test_restrict_baseline_activity` $\longrightarrow$ **PASSED** (Prevents deleting baseline planting activity)
* `test_restrict_inspection_with_evidence` $\longrightarrow$ **PASSED** (Prevents deleting inspection with photos)
* `test_partial_unique_index_rejects_active_duplicate` $\longrightarrow$ **PASSED** (Blocks concurrent active observation duplicates)
* `test_observation_supersession_workflow` $\longrightarrow$ **PASSED** (Preserves inactive history, creates active replacement, sets supersession FK)
* `test_survival_rate_derived_property` $\longrightarrow$ **PASSED** (Derives 87.50% on sample, returns None on zero assessed population)
* `test_evidence_target_mutual_exclusion` $\longrightarrow$ **PASSED** (Enforces valid target discriminator in `evidence_files`)

**Result:** 11 passed in 0.84s (100% pass rate).

### Full Backend Regression Test Suite
Executed command: `pytest -v` across all test modules.
* Monitoring Schema & Migration: 11 tests passed
* Auth, RBAC & Token Lifecycle: 33 tests passed
* Dashboard & Environmental Ledger: 7 tests passed
* Operations, Evidence & Verification: 18 tests passed
* Projects, Assignments & Targets: 18 tests passed
* Models & Integrity Constraints: 5 tests passed
* Database & E2E Production Acceptance: 4 tests passed

**Total Backend Test Count:** **96 passed in 41.80s (100% pass rate)**. Zero regressions.

---

## 6. Protection of Existing Functionality & Invariants

1. **Environmental Ledger Invariant (Rule 7):** Zero changes made to `ActivityRevision`, `EnvironmentalLedgerService`, or ledger aggregation math. Verified achievement calculations remain 100% verified-only.
2. **Anti-Self-Verification Gate (Rule 5):** Verification state machine and authorization rules remain completely untouched and verified by passing regression tests.
3. **Audit Trail Integrity (Rule 6):** Append-only audit history preserved; `ON DELETE RESTRICT` protects evidence and baseline activities from deletion.
4. **Existing Evidence Records:** All existing rows in `evidence_files` continue satisfying `chk_evidence_target` with `inspection_id = NULL`. Zero metadata or file loss.

---

## 7. Scope Boundary & Sign-off

Phase 6.1 deliverables are complete, verified, and locked. No API routes, domain services, or frontend components have been implemented yet. All work for Phase 6.2 remains awaiting user authorization.
