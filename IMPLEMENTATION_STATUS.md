# VANA — Implementation Status

**Current Stage:** Phase 6.6 Full Platform End-to-End Acceptance Completed and Accepted | Milestones 1A–5 and 6.1–6.6 Fully Verified  
**Overall Status:** All Implemented Domains (Phases 1A–5 and 6.1–6.6) 100% Complete, Hardened, End-to-End Audited & Accepted (All 119 Backend + 77 Frontend Tests Passed)  
**Last Updated:** 2026-11-04  

---

## 1. Milestone Tracking Matrix

| Milestone | Description | Status | Target Date | Completed Date | Test Pass Rate | Sign-Off |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **M0** | Documentation & Design System | **COMPLETED** | 2026-11-02 | 2026-11-02 | 100% (Audit Passed) | Approved by User |
| **M1A** | Backend Foundation, Models & Migrations | **COMPLETED** | 2026-11-02 | 2026-11-02 | 100% (8/8 Tests Passed) | Approved by User |
| **M1B** | Frontend Scaffolding & Design Tokens | **COMPLETED** | 2026-11-02 | 2026-11-02 | 100% (Typecheck & Build Clean) | Approved by User |
| **M2** | Auth, RBAC & User Management | **COMPLETED** | 2026-11-02 | 2026-11-02 | 100% (41/41 Backend, 5/5 Frontend) | Token Lifecycle Verified |
| **M3** | Project Portfolio & Targets | **COMPLETED** | 2026-11-02 | 2026-11-02 | 100% (59/59 Backend, 14/14 Frontend) | Acceptance Audit PASS |
| **M4** | Field Operations, Evidence & Verification | **COMPLETED** | 2026-11-03 | 2026-11-03 | 100% (77/77 Backend, 21/21 Frontend) | Acceptance Audit PASS |
| **M5** | Environmental Ledger & Organization Dashboard | **COMPLETED** | 2026-11-03 | 2026-11-03 | 100% (84/84 Backend, 32/32 Frontend) | Acceptance Audit PASS |
| **M6** | Living Earth Interactive Map | **COMPLETED** (Integrated in M5) | 2026-11-03 | 2026-11-03 | 100% (Integrated in Map View) | Acceptance Audit PASS |
| **Phase 6.1** | Field Monitoring Schema & Migration | **COMPLETED** | 2026-11-03 | 2026-11-03 | 100% (96/96 Backend, 11/11 Phase 6.1 Tests) | Acceptance Audit PASS |
| **Phase 6.2** | Field Monitoring Domain Services & Logic | **COMPLETED** | 2026-11-04 | 2026-11-04 | 100% (112/112 Backend, 16/16 Phase 6.2 Tests) | Acceptance Audit PASS |
| **Phase 6.3** | Field Monitoring APIs & Multi-Tenant RBAC | **COMPLETED** | 2026-11-04 | 2026-11-04 | 100% (118/118 Backend, 6/6 API Suites) | Acceptance Audit PASS |
| **Phase 6.4** | Frontend API Integration & TanStack Query | **COMPLETED** | 2026-11-04 | 2026-11-04 | 100% (61/61 Frontend, Typecheck/Build Clean) | Acceptance Audit PASS |
| **Phase 6.5** | Field Monitoring UI Workspaces & Modals | **COMPLETED & ACCEPTED** | 2026-11-04 | 2026-11-04 | 100% (77/77 Frontend, Typecheck/Build Clean) | Acceptance Audit PASS & Approved |
| **Phase 6.6** | Full Platform End-to-End Acceptance | **COMPLETED & ACCEPTED** | 2026-11-04 | 2026-11-04 | 100% (119/119 Backend, 77/77 Frontend) | Acceptance Audit PASS & Approved |
| **Production Readiness** | Pre-Deployment Audit & Security Hardening | **READY** | 2026-11-04 | 2026-11-04 | 100% (130/130 Backend, 77/77 Frontend) | All 3 Blockers Resolved & Verified |
| **M7** | Executive Analytics & Reporting | PENDING | TBD | — | 0% | — |
| **M8** | Audit History & Final Security Review | PENDING | TBD | — | 0% | — |

---

## 2. Milestone 1A Deliverables Verification

* [x] **Project Scaffolding:** FastAPI modular monolith project structure created in `backend/app/`.
* [x] **Pydantic Settings:** `app/core/config.py` configured with `.env` / `.env.example`.
* [x] **Database Engine:** Async SQLAlchemy 2.x engine and sessionmaker in `app/core/database.py`.
* [x] **Security Primitives:** Argon2id hasher and JWT utilities in `app/core/security.py`.
* [x] **Storage Abstraction:** `IStorageService` and `LocalStorageService` in `app/core/storage.py`.
* [x] **Database Models:** All 8 domain models implemented across `app/domains/` and consolidated in `app/models.py`.
* [x] **Alembic Baseline Migration:** `alembic/versions/0001_initial_schema.py` generated with topological order.
* [x] **Migration Verification:** Two-way migration cycle (`upgrade head` $\to$ `downgrade base` $\to$ `upgrade head`) verified clean.
* [x] **Partial Unique Index:** `uq_activity_single_active_ledger` verified; strictly prevents double counting active ledger revisions.
* [x] **Check Constraints:** Verified `chk_active_ledger_verified`, `chk_rejection_reason_required`, `chk_verification_signature_required`, and FK delete restrict.
* [x] **Health Check Endpoint:** `GET /health` verified live against running PostgreSQL instance.
* [x] **Automated Test Suite:** 8/8 pytest tests passing (100% pass rate in 1.80s).

