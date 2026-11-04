# VANA Phase 6.2 — Monitoring Domain Logic: Completion Report

> **Document Status:** Complete & Verified\
> **Milestone:** Phase 6.2 (Field Monitoring & Follow-up Management — Domain Logic & Services)\
> **Date:** November 4, 2026\
> **Backend Test Results:** 112/112 Tests Passed (100% Pass Rate in 47.33s)\
> **Frontend Test Results:** 32/32 Tests Passed (100% Pass Rate in 0.22s)\
> **Sign-Off:** Ready for User Review\

---

## 1. Executive Summary

Phase 6.2 implements the complete core domain services and business logic for **Field Monitoring & Follow-up Management** atop the verified Phase 6.1 relational schema.

All mandated business rules, deterministic state transitions, server-side derived survival mathematics, atomic observation supersession workflows, dynamic database alert evaluations, and immutable audit logs are fully implemented and verified with zero schema modifications, zero external background queues, and zero impact on the existing environmental ledger or verification systems.

---

## 2. Files Created and Modified

### Created Files
1. [`backend/app/domains/monitoring/schemas.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/monitoring/schemas.py)
   * Pydantic v2 validation models for inspections, tasks, survival observations, and dynamic alerts.
   * Rejects client-supplied `survival_rate`; enforces $(alive\_count + dead\_count) \le sample\_size$.
2. [`backend/app/domains/monitoring/services.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/monitoring/services.py)
   * Core domain services: `MonitoringAuthorizationService`, `InspectionService`, `MaintenanceTaskService`, `SurvivalObservationService`, `AlertService`.
3. [`backend/tests/domains/monitoring/test_monitoring_domain_services.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/tests/domains/monitoring/test_monitoring_domain_services.py)
   * 16 comprehensive automated pytest integration tests verifying all lifecycles, cross-project rejections, ownership checks, atomic supersession, and dynamic alert queries.
4. [`docs/PHASE_6_2_COMPLETION_REPORT.md`](file:///c:/Developers/Sneha/Projects/VANA/docs/PHASE_6_2_COMPLETION_REPORT.md)
   * Comprehensive completion documentation.

### Modified Files
1. [`backend/app/domains/monitoring/__init__.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/monitoring/__init__.py)
   * Exported domain services, models, enums, and request/response schemas.

---

## 3. Service Methods Implemented

### 3.1 `MonitoringAuthorizationService`
* `verify_project_access(db, user, project_id, allowed_roles=None)`:
  * Server-side project boundary enforcement.
  * `ADMIN`: Organization-wide access.
  * `PROJECT_MANAGER` & `FIELD_OFFICER`: Enforces active `ProjectAssignment` membership; rejects unauthorized project access with `HTTP 403 FORBIDDEN`.
* `get_scoped_project_ids(db, user, requested_project_id=None)`:
  * Resolves authorized project ID filters for multi-tenant query scoping.

### 3.2 `InspectionService`
* `schedule_inspection(db, user, data)`:
  * Restricts scheduling to `ADMIN` and assigned `PROJECT_MANAGER` (`FIELD_OFFICER` denied with `403`).
  * Validates inspector has active project assignment (`400` if unassigned).
  * Validates linked activity belongs to the same project (`400` if cross-project).
  * Records `INSPECTION_SCHEDULED` audit event.
* `get_inspection(db, user, inspection_id)`:
  * Validates project membership before returning inspection details.
* `list_inspections(db, user, project_id, status_filter, assigned_to_id, from_date, to_date)`:
  * Multi-tenant scoped query filtering by status, assignee, and date ranges.
* `start_inspection(db, user, inspection_id, notes)`:
  * Transitions inspection from `SCHEDULED` $\to$ `IN_PROGRESS` with pessimistic lock (`with_for_update()`).
  * Field Officer ownership check: Field Officers can only start inspections assigned to them (`403` if assigned to another officer).
  * Rejects invalid status transitions (`400`).
  * Records `INSPECTION_STARTED` audit event.
