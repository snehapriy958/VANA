# VANA Phase 6.3 — Monitoring API & RBAC: Completion Report

> **Document Status:** Complete & Verified\
> **Milestone:** Phase 6.3 (Field Monitoring & Follow-up Management — API Router & RBAC)\
> **Date:** November 4, 2026\
> **FastAPI Mounting Route:** `/api/v1/monitoring`\
> **Backend Test Results:** 118/118 Tests Passed (100% Pass Rate in 49.43s)\
> **Frontend Test Results:** 32/32 Tests Passed (100% Pass Rate in 0.22s)\
> **OpenAPI Endpoints Mounted:** 19 Monitoring Endpoints Active & Documented\
> **Sign-Off:** Ready for User Review\

---

## 1. Executive Summary

Phase 6.3 successfully exposes the core domain logic and services of the Field Monitoring & Follow-up Management module through 19 fully validated, role-scoped FastAPI REST endpoints mounted under `/api/v1/monitoring`.

All endpoints delegate business operations to the existing Phase 6.2 domain services (`InspectionService`, `MaintenanceTaskService`, `SurvivalObservationService`, `AlertService`, `MonitoringDashboardService`, `MonitoringAuthorizationService`). The API layer enforces server-side Role-Based Access Control (RBAC), multi-tenant project assignment scoping, IDOR protection, request validation via Pydantic v2, SHA-256 evidence handling, and rejection of client-supplied survival calculations.

---

## 2. Files Created and Modified

### Created Files
1. [`backend/app/domains/monitoring/router.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/monitoring/router.py)
   * FastAPI APIRouter mounted at `/api/v1/monitoring` containing 19 REST endpoints across inspections, tasks, survival observations, dynamic alerts, and dashboard KPIs.
2. [`backend/tests/domains/monitoring/test_monitoring_api.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/tests/domains/monitoring/test_monitoring_api.py)
   * 6 comprehensive integration test suites verifying HTTP status codes, request validation, RBAC boundaries, evidence upload/streaming, and IDOR protection.