---

## 3. Milestone 1B Deliverables Verification

* [x] **Frontend Scaffolding:** React 19, TypeScript ~5.7.2, Vite ^6.2.0 configured in `frontend/`.
* [x] **VANA Design Tokens:** Tailwind CSS configured with exact approved brand tokens:
  * Forest: `#183D32` (Primary, headings, active states)
  * Ivory: `#F5F3EA` (Canvas background, muted surface)
  * Sage: `#A8B99B` (Accent, soft borders, muted badges)
  * Gold: `#D6A76A` (Highlights, earth warmth, action accents)
  * Charcoal: `#29332F` (High-contrast body text, structural borders)
  * White: `#FFFFFF` (Card surfaces, elevated components)
  * Crimson: `#9E3A2B` (Destructive actions, rejection states, errors)
* [x] **Typography Scale:** Google Fonts loaded in `index.html` with `Manrope` (headings) and `Inter` (body, data, tabular numbers).
* [x] **Component Primitives:** Reusable accessible primitives created under `src/components/ui/` (`Button`, `Badge`, `Card`, `Input`, `Dialog`).
* [x] **Application Shell:** Responsive layout with sticky desktop sidebar (`w-64`) and slide-in mobile navigation drawer with backdrop.
* [x] **Final Gate Audit:** Complete audit documented in `docs/MILESTONE_1B_FINAL_GATE_AUDIT.md` (Dependencies, Git & Env safety, API config, Browser limitations, and Regression checks).

---

## 4. Milestone 2 Deliverables Verification

* [x] **Backend Authentication:**
  * `POST /api/v1/auth/login`: Argon2id password verification, JWT access (60 min) and refresh (7 days) token issuance.
  * `POST /api/v1/auth/refresh`: Stateless token rotation exchanging valid refresh tokens for new access tokens.
  * `GET /api/v1/auth/me`: Current authenticated user profile with active role.
  * `POST /api/v1/auth/logout`: Graceful session termination with immutable audit event logging.
* [x] **Role-Based Access Control (RBAC):**
  * Strict enforcement of `ADMIN`, `PROJECT_MANAGER`, and `FIELD_OFFICER` server-side dependencies (`require_roles`, `require_admin`, `require_pm_or_admin`).
  * Anti-self-role modification: Users (including administrators) prohibited from altering their own role (`SELF_ROLE_CHANGE_PROHIBITED`).
  * Privilege escalation prevention: Non-admins blocked with HTTP 403 (`UNAUTHORIZED_ROLE_ESCALATION`, `UNAUTHORIZED_STATUS_CHANGE`).
  * Project-level authorization boundary dependency established for subsequent milestones (`verify_project_access`).
* [x] **User Management APIs:**
  * `GET /api/v1/users`: Scoped directory listing (`ADMIN` sees organization-wide; `PROJECT_MANAGER` sees users assigned to their projects; `FIELD_OFFICER` denied).
  * `POST /api/v1/users`: Provisioning endpoint with duplicate email conflict prevention (`HTTP 409 EMAIL_ALREADY_EXISTS`) and Argon2 hashing (restricted to `ADMIN`).
  * `GET /api/v1/users/{id}`: Detailed user profile access (ADMIN, Self, or assigned PM).
  * `PUT /api/v1/users/{id}`: Attribute modification and user deactivation with audit trail.
* [x] **Security & Audit Logging:**
  * Automated credential scrubbing (`sanitize_state`) preventing passwords, hashes, and JWT tokens from ever being persisted in `audit_logs` state diffs.
  * Audit events recorded for `USER_LOGIN_SUCCESS`, `USER_LOGIN_FAILED`, `USER_LOGOUT`, `USER_CREATED`, `USER_UPDATED`, `USER_ROLE_CHANGED`, `USER_ACTIVATED`, `USER_DEACTIVATED`.
* [x] **Frontend Authentication & State:**
  * React 19 `LoginView` built on VANA design tokens with React Hook Form + Zod email/password validation.
  * `AuthContext` with in-memory token state and tab-scoped `sessionStorage` (strictly avoids persistent `localStorage`).
  * `ProtectedRoute` enforcing authentication and role-based route boundaries with clear 403 Forbidden feedback.
  * Role-aware `Sidebar` navigation dynamically hiding/showing unauthorized views.
  * `Header` displaying authenticated user name, email, role badge, and interactive Logout button.
  * `UserManagementView` providing personnel directory table, provisioning modal dialog, and instant activation/deactivation toggles for administrators.