* `complete_inspection(db, user, inspection_id, data)`:
  * Transitions inspection from `IN_PROGRESS` $\to$ `COMPLETED`.
  * Field Officer ownership check enforced.
  * Requires mandatory non-empty findings and health score validation ($1 \le score \le 5$).
  * Locks completed inspections against subsequent edits (`COMPLETED_INSPECTION_LOCKED`).
  * Records `INSPECTION_COMPLETED` audit event.
* `cancel_inspection(db, user, inspection_id, data)`:
  * Cancels inspection from `SCHEDULED` or `IN_PROGRESS` with mandatory cancellation reason.
  * Restricted to `ADMIN` and assigned `PROJECT_MANAGER` (`FIELD_OFFICER` denied with `403`).
  * Completed inspections cannot be cancelled.
  * Records `INSPECTION_CANCELLED` audit event.
* `add_addendum(db, user, inspection_id, data)`:
  * Records immutable correction addenda on `COMPLETED` inspections without mutating original findings.
  * Restricted to `ADMIN` and assigned `PROJECT_MANAGER` (`FIELD_OFFICER` denied with `403`).
  * Records `INSPECTION_ADDENDUM_RECORDED` audit event.

### 3.3 `MaintenanceTaskService`
* `create_task(db, user, data)`:
  * Restricts task creation to `ADMIN` and assigned `PROJECT_MANAGER` (`FIELD_OFFICER` denied with `403`).
  * Validates assignee belongs to project (`400` if unassigned).
  * Validates linked inspection and activity belong to target project (`400` on cross-project links).
  * Records `TASK_CREATED` audit event.
* `get_task(db, user, task_id)`:
  * Scoped retrieval with project authorization check.
* `list_tasks(db, user, project_id, status_filter, assigned_to_id, priority_filter, category_filter)`:
  * Multi-tenant scoped listing ordered by `due_date ASC`.
* `start_task(db, user, task_id, notes)`:
  * Transitions task from `TODO` $\to$ `IN_PROGRESS`.
  * Field Officer ownership check: Field Officers can only start their own assigned tasks.
  * Records `TASK_STARTED` audit event.
* `complete_task(db, user, task_id, data)`:
  * Transitions task to `COMPLETED` with mandatory completion notes.
  * Field Officer ownership check enforced.
  * Records `TASK_COMPLETED` audit event.
* `cancel_task(db, user, task_id, data)`:
  * Cancels task with mandatory cancellation reason (`ADMIN`/`PM` only).
  * Records `TASK_CANCELLED` audit event.
* `reopen_task(db, user, task_id, data)`:
  * Reopens `COMPLETED` task back to `TODO` with mandatory justification note (`ADMIN`/`PM` only).
  * Records `TASK_REOPENED` audit event.

### 3.4 `SurvivalObservationService`
* `create_observation(db, user, data)`:
  * Permitted for `ADMIN`, assigned `PM`, and assigned `FIELD_OFFICER`.
  * Validates $(alive\_count + dead\_count) \le sample\_size$.
  * Validates cross-project activity and inspection references.
  * Rejects duplicate active observations for $(project\_id, plot, cohort, date)$ with `HTTP 409 CONFLICT`.
  * Rejects client-supplied `survival_rate`; calculates dynamically on-demand:
    $$\text{survival\_rate} = \frac{A}{A + D} \times 100 \quad (\text{if } A + D > 0 \text{ else None})$$
  * Records `SURVIVAL_OBSERVATION_CREATED` audit event.
* `get_observation(db, user, observation_id)`:
  * Scoped retrieval with project validation.
* `get_observation_history(db, user, project_id, plot, cohort, active_only=False)`:
  * Preserves historical superseded rows when `active_only=False`.