3. [`docs/PHASE_6_3_COMPLETION_REPORT.md`](file:///c:/Developers/Sneha/Projects/VANA/docs/PHASE_6_3_COMPLETION_REPORT.md)
   * Official completion report for Phase 6.3.

### Modified Files
1. [`backend/app/main.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/main.py)
   * Registered `monitoring_router` under `settings.API_V1_STR`.
2. [`backend/app/domains/monitoring/schemas.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/monitoring/schemas.py)
   * Added `MonitoringEvidenceResponse` and `MonitoringDashboardResponse`.
3. [`backend/app/domains/monitoring/services.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/monitoring/services.py)
   * Added `InspectionService.upload_evidence` and `MonitoringDashboardService.get_dashboard_summary`.
4. [`backend/app/domains/operations/services.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/operations/services.py)
   * Hardened `EvidenceService.get_evidence_file_path` to resolve project scoping from either `activity` or `inspection` targets.
5. [`IMPLEMENTATION_STATUS.md`](file:///c:/Developers/Sneha/Projects/VANA/IMPLEMENTATION_STATUS.md)
   * Updated tracking matrix and Phase 6.3 checklist.

---

## 3. Endpoint Inventory & Specification

### 3.1 Field Inspections

| HTTP Method | Route | Description | Allowed Roles | Request Body / Params | Status Code |
| :--- | :--- | :--- | :---: | :--- | :---: |
| `POST` | `/api/v1/monitoring/inspections` | Schedule new inspection | `ADMIN`, `PM` (Assigned) | `FieldInspectionCreate` (JSON) | `201 Created` |
| `GET` | `/api/v1/monitoring/inspections` | List inspections (paginated) | `ADMIN`, `PM`, `FIELD_OFFICER` | Query: `project_id`, `status`, `assigned_to_id`, `from_date`, `to_date`, `skip`, `limit` | `200 OK` |
| `GET` | `/api/v1/monitoring/inspections/{id}` | Get inspection details | `ADMIN`, `PM`, `FIELD_OFFICER` | Path: `id: UUID` | `200 OK` |
| `POST` | `/api/v1/monitoring/inspections/{id}/start` | Transition to `IN_PROGRESS` | `ADMIN`, `PM`, `FIELD_OFFICER` (Owner) | Path: `id: UUID`, Body: `InspectionStartRequest` | `200 OK` |
| `POST` | `/api/v1/monitoring/inspections/{id}/complete` | Complete inspection with findings | `ADMIN`, `PM`, `FIELD_OFFICER` (Owner) | Path: `id: UUID`, Body: `InspectionCompleteRequest` | `200 OK` |
| `POST` | `/api/v1/monitoring/inspections/{id}/cancel` | Cancel inspection with reason | `ADMIN`, `PM` (Assigned) | Path: `id: UUID`, Body: `InspectionCancelRequest` | `200 OK` |
| `POST` | `/api/v1/monitoring/inspections/{id}/addendum` | Record post-completion addendum | `ADMIN`, `PM` (Assigned) | Path: `id: UUID`, Body: `InspectionAddendumCreate` | `200 OK` |
| `POST` | `/api/v1/monitoring/inspections/{id}/evidence` | Upload photo/document evidence | `ADMIN`, `PM`, `FIELD_OFFICER` (Owner) | Form: `file: UploadFile`, `latitude`, `longitude`, `caption` | `201 Created` |

### 3.2 Maintenance Tasks

| HTTP Method | Route | Description | Allowed Roles | Request Body / Params | Status Code |
| :--- | :--- | :--- | :---: | :--- | :---: |
| `POST` | `/api/v1/monitoring/tasks` | Create maintenance task | `ADMIN`, `PM` (Assigned) | `MaintenanceTaskCreate` (JSON) | `201 Created` |
| `GET` | `/api/v1/monitoring/tasks` | List maintenance tasks (paginated) | `ADMIN`, `PM`, `FIELD_OFFICER` | Query: `project_id`, `status`, `assigned_to_id`, `priority`, `category`, `skip`, `limit` | `200 OK` |
| `GET` | `/api/v1/monitoring/tasks/{id}` | Get maintenance task details | `ADMIN`, `PM`, `FIELD_OFFICER` | Path: `id: UUID` | `200 OK` |
| `POST` | `/api/v1/monitoring/tasks/{id}/start` | Transition task to `IN_PROGRESS` | `ADMIN`, `PM`, `FIELD_OFFICER` (Owner) | Path: `id: UUID`, Body: `TaskStartRequest` | `200 OK` |
| `POST` | `/api/v1/monitoring/tasks/{id}/complete` | Complete task with notes | `ADMIN`, `PM`, `FIELD_OFFICER` (Owner) | Path: `id: UUID`, Body: `TaskCompleteRequest` | `200 OK` |
| `POST` | `/api/v1/monitoring/tasks/{id}/cancel` | Cancel task with reason | `ADMIN`, `PM` (Assigned) | Path: `id: UUID`, Body: `TaskCancelRequest` | `200 OK` |
| `POST` | `/api/v1/monitoring/tasks/{id}/reopen` | Reopen completed task | `ADMIN`, `PM` (Assigned) | Path: `id: UUID`, Body: `TaskReopenRequest` | `200 OK` |

### 3.3 Survival Observations

| HTTP Method | Route | Description | Allowed Roles | Request Body / Params | Status Code |
| :--- | :--- | :--- | :---: | :--- | :---: |
| `POST` | `/api/v1/monitoring/survival-observations` | Record survival observation | `ADMIN`, `PM`, `FIELD_OFFICER` | `SurvivalObservationCreate` (JSON) | `201 Created` |
| `GET` | `/api/v1/monitoring/survival-observations` | Get observation history | `ADMIN`, `PM`, `FIELD_OFFICER` | Query: `project_id` (mandatory), `plot_identifier`, `cohort_identifier`, `active_only`, `skip`, `limit` | `200 OK` |
| `GET` | `/api/v1/monitoring/survival-observations/{id}` | Get observation details | `ADMIN`, `PM`, `FIELD_OFFICER` | Path: `id: UUID` | `200 OK` |
| `POST` | `/api/v1/monitoring/survival-observations/{id}/correct` | Record superseding correction | `ADMIN`, `PM` (Assigned) | Path: `id: UUID`, Body: `SurvivalObservationCorrectionRequest` | `200 OK` |
| `GET` | `/api/v1/monitoring/survival-analytics` | Longitudinal survival trajectory | `ADMIN`, `PM`, `FIELD_OFFICER` | Query: `project_id`, `plot_identifier`, `cohort_identifier` | `200 OK` |

### 3.4 Monitoring Operations

| HTTP Method | Route | Description | Allowed Roles | Request Body / Params | Status Code |
| :--- | :--- | :--- | :---: | :--- | :---: |
| `GET` | `/api/v1/monitoring/alerts` | Query active operational alerts | `ADMIN`, `PM`, `FIELD_OFFICER` | Query: `project_id` (optional scoping) | `200 OK` |
| `GET` | `/api/v1/monitoring/dashboard` | Monitoring KPIs & backlog summary | `ADMIN`, `PM`, `FIELD_OFFICER` | Query: `project_id` (optional scoping) | `200 OK` |

---

## 4. RBAC & Multi-Tenant Enforcement

Every endpoint invokes `MonitoringAuthorizationService.verify_project_access` or `get_scoped_project_ids` server-side:
* **Admin Privilege:** `ADMIN` has organization-wide visibility across all projects and can perform management actions (schedule inspections, create tasks, cancel, record addenda, perform supersession).
* **Project Manager Scoping:** `PROJECT_MANAGER` access is strictly checked against PostgreSQL `project_assignments`. Attempting to access an unassigned project returns `HTTP 403 FORBIDDEN` (`PROJECT_ACCESS_DENIED`).
* **Field Officer Scoping & Ownership:**
  * Can view monitoring records strictly within assigned projects.
  * Can start, upload evidence to, and complete inspections **only if `assigned_to_id == current_user.id`**.
  * Can start and complete tasks **only if `assigned_to_id == current_user.id`**.
  * Scheduling inspections, creating tasks, cancelling, reopening, recording addenda, and superseding observations are forbidden (`HTTP 403 FORBIDDEN`).
* **IDOR Protection:** All entity Lookups (`/inspections/{id}`, `/tasks/{id}`, `/survival-observations/{id}`) verify that the requesting user has legitimate assignment access to the entity's `project_id` before returning details or applying mutations.

---

## 5. Evidence Upload & Retrieval Integration

* **Endpoint:** `POST /api/v1/monitoring/inspections/{id}/evidence`
* **Storage Engine:** Reuses `LocalStorageService` with SHA-256 deduplication.
* **Integrity Constraints:**
  * Protected under `ON DELETE RESTRICT` (inspections with evidence attachments cannot be deleted).
  * Validates MIME types (`image/jpeg`, `image/png`, `image/webp`, `application/pdf`).
  * Enforces maximum file size of 10 MB (`MAX_FILE_SIZE_BYTES`).
  * Enforces database check constraint `chk_evidence_target`:
    ```sql
    CONSTRAINT chk_evidence_target CHECK (
        (activity_id IS NOT NULL AND revision_id IS NOT NULL AND inspection_id IS NULL)
        OR
        (inspection_id IS NOT NULL AND activity_id IS NULL AND revision_id IS NULL)
    );
    ```
* **Streaming Retrieval:** `GET /api/v1/operations/evidence/{id}` verifies project access via either `evidence.activity.project_id` or `evidence.inspection.project_id` before streaming file bytes.

---

## 6. Automated Testing Results

### Phase 6.3 Dedicated API Test Suite
File: [`backend/tests/domains/monitoring/test_monitoring_api.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/tests/domains/monitoring/test_monitoring_api.py)
* `test_api_schedule_and_list_inspections` $\longrightarrow$ **PASSED**
* `test_api_inspection_lifecycle_ownership_and_addenda` $\longrightarrow$ **PASSED**
* `test_api_inspection_evidence_upload_and_access` $\longrightarrow$ **PASSED**
* `test_api_maintenance_task_lifecycle_and_reopen` $\longrightarrow$ **PASSED**
* `test_api_survival_observation_creation_and_supersession` $\longrightarrow$ **PASSED**
* `test_api_alerts_and_dashboard_endpoints` $\longrightarrow$ **PASSED**

**Result: 6/6 test suites passed in 7.79s.**

### Combined Monitoring Domain Test Suite
Files in `tests/domains/monitoring/`:
* `test_monitoring_api.py`: 6 passed
* `test_monitoring_domain_services.py`: 16 passed
* `test_monitoring_schema_and_migration.py`: 11 passed

**Result: 33/33 monitoring tests passed in 9.55s.**

### Full Backend Regression Test Suite
Executed: `pytest -v` across all 8 domain test modules.
* **Total Backend Tests:** **118 passed in 49.43s (100% Pass Rate)**
* **Regressions:** 0

### Frontend Test Suite
Executed: `npm test`
* **Total Frontend Tests:** **32 passed in 0.22s (100% Pass Rate)**
* **Regressions:** 0

---

## 7. OpenAPI Verification

OpenAPI documentation generated and confirmed via FastAPI runtime introspection:
```powershell
Total monitoring endpoints mounted: 19
/api/v1/monitoring/alerts
/api/v1/monitoring/dashboard
/api/v1/monitoring/inspections
/api/v1/monitoring/inspections/{id}
/api/v1/monitoring/inspections/{id}/addendum
/api/v1/monitoring/inspections/{id}/cancel
/api/v1/monitoring/inspections/{id}/complete
/api/v1/monitoring/inspections/{id}/evidence
/api/v1/monitoring/inspections/{id}/start
/api/v1/monitoring/survival-analytics
/api/v1/monitoring/survival-observations
/api/v1/monitoring/survival-observations/{id}
/api/v1/monitoring/survival-observations/{id}/correct
/api/v1/monitoring/tasks
/api/v1/monitoring/tasks/{id}
/api/v1/monitoring/tasks/{id}/cancel
/api/v1/monitoring/tasks/{id}/complete
/api/v1/monitoring/tasks/{id}/reopen
/api/v1/monitoring/tasks/{id}/start
```

---

## 8. Known Limitations & Strict Scope Boundary

1. **Frontend Integration Restriction:** Frontend API client hooks (`monitoringApi.ts`) and React views have not been modified or created, per explicit instruction. That is reserved for Phase 6.4 (API client) and Phase 6.5 (monitoring UI).
2. **Database Schema Unchanged:** Zero schema migrations were executed.
3. **No External Background Workers:** Alerts are queried dynamically in PostgreSQL without Redis or Celery.

---

## 9. Next Stage Gate

Phase 6.3 is complete, hardened, and verified. Work is paused awaiting your explicit instruction before proceeding to Phase 6.4.