* [x] **Final Security Audit:** Complete audit documented in `docs/MILESTONE_2_FINAL_SECURITY_AUDIT.md` (JWT lifecycle, refresh-token rotation/revocation, role freshness against PostgreSQL, project boundaries, audit sanitization).
* [x] **Token Lifecycle & Concurrency Verification:** Complete verification documented in `docs/MILESTONE_2_TOKEN_LIFECYCLE_REVIEW.md` (concurrent atomicity via PostgreSQL advisory lock, append-only audit log integrity, logout invalidation mechanics).
* [x] **Testing & Verification:**
  * Full backend test suite passing: **41/41 tests passed (100%) in 10.44s**.
  * Frontend unit tests passing: **5/5 tests passed (100%) in 0.14s**.
  * Frontend typecheck clean: `npm run typecheck` exits with code 0.
  * Frontend production build clean: `npm run build` exits with code 0 (1794 modules transformed).

---

## 5. Milestone 3 Deliverables Verification

* [x] **Project Management Backend:**
  * `POST /api/v1/projects`: Admin-only creation with unique uppercase project code, latitude/longitude boundary checks, and optional GeoJSON polygon.
  * `GET /api/v1/projects`: Role-scoped portfolio directory (ADMIN views all; PM and FIELD_OFFICER view assigned projects).
  * `GET /api/v1/projects/{id}`: Detailed workspace retrieval with targets and team roster.
  * `PUT /api/v1/projects/{id}`: Authorized for ADMIN and assigned PM with strict lifecycle status transition validation (`DRAFT`, `ACTIVE`, `COMPLETED`, `ARCHIVED`).
* [x] **Project Team Assignments:**
  * `POST /api/v1/projects/{id}/assignments`: Allocates users to project rosters with active status validation and duplicate rejection (`HTTP 409 Conflict`).
  * `GET /api/v1/projects/{id}/assignments`: Lists project roster with user profile details.
  * `DELETE /api/v1/projects/{id}/assignments/{userId}`: Removes user from project roster.
* [x] **Environmental Targets:**
  * Authoritative catalog engine in `app/domains/projects/metrics.py` defining 7 approved metrics across 4 active categories.
  * Unit validation enforcing compatible units per metric definition; cross-metric aggregation strictly forbidden.
  * `POST /api/v1/projects/{id}/targets`: Creates dimensional targets; duplicate target check prevents duplicate active targets for the same metric.
  * `GET /api/v1/projects/{id}/targets`: Lists dimensional targets enriched with category, dimension, and canonical unit.
  * `PUT /api/v1/projects/{id}/targets/{targetId}`: Updates target quantity, unit, or deadline.
  * `DELETE /api/v1/projects/{id}/targets/{targetId}`: Removes target from project.
  * `GET /api/v1/metrics/catalog`: Exposes approved metric catalog for dynamic frontend consumption.
* [x] **Geographic Boundary & Coordinate Validation:**
  * Native PostgreSQL JSONB storage without PostGIS overhead.
  * Pydantic RFC 7946 GeoJSON Polygon validator enforcing closed linear rings ($\ge 4$ vertices, `first == last`) and bounds checks (`[-180..180, -90..90]`).
* [x] **Audit Trail Integrity:**
  * Records immutable audit entries: `PROJECT_CREATED`, `PROJECT_UPDATED`, `PROJECT_STATUS_CHANGED`, `TARGET_CREATED`, `TARGET_UPDATED`, `TARGET_DELETED`, `ASSIGNMENT_CREATED`, `ASSIGNMENT_DELETED`.
* [x] **Frontend Views & Integration:**
  * `ProjectPortfolioView.tsx` (`/projects`): Search, status filter pills, card grid/table toggle, status badges, "New Project" modal (Admin).
  * `ProjectWorkspaceView.tsx` (`/projects/:projectId`): Hero summary banner, 4 interactive tabs (`Overview`, `Targets`, `Team Roster`, `Geographic Information`), "Add Target" modal, "Assign Member" modal, "Edit Project" modal, GeoJSON viewer.
* [x] **Final Acceptance Audit:** Full audit documented in `docs/MILESTONE_3_FINAL_ACCEPTANCE_AUDIT.md` (Audit Verdict: **PASS**).
* [x] **Testing & Verification:**
  * Full backend test suite passing: **59/59 tests passed (100%) in 22.47s**.
  * Full frontend test suite passing: **14/14 tests passed (100%) in 0.15s**.
  * Frontend typecheck clean: `npm run typecheck` exits with code 0.
  * Frontend production build clean: `npm run build` exits with code 0 (1798 modules transformed in 8.46s).

---

## 6. Milestone 4 Deliverables Verification

* [x] **Field Activity Reporting Backend:**
  * `POST /api/v1/operations/activities`: Multipart/form-data submission with positive quantity validation, metric/target verification, project scoping check, and initial Revision 1 creation (`PENDING`, `is_active_ledger_entry = False`).
  * `GET /api/v1/operations/activities`: Role-scoped activity listing with filters (`project_id`, `status`, `metric_code`, `is_archived`).
  * `GET /api/v1/operations/activities/{id}`: Detailed retrieval of logical activity container with full immutable revision history.
  * `POST /api/v1/operations/activities/{id}/revisions`: Amendment and correction submission with duplicate pending prevention (`PENDING_REVISION_EXISTS`) and net adjustment calculation.
  * `DELETE /api/v1/operations/activities/{id}`: Soft-delete/archiving endpoint for Admin and assigned PMs, deactivating any active ledger entries.