* `correct_observation(db, user, observation_id, replacement_data)`:
  * Atomic supersession restricted to `ADMIN` and assigned `PROJECT_MANAGER` (`FIELD_OFFICER` denied with `403`).
  * Pessimistically locks the original observation row (`with_for_update()`).
  * Verifies original is active (`400 OBSERVATION_ALREADY_SUPERSEDED` if inactive).
  * Deactivates original (`is_active = False`) and records `correction_notes`.
  * Creates replacement observation (`is_active = True`) with identical $(project, plot, cohort, date)$ identity.
  * Links original `superseded_by_id = replacement.id` (acyclic).
  * Records `SURVIVAL_OBSERVATION_SUPERSEDED` and `SURVIVAL_OBSERVATION_CORRECTION_CREATED` audit events.
* `get_survival_trajectory(db, user, project_id, plot, cohort)`:
  * Chronological trajectory of active observations with derived rate, assessed count, and unassessed breakdown.

### 3.5 `AlertService`
* `evaluate_alerts(db, user, project_id=None)`:
  * Pure database-backed SQL dynamic queries evaluating:
    1. `OVERDUE_INSPECTION`: `status = 'SCHEDULED' AND scheduled_date < CURRENT_DATE` (Severity: `HIGH`).
    2. `UPCOMING_INSPECTION`: `status = 'SCHEDULED' AND scheduled_date BETWEEN CURRENT_DATE AND (CURRENT_DATE + 7 days)` (Severity: `MEDIUM`).
    3. `OVERDUE_TASK`: `status IN ('TODO', 'IN_PROGRESS') AND due_date < CURRENT_DATE` (Severity: `HIGH` for HIGH/URGENT priority, `MEDIUM` otherwise).
  * Excludes completed or cancelled items.
  * Scoped strictly to projects the user is authorized to view.
* `get_alert_summary(db, user, project_id=None)`:
  * Aggregates total alert count, high count, medium count, and low count.

---

## 4. Security & RBAC Enforcement Summary

| Action | `ADMIN` | `PROJECT_MANAGER` | `FIELD_OFFICER` | Policy Enforcement Rule |
| :--- | :---: | :---: | :---: | :--- |
| **Schedule Inspection** | Allowed | Allowed (Assigned) | Denied (`403`) | Inspector must be assigned to project |
| **Start Inspection** | Allowed | Allowed (Assigned) | Allowed (Owner Only) | Field Officer must be `assigned_to_id` |
| **Complete Inspection** | Allowed | Allowed (Assigned) | Allowed (Owner Only) | Mandatory findings; locks inspection |
| **Cancel Inspection** | Allowed | Allowed (Assigned) | Denied (`403`) | Mandatory cancellation reason |
| **Record Addendum** | Allowed | Allowed (Assigned) | Denied (`403`) | On `COMPLETED` inspections only |
| **Create Task** | Allowed | Allowed (Assigned) | Denied (`403`) | Assignee must belong to project |
| **Start Task** | Allowed | Allowed (Assigned) | Allowed (Owner Only) | Field Officer must be `assigned_to_id` |
| **Complete Task** | Allowed | Allowed (Assigned) | Allowed (Owner Only) | Mandatory completion notes |
| **Cancel Task** | Allowed | Allowed (Assigned) | Denied (`403`) | Mandatory cancellation reason |
| **Reopen Task** | Allowed | Allowed (Assigned) | Denied (`403`) | On `COMPLETED` tasks with justification |
| **Record Survival Obs** | Allowed | Allowed (Assigned) | Allowed (Assigned) | $(A + D) \le sample\_size$; client rate ignored |
| **Correct Survival Obs** | Allowed | Allowed (Assigned) | Denied (`403`) | Atomic supersession with row locking |
| **View Alerts & Dashboards** | Allowed | Allowed (Assigned) | Allowed (Assigned) | Filtered strictly by assigned projects |

---

## 5. Automated Testing Results

