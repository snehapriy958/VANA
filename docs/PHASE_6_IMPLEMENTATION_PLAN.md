# VANA Phase 6 — Field Monitoring & Follow-up Management: Implementation Plan

> **Document Status:** Final Gate Approved\
> **Target Release:** VANA Phase 6 (Milestone 6)\
> **Traceability:** Aligns with `AGENTS.md` (Rules 1, 4, 6, 7, 8, 9, 11), `docs/PHASE_6_FINAL_IMPLEMENTATION_GATE.md`.

---

## 1. Execution Strategy & Architecture Invariants

Implementation follows a strict milestone discipline:
$$\text{Database Schema} \longrightarrow \text{Domain Service} \longrightarrow \text{API Routers} \longrightarrow \text{Frontend Services} \longrightarrow \text{Frontend Views} \longrightarrow \text{Verification}$$

* **Rule 1 (Modular Monolith):** Code placed strictly in `backend/app/domains/monitoring` and `frontend/src/views/projects`.
* **Rule 6 (Evidence Retention):** `ON DELETE RESTRICT` on evidence files; append-only survival corrections.
* **Rule 7 (Ledger Invariant):** Monitoring observations never modify `activity_revisions.quantity` or `is_active_ledger_entry`.
* **Rule 9 (Scientific Grounding):** Survival rate strictly $A / (A + D) \times 100$ when $(A + D) > 0$. No arbitrary thresholds.
* **Rule 11 (Discipline):** One sub-phase at a time with passing automated tests before proceeding.

---

## 2. Phase-by-Phase Implementation Roadmap

### Phase 6.1: Database Schema & Migration
* **Scope:**
  * Define SQLAlchemy ORM models in `backend/app/domains/monitoring/models.py`:
    * `FieldInspection`: with composite FK to `field_activities`, `addenda` JSONB, status check, score check.
    * `MaintenanceTask`: with composite FKs to `field_inspections` and `field_activities`, priority and category checks.
    * `SurvivalObservation`: with composite FKs, `superseded_by_id`, `is_active`, `plot_identifier`, `cohort_identifier`, counts checks, unique constraint `(project_id, plot_identifier, cohort_identifier, observation_date)`.
  * Update `backend/app/domains/operations/models.py`:
    * Alter `EvidenceFile` to add `inspection_id` (`ON DELETE RESTRICT`), `latitude`, `longitude`, `caption`.
  * Create Alembic migration `backend/alembic/versions/0002_field_monitoring.py`:
    * `revision = "0002_field_monitoring"`
    * `down_revision = "0001_initial_schema"`
    * Symmetrical `upgrade()` and `downgrade()` logic.
  * Register new models in `backend/app/models.py`.
  * Execute migration against `vana_dev` and verify database schema.

### Phase 6.2: Core Domain Logic & Monitoring Service
* **Scope:**
  * Define Pydantic v2 schemas in `backend/app/domains/monitoring/schemas.py`:
    * Inspection creation, completion, addenda, and response schemas.
    * Task creation, completion, reopen, and response schemas.
    * Survival observation creation, correction, and trajectory response schemas.
    * Alert item and dashboard summary schemas.
  * Implement `MonitoringService` in `backend/app/domains/monitoring/service.py`:
    * Inspector assignment validation against `project_assignments`.
    * Cross-project reference validation against `field_activities` and `field_inspections`.
    * State machine methods (`start_inspection`, `complete_inspection`, `cancel_inspection`, `add_inspection_addendum`, `start_task`, `complete_task`, `cancel_task`, `reopen_task`).
    * Evidence upload with `LocalStorageService` and SHA-256 deduplication.
    * Mathematical calculation: $\text{observed\_sample\_survival\_rate} = A / (A + D) \times 100$ when $(A + D) > 0$, else `None`.
    * Longitudinal trajectory filtering by 3-tuple `(project_id, plot_identifier, cohort_identifier)`.
    * Observation correction method creating superseding row and updating `superseded_by_id`.
    * Dynamic SQL alert queries (overdue inspections, upcoming inspections, overdue tasks).
    * Immutable audit trail logging via `record_audit_log`.
  * Write unit tests in `backend/tests/domains/monitoring/test_monitoring_service.py`.

### Phase 6.3: API Endpoints & RBAC Security
* **Scope:**
  * Implement FastAPI router in `backend/app/domains/monitoring/router.py`:
    * Explicit transition routes rather than unrestricted PATCH.
    * Route dependencies: `get_current_active_user`, `verify_project_access`, `require_roles`.
    * Field Officer ownership validation.
  * Register router in `backend/app/main.py` under `/api/v1/monitoring`.
  * Write API integration tests in `backend/tests/domains/monitoring/test_monitoring_api.py` and `test_cross_project_integrity.py`:
    * Admin full access.
    * Project Manager scoped access.
    * Field Officer own-assignment access vs cross-officer 403.
    * Cross-project reference 400 rejection (composite FK integration).
    * Unauthenticated 401 rejection.

### Phase 6.4: Frontend Types, API Client & State Hooks
* **Scope:**
  * Define TypeScript interfaces in `frontend/src/types/monitoring.ts`:
    * `FieldInspection`, `MaintenanceTask`, `SurvivalObservation`, `MonitoringAlert`, `MonitoringDashboardKpis`.
  * Implement API service in `frontend/src/services/monitoringService.ts`.
  * Implement React hooks using TanStack Query:
    * `useProjectInspections`, `useProjectTasks`, `useSurvivalAnalytics`, `useProjectAlerts`, `useMonitoringDashboard`.

### Phase 6.5: Frontend UI Views & Modals
* **Scope:**
  * Add `Monitoring` tab to `ProjectWorkspaceView.tsx`:
    * Component: `frontend/src/views/projects/MonitoringWorkspaceTab.tsx`.
  * Inspection Section: Table/cards for inspections, `InspectionSchedulerModal`, `InspectionCompletionModal`, `InspectionAddendumModal`.
  * Maintenance Task Board: Status-filtered list (`TODO`, `IN_PROGRESS`, `COMPLETED`), `TaskCreateModal`, `TaskCompleteModal`.
  * Survival Trajectory Section: `SurvivalObservationModal`, `SurvivalCorrectionModal`, Recharts line chart filtered by plot and cohort, displaying sample size and assessed count.
  * Alerts Banner: Overdue inspections, upcoming inspections, overdue tasks.
  * Design Token Compliance: Forest Green (`#183D32`), Warm Ivory (`#F5F3EA`), Sage (`#A8B99B`), Earth Gold (`#D6A76A`), Charcoal (`#29332F`).

### Phase 6.6: End-to-End Verification & Documentation
* **Scope:**
  * Complete test suite execution (`pytest`, `vitest`).
  * Browser acceptance testing of monitoring flows.
  * Update `IMPLEMENTATION_STATUS.md` and `DECISION_LOG.md`.