* [x] **Photo Evidence Management:**
  * Strict validation for MIME types (`image/jpeg`, `image/png`, `image/webp`, `application/pdf`) and max file size (10 MB).
  * Content-addressed storage using SHA-256 via `LocalStorageService` under `uploads/`.
  * Secure, access-controlled streaming endpoint: `GET /api/v1/operations/evidence/{evidence_id}` enforcing project assignment authorization before serving file bytes.
* [x] **Activity Verification Centre & Anti-Self-Verification Gate:**
  * `GET /api/v1/verification/queue`: Triage queue for reviewers (Admin org-wide; PM assigned projects; Field Officers forbidden with HTTP 403).
  * `POST /api/v1/verification/revisions/{id}/decision`: Digital sign-off supporting `VERIFIED` and `REJECTED`.
  * **Mandatory Rule 5 (Anti-Self-Verification Gate):** Strict server-side rejection (`HTTP 403 SELF_VERIFICATION_PROHIBITED`) if `current_user.id == activity.created_by_id`.
  * Mandatory rejection validation requiring a valid `rejection_reason_code` (`INSUFFICIENT_EVIDENCE`, `COORDINATES_MISMATCH`, `INCORRECT_UNIT_OR_QUANTITY`, `DUPLICATE_SUBMISSION`, `DATA_ENTRY_ERROR`) and non-empty `review_notes`.
  * **5-Ledger Accounting:** Approvals atomically activate target revision and deactivate previous active ledger entries. Rejections preserve previously verified revisions in the active ledger.
* [x] **Frontend Views & Integration:**
  * `FieldOperationsView.tsx` (`/operations`): Mobile-optimized submission modal, project and metric selectors, GPS location capture with accuracy warning (>25m), multi-file photo uploader with instant preview, revision history drawer, amendment modal, and draft persistence in `sessionStorage`.
  * `VerificationCentreView.tsx` (`/verification`): Split-screen triage queue, submitter inspection, net adjustment breakdown, photo evidence viewer with full lightbox, GPS verification, approval confirmation modal, and rejection modal with calibrated reason codes.
  * Anti-self-verification UI protection: Approve and Reject buttons disabled with descriptive policy violation warnings when an author views their own submission.
* [x] **Final Acceptance Audit:** Full audit documented in `docs/MILESTONE_4_FINAL_ACCEPTANCE_AUDIT.md` (Audit Verdict: **PASS**).
* [x] **Testing & Verification:**
  * Full backend test suite passing: **77/77 tests passed (100%) in 42.06s**.
  * Full frontend test suite passing: **21/21 tests passed (100%) in 0.25s**.
  * Frontend typecheck clean: `npm run typecheck` exits with code 0.
  * Frontend production build clean: `npm run build` exits with code 0 (1801 modules transformed in 11.65s).

---

## 7. Milestone 5 Deliverables Verification

* [x] **Authoritative Environmental Ledger Engine:**
  * Implemented `EnvironmentalLedgerService` in `backend/app/domains/analytics/services.py`.
  * Verified aggregation strictly queries `ActivityRevision.is_active_ledger_entry = True` and excludes unreviewed, rejected, or archived (`is_archived = True`) activities.
  * Preserves metric dimensionality (Rule 8) and converts units cleanly to canonical units using `APPROVED_METRIC_CATALOG`.
  * Isolates net pending adjustments without inflating official verified totals.
  * Verified arithmetic against user-specified test: 1,000 target, verified 200 + 250 + 150 = 600 (60% achievement, 400 remaining); unreviewed amendment of +50 leaves verified strictly at 600.
* [x] **Backend Analytics & Dashboard Endpoints:**
  * `GET /api/v1/dashboard/overview`: High-level KPI cards, attention project alerts, and metric progress summaries.
  * `GET /api/v1/dashboard/projects`: Project portfolio balance sheet with verified achievement percentages and coordinates.
  * `GET /api/v1/dashboard/recent-activity`: Real-time operational audit feed of submissions, approvals, rejections, and amendments.
  * `GET /api/v1/analytics/projects/{project_id}/impact`: Comprehensive ledger breakdown with revision health counts.
  * `GET /api/v1/analytics/projects/{project_id}/trends`: Activity velocity and cumulative progress time-series.
  * `GET /api/v1/analytics/metrics`: Active metrics catalog summary.
* [x] **Multi-Tenant RBAC Authorization:**
  * Portfolio-wide visibility for `ADMIN`.
  * Strict project assignment scoping for `PROJECT_MANAGER` and `FIELD_OFFICER`. Unauthorized project queries return `HTTP 403 FORBIDDEN`.
* [x] **Organization Dashboard (`/dashboard`):**
  * `OrganizationDashboardView.tsx` with role-aware metrics, Recharts portfolio chart, attention alerts, recent activity feed, and project table.