### Phase 6.2 Monitoring Domain Services Test Suite
File: [`backend/tests/domains/monitoring/test_monitoring_domain_services.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/tests/domains/monitoring/test_monitoring_domain_services.py)
* `test_schedule_inspection_success_and_audit` $\longrightarrow$ **PASSED**
* `test_schedule_inspection_rbac_field_officer_denied` $\longrightarrow$ **PASSED**
* `test_schedule_inspection_unassigned_inspector_rejected` $\longrightarrow$ **PASSED**
* `test_schedule_inspection_cross_project_activity_rejected` $\longrightarrow$ **PASSED**
* `test_inspection_lifecycle_and_ownership` $\longrightarrow$ **PASSED**
* `test_inspection_cancellation_and_addendum` $\longrightarrow$ **PASSED**
* `test_maintenance_task_lifecycle_and_reopen` $\longrightarrow$ **PASSED**
* `test_maintenance_task_cross_project_reference_rejection` $\longrightarrow$ **PASSED**
* `test_survival_observation_creation_and_rate_derivation` $\longrightarrow$ **PASSED**
* `test_survival_observation_duplicate_active_rejected` $\longrightarrow$ **PASSED**
* `test_atomic_observation_supersession_workflow` $\longrightarrow$ **PASSED**
* `test_dynamic_monitoring_alerts_evaluation` $\longrightarrow$ **PASSED**
* `test_concurrent_supersession_atomicity` $\longrightarrow$ **PASSED**
* `test_cross_project_survival_activity_and_inspection` $\longrightarrow$ **PASSED**
* `test_survival_trajectory_calculation_fidelity` $\longrightarrow$ **PASSED**
* `test_multi_tenant_scoping_for_monitoring` $\longrightarrow$ **PASSED**

**Result: 16/16 Passed in 1.88s (100% Pass Rate)**

---

### Complete Backend Regression Test Suite
Executed: `pytest -v`
* Monitoring Domain Services: 16 tests passed
* Monitoring Schema & Migrations: 11 tests passed
* Auth, RBAC & Token Lifecycle: 33 tests passed
* Dashboard & Environmental Ledger: 7 tests passed
* Operations, Verification & Anti-Self-Verification: 18 tests passed
* Projects, Assignments & Targets: 18 tests passed
* Models & Integrity Constraints: 5 tests passed
* Database & E2E Production Acceptance: 4 tests passed

**Total Backend Test Count:** **112/112 passed (100% Pass Rate in 47.33s)** with zero regressions.

---

### Complete Frontend Test Suite
Executed: `npm test`
* Target Achievement & Progress Calculation: 5 tests passed
* Metric Dimensionality & Catalog Isolation: 1 test passed
* Attention Projects Evaluation Rules: 3 tests passed
* Living Earth Geospatial Validation: 2 tests passed
* Field Operations & Verification Logic: 7 tests passed
* Project Portfolio & Workspace Unit Tests: 9 tests passed
* Authentication & RBAC Unit Tests: 5 tests passed

**Total Frontend Test Count:** **32/32 passed (100% Pass Rate in 0.22s)** with zero regressions.

---

## 6. Known Limitations & Scope Boundaries

1. **API Router Scope Restriction:** Per Phase 6.2 instructions, FastAPI monitoring router endpoints (`/api/v1/monitoring/*`) and HTTP wiring have not been introduced yet and remain scheduled for the next phase.
2. **Frontend Scope Restriction:** Frontend views, React components, and UI integrations have not been modified.
3. **External Queue Restriction:** In accordance with modular monolith rules, alert evaluations execute exclusively via fast in-database PostgreSQL queries without Celery, Redis, or background workers.
4. **Historical Planting Ledger Protection:** Official environmental achievements reflect verified planting submissions only. Mortality observations do not mutate verified ledger entries.

---

## 7. Stage Gate Sign-Off

Phase 6.2 domain logic implementation is complete, verified, and locked. The codebase is ready to proceed to Phase 6.3 upon explicit stakeholder authorization.