* [x] **Project-Level Impact Analytics:**
  * Integrated dedicated "Impact & Analytics" tab in `ProjectWorkspaceView.tsx` with bi-level progress bars (forest green verified + gold pending adjustment), Recharts activity velocity curve, and immutable revision accounting audit.
* [x] **Living Earth Interactive Map (`/map`):**
  * Implemented `LivingEarthMap.tsx` and `LivingEarthMapView.tsx` using `react-leaflet` with status-colored SVG pins, popups with verified progress, coordinate bounds validation, and workspace links.
* [x] **Automated Testing Suite:**
  * Backend pytest: **84/84 tests passed (100%) in 37.40s**.
  * Frontend unit tests: **32/32 tests passed (100%) in 0.18s**.
  * Frontend typecheck: clean (`tsc --noEmit`).
  * Frontend production build: clean (`tsc -b && vite build` in 13.94s).

---

## 8. Phase 6.1 Deliverables Verification

* [x] **Domain Models (`app/domains/monitoring/models.py`):**
  * Implemented `FieldInspection` model with health scoring, findings, and composite foreign key to `FieldActivity`.
  * Implemented `MaintenanceTask` model with priority, status lifecycle (`PENDING`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`), deadline, and composite FKs to project/inspection/activity.
  * Implemented `SurvivalObservation` model with sample vs. census tracking, counts (`alive_count`, `dead_count`, `unassessed_count`), methodology checks, partial active uniqueness, and deferred self-referential `superseded_by_id`.
  * Derived survival rate property strictly calculated as `alive_count / (alive_count + dead_count) * 100` dynamically, preventing static persistence or ungrounded extrapolation.
* [x] **Evidence Target Exclusivity (`app/domains/operations/models.py`):**
  * Extended `EvidenceFile` with optional `inspection_id` (`ON DELETE RESTRICT`), latitude, longitude, and caption.
  * Enforced database check constraint `chk_evidence_target` strictly requiring either `activity_revision_id` OR `inspection_id`, disallowing ambiguous dual-attachments or orphaned evidence.
* [x] **Alembic Database Migration (`alembic/versions/0002_field_monitoring.py`):**
  * Added composite unique constraint `uq_field_activities_id_project` on `field_activities(id, project_id)`.
  * Generated `field_inspections`, `maintenance_tasks`, and `survival_observations` tables with full composite foreign key constraints.
  * Applied PostgreSQL 17's column-specific `ON DELETE SET NULL (column_name)` on composite FKs preserving `project_id`.
  * Enforced partial unique index `uq_active_survival_observation` on `(project_id, plot_identifier, cohort_identifier, observation_date) WHERE is_active = TRUE`.
  * Two-way migration cycle (`upgrade head` $\to$ `downgrade -1` $\to$ `upgrade head`) verified 100% clean and reversible on `vana_test`.
* [x] **Testing & Verification:**
  * Dedicated Phase 6.1 test suite: **11/11 tests passed (100%) in 0.84s** (`tests/domains/monitoring/test_monitoring_schema_and_migration.py`).
  * Full backend regression test suite: **96/96 tests passed (100%) in 41.80s** with 0 regressions.
  * Completion report published in `docs/PHASE_6_1_COMPLETION_REPORT.md`.
  * Architecture Decision Record published in `DECISION_LOG.md` (ADR-019).

---

## 9. Phase 6.2 Deliverables Verification

* [x] **Inspection Management Service (`app/domains/monitoring/services.py`):**
  * Schedule inspection with project assignment validation and cross-project activity rejection.
  * Deterministic state transitions: `SCHEDULED` $\to$ `IN_PROGRESS` $\to$ `COMPLETED` and `SCHEDULED` / `IN_PROGRESS` $\to$ `CANCELLED`.
  * Inspector ownership protection: Field Officers can only start and complete inspections assigned to them.
  * Direct editing locked on completed inspections (`COMPLETED_INSPECTION_LOCKED`).
  * Post-completion correction addenda recorded immutably on completed inspections without mutating original findings.
* [x] **Maintenance Task Service (`app/domains/monitoring/services.py`):**
  * Create maintenance task with project assignment validation and cross-project inspection/activity link validation.
  * Task lifecycle transitions: `TODO` $\to$ `IN_PROGRESS` $\to$ `COMPLETED` with mandatory completion notes.
  * Task cancellation restricted to PM/Admin with mandatory reason.
  * Task reopening (`COMPLETED` $\to$ `TODO`) restricted to PM/Admin with mandatory justification note.
  * Assignee ownership protection: Field Officers can only start and complete their own assigned tasks.
* [x] **Survival Observation Service (`app/domains/monitoring/services.py`):**
  * Server-side derived survival rate: rejects client-supplied survival rates; returns `None` safely when assessed population is zero.
  * Enforces scientific count constraint $(alive\_count + dead\_count) \le sample\_size$.
  * Duplicate active observation prevention: rejects multiple active observations for $(project, plot, cohort, date)$ with `HTTP 409 Conflict`.
  * Atomic observation supersession: locks original with `with_for_update()`, deactivates original (`is_active = False`), creates replacement (`is_active = True`) with identical population identity, and links `superseded_by_id`.
  * Preserves historical superseded rows in history query; provides longitudinal trajectory curves of active observations.
* [x] **Dynamic Alerts Query Engine (`app/domains/monitoring/services.py`):**
  * Pure database-backed SQL dynamic queries for `OVERDUE_INSPECTION`, `UPCOMING_INSPECTION`, and `OVERDUE_TASK`.
  * Zero external background daemons, Celery, Redis, or push notifications.
  * Multi-tenant scoped by user project assignments.
* [x] **Audit Trail Coverage (`app/domains/audit/services.py`):**
  * Immutable audit entries created for all inspection, task, and observation mutations.
* [x] **Testing & Verification:**
  * Dedicated Phase 6.2 domain services test suite: **16/16 tests passed (100%) in 1.88s** (`tests/domains/monitoring/test_monitoring_domain_services.py`).
  * Full monitoring domain tests (schema + services): **27/27 tests passed in 2.52s**.
  * Full backend regression test suite: **112/112 tests passed (100%) in 47.33s** with zero regressions.
  * Frontend unit tests: **32/32 tests passed (100%) in 0.22s**.
  * Completion report published in `docs/PHASE_6_2_COMPLETION_REPORT.md`.

---

## 10. Phase 6.3 Deliverables Verification

* [x] **FastAPI Monitoring Router (`backend/app/domains/monitoring/router.py`):**
  * Mounted 19 REST endpoints under `/api/v1/monitoring`.
  * Field Inspections: schedule, list, get, start, complete, cancel, addendum, evidence upload.
  * Maintenance Tasks: create, list, get, start, complete, cancel, reopen.
  * Survival Observations: create, list, get, correct (supersede), trajectory analytics.
  * Operational Alerts & Dashboard: alerts evaluation, consolidated monitoring dashboard.
* [x] **Multi-Tenant RBAC & Project Scoping:**
  * Independent backend authorization enforcing project assignment and role permissions on every route.
  * `ADMIN` org-wide, `PROJECT_MANAGER` scoped to assigned projects, `FIELD_OFFICER` restricted to assigned projects and assignee-only actions.
* [x] **Testing & Verification:**
  * Dedicated API integration test suite: **6/6 test suites passed** in `tests/domains/monitoring/test_monitoring_api.py`.
  * Backend regression suite: **118/118 tests passed (100%) in 49.43s**.
  * Completion report published in `docs/PHASE_6_3_COMPLETION_REPORT.md`.

---

## 11. Phase 6.4 Deliverables Verification

* [x] **TypeScript Contracts (`frontend/src/types/monitoring.ts`):**
  * Strictly mapped to FastAPI OpenAPI schemas and PostgreSQL domain models.
  * Defined enums: `InspectionStatus`, `InspectionType`, `CanopyCondition`, `SoilMoistureCondition`, `MaintenanceTaskStatus`, `MaintenanceTaskCategory`, `MaintenanceTaskPriority`, `SurvivalMethodology`, `AlertType`, `AlertSeverity`.
  * Defined request/response interfaces: `FieldInspection`, `InspectionCreateRequest`, `InspectionCompleteRequest`, `MaintenanceTask`, `MaintenanceTaskCreateRequest`, `SurvivalObservation`, `SurvivalObservationCreateRequest`, `SurvivalObservationCorrectionRequest`, `SurvivalAnalytics`, `MonitoringAlertSummary`, `MonitoringDashboard`.
* [x] **Shared API Client & Centralized Error Handling (`frontend/src/services/apiClient.ts`):**
  * Enhanced Axios response interceptor for FastAPI/Pydantic error payloads (`detail` string, structured `{ message }`, validation array `[{ loc, msg }]`).
  * Preserves meaningful backend errors for 400, 401, 403, 404, 409, 422, and network failures.
  * Added `extractErrorMessage(error: unknown): string` utility.
* [x] **Monitoring API Service (`frontend/src/services/monitoringService.ts`):**
  * Implemented all 19 endpoints across Field Inspections, Maintenance Tasks, Survival Observations, Trajectory Analytics, Operational Alerts, and Dashboard Summaries.
  * Supports typed request bodies, query parameters, pagination, and multipart `FormData` evidence upload.
* [x] **TanStack Query Hooks (`frontend/src/hooks/useMonitoring.ts`):**
  * Hierarchical query key factory `monitoringKeys` preventing key collisions and enabling targeted cache invalidation.
  * 9 Query hooks: `useInspections`, `useInspection`, `useMaintenanceTasks`, `useMaintenanceTask`, `useSurvivalObservations`, `useSurvivalObservation`, `useSurvivalAnalytics`, `useMonitoringAlerts`, `useMonitoringDashboard`.
  * 13 Mutation hooks with automated cache invalidation preventing stale dashboard and analytics data.
* [x] **Testing & Verification:**
  * Dedicated Phase 6.4 frontend test suite: **29/29 tests passed** in `frontend/tests/monitoring.test.mjs`.
  * Full frontend test suite: **61/61 tests passed (100%) in 196ms**.
  * Frontend typecheck: `tsc --noEmit` clean (code 0).
  * Frontend production build: `tsc -b && vite build` clean (code 0, 2237 modules transformed).
  * Full backend regression test suite: **118/118 tests passed (100%) in 54.92s**.
  * Completion report published in `docs/PHASE_6_4_COMPLETION_REPORT.md`.

---

## 12. Phase 6.5 Deliverables Verification

* [x] **Navigation & Route Integration:**
  * Added "Field Monitoring" navigation item with `Activity` icon in `frontend/src/components/layout/Sidebar.tsx`.
  * Mounted `/monitoring` route rendering `FieldMonitoringView` in `frontend/src/routes/index.tsx`.
* [x] **Four Dedicated Workspace Tabs (`frontend/src/views/monitoring/`):**
  * `MonitoringDashboardTab.tsx`: 6 KPI cards, dynamic alerts banner with severity badges, upcoming inspections, attention tasks, and recent survival feed.
  * `InspectionsTab.tsx`: Filterable registry, search, inspector dropdown, schedule modal, execute/complete modal with health scores (1-5), canopy & moisture condition, detected threats, photo evidence attachment, cancellation modal, and details drawer with immutable post-completion addenda log.
  * `MaintenanceTasksTab.tsx`: Overdue visual highlighting (`due_date < today`), priority and category filtering, task creation modal, complete modal (mandatory notes), cancel modal (mandatory reason), and reopen modal (mandatory justification).
  * `SurvivalMonitoringTab.tsx`: Observation history table, Recharts longitudinal trajectory analytics curve, record observation modal with dynamic live preview (assessed, unassessed, observed sample survival rate), and atomic correction/supersession modal.
* [x] **Evidence Lightbox Modal (`frontend/src/views/monitoring/components/EvidenceLightboxModal.tsx`):**
  * Media lightbox with download link, GPS coordinates badge, MIME type, file size formatting, and caption.
* [x] **Scientific Rigor & Immutability:**
  * Prohibited client-side editing or submission of `survival_rate`; strictly server-derived.
  * Dynamic live preview correctly calculates assessed population, unassessed remainder, and observed sample survival rate.
  * Completed inspections locked against direct modification; post-completion changes strictly appended as immutable addenda.
  * Observation corrections executed as atomic supersessions preserving population identity and audit reasons.
* [x] **Testing & Verification:**
  * Dedicated Phase 6.5 UI logic test suite: **16/16 tests passed** in `frontend/tests/monitoring_ui.test.mjs`.
  * Full frontend test suite: **77/77 tests passed (100%) in 278ms** across 6 test suites.
  * Frontend typecheck: `tsc --noEmit` clean (code 0).
  * Frontend production build: `tsc -b && vite build` clean (code 0, 2245 modules transformed in 15.23s).
  * Full backend regression test suite: **118/118 tests passed (100%) in 51.34s**.
  * Live end-to-end service verification confirmed against running PostgreSQL, Uvicorn, and Vite instances.
  * Completion report published in `docs/PHASE_6_5_COMPLETION_REPORT.md`.
  * Architecture Decision Record published in `DECISION_LOG.md` (ADR-022).

---

## 13. Phase 6.6 Deliverables Verification

* [x] **Full Business Lifecycle Verification (`backend/tests/e2e_full_lifecycle_audit.py`):**
  * Automated end-to-end execution of all 8 lifecycle stages: `PLAN -> ASSIGN -> EXECUTE -> RECORD -> VERIFY -> MEASURE -> MONITOR`.
  * Verified project creation, multi-target allocation, and role-scoped personnel assignments.
  * Submitted field activities with geotagged photo evidence; verified content-addressed storage.
  * Verified Anti-Self-Verification Gate strictly blocks creator self-approval with HTTP 403 Forbidden.
  * Verified independent review approval, rejections with mandatory reasons, and amendment net adjustment accounting.
  * Verified activity archival: soft-delete automatically deactivates active ledger entry and rolls back official achievements.
  * Executed field inspections, immutable post-completion addenda, maintenance task workflows, and task reopening with mandatory justification.
  * Recorded survival observation with server-derived rate and performed atomic supersession with audit reason.
* [x] **Zero Environmental Contamination Verification:**
  * Confirmed that sample plot survival observations and observed sapling counts remain 100% isolated from official verified ledger achievements.
* [x] **Database & Migration Reversibility:**
  * Executed two-way migration cycle (`downgrade -1` $\to$ `upgrade head`) on `vana_test`: verified 100% clean and reversible.
  * Verified relational integrity: composite foreign keys, delete behaviors (`RESTRICT` on baseline activities, column-specific `SET NULL`), and partial unique indexes (`uq_activity_single_active_ledger`, `uq_active_survival_observation`).
* [x] **Browser Acceptance & Screenshot Capture:**
  * Executed headless Chrome DevTools Protocol automation against live backend data.
  * Captured genuine screenshots in `docs/screenshots/`:
    * `monitoring_overview.png`: KPI metrics, alert banner, and activity stream.
    * `monitoring_inspections.png`: Filterable registry and action modals.
    * `monitoring_tasks.png`: Priority/status filtering and task modals.
    * `monitoring_survival.png`: Observation registry and Recharts trajectory curve.
* [x] **Regression Suite Execution:**
  * Full backend pytest regression suite: **119/119 tests passed (100%) in 54.17s** against `vana_test`.
  * Full frontend unit & integration suite: **77/77 tests passed (100%) in 234ms** across 6 test suites.
  * Frontend TypeScript typecheck: `tsc --noEmit` clean (code 0).
  * Frontend production build: `tsc -b && vite build` clean (code 0, 2245 modules transformed in 16.00s).
* [x] **Documentation & Final Reporting:**
  * Comprehensive 14-section audit report published in `docs/PHASE_6_6_FINAL_ACCEPTANCE_REPORT.md`.
  * Final Acceptance Verdict: **PASS**.

---

## 14. Production Readiness & Deployment Blockers Deliverables Verification

* [x] **Production Readiness Audit:**
  * Completed full architectural audit across 11 domains documented in `docs/PRODUCTION_READINESS_AUDIT.md`.
  * Verdict: **READY** (All 3 Actionable Deployment Blockers Resolved and Formally Verified).
* [x] **Blocker 1 Resolution — Alembic Production Database Configuration:**
  * Cleared hardcoded localhost URL default in `backend/alembic.ini`.
  * Configured dynamic URL precedence in `backend/alembic/env.py`: `ALEMBIC_DATABASE_URL` $\to$ `settings.DATABASE_URL` $\to$ `alembic.ini`.
  * Implemented Neon asyncpg driver normalization (`postgres://` / `postgresql://` $\to$ `postgresql+asyncpg://`) and SSL query normalization (`sslmode=` $\to$ `ssl=`).
  * Enforced critical production fail-safe in `env.py` and `app/core/config.py` rejecting local/dev database connections when `ENVIRONMENT=production`.
  * Declared `ALEMBIC_DATABASE_URL` with `sync: false` in `render.yaml`.
* [x] **Blocker 2 Resolution — Secure Production Administrator Bootstrap CLI:**
  * Created standalone CLI module `backend/app/bootstrap_admin.py` executed via `python -m app.bootstrap_admin`.
  * Reads credentials strictly from environment variables: `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`, `BOOTSTRAP_ADMIN_NAME`.
  * Enforces password complexity ($\ge 12$ chars, upper, lower, digit, special char) and rejects dictionary/weak passwords.
  * Hashes credentials with Argon2id and writes immutable `USER_PROVISIONED` audit log.
  * Verified duplicate conflict protection: refuses to overwrite existing user accounts.
  * Dedicated test suite passing: **4/4 tests passed** in `backend/tests/test_bootstrap_admin.py`.
* [x] **Blocker 3 Resolution — Exact CORS Configuration & Production Validation:**
  * Hardened `validate_production_security` in `backend/app/core/config.py` to enforce non-empty `CORS_ORIGINS`, reject `*` and wildcard patterns (`*.vercel.app`) when credentials are enabled, and reject `localhost`/`127.0.0.1` origins in production.
  * Dedicated test suite passing: **7/7 tests passed** in `backend/tests/test_cors_configuration.py`.
  * Updated `.env.example`, `backend/.env.example`, and `frontend/.env.example` with documented production origins (`https://vana.earth`, `https://vana-app.vercel.app`).
* [x] **Frontend Production Environment Normalization:**
  * Added `resolveApiBaseUrl()` in `frontend/src/services/apiClient.ts` to prevent duplicate `/api/v1` segments and emit console warning if `VITE_BACKEND_URL` is omitted in production build.
  * Verified `frontend/vercel.json` SPA routing rewrite (`/(.*)` $\to$ `/index.html`).
* [x] **Full Regression & Build Verification:**
  * Backend regression suite: **130/130 tests passed (100%) in 55.92s** against `vana_test`.
  * Frontend unit/integration suite: **77/77 tests passed (100%) in 250ms**.
  * Frontend TypeScript typecheck: clean (`tsc --noEmit`, exit 0).
  * Frontend production build: clean (`tsc -b && vite build` in 15.22s, exit 0).
  * ADR published in `DECISION_LOG.md` (ADR-024).

---

## 15. Active Invariants & Scoping Boundaries

* **Single Source of Truth:** PostgreSQL database schema and constraints remain authoritative (`uq_activity_single_active_ledger`, `chk_active_ledger_verified`, `uq_active_survival_observation`, `chk_evidence_target`).
* **Anti-Self-Verification Absolute:** Rule 5 strictly enforced across backend verification services, API routers, and UI components.
* **Environmental Ledger Integrity:** Official achievements strictly reflect active verified ledger revisions only (`is_active_ledger_entry = True`).
* **Monitoring Isolation Invariant:** Monitoring observations, sample plots, and survival rates remain strictly server-derived and never contaminate official verified ledger achievements.
* **Cross-Project Isolation:** Composite foreign keys and service validation guarantee zero cross-project linkage across activities, inspections, tasks, and observations.
* **Scope Discipline Enforced:** Phase 6.6 Full Platform Acceptance is fully completed, verified, and accepted. Milestone 7 / Phase 6.7 has NOT been started and awaits explicit gate approval.
