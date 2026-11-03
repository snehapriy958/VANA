# VANA — Milestone 3 Completion Report
## Project Portfolio, Assignments, Geographic Boundaries & Environmental Targets

> **Status:** Completed & Verified  
> **Date:** 2026-11-02  
> **Milestone:** 3  
> **Related Documents:** `AGENTS.md`, `DECISION_LOG.md` (ADR-003, ADR-005, ADR-007, ADR-009, ADR-015), `IMPLEMENTATION_STATUS.md`  

---

## 1. Executive Summary

Milestone 3 has been fully implemented, integrated, and verified against real PostgreSQL transactions and the React 19 frontend application. The platform now delivers end-to-end management for environmental conservation initiatives, project team allocations, geographic coordinates and boundary polygons, and dimensional environmental targets anchored to an authoritative scientific catalog.

All changes adhere strictly to the modular monolith architecture, role-based security boundaries (`ADMIN`, `PROJECT_MANAGER`, `FIELD_OFFICER`), and permanent engineering invariants defined in `AGENTS.md`.

* **Backend Verification:** **54/54 tests passed (100% pass rate in 19.10s)** across all foundation, authentication, token lifecycle, and project/target test modules.
* **Frontend Verification:** **14/14 unit tests passed (100% pass rate in 0.17s)**; TypeScript typecheck reported **0 errors**; production build completed cleanly (**1798 modules transformed in 8.70s**).

---

## 2. Implemented Endpoints & REST Architecture

All endpoints are mounted under `/api/v1` and protected by independent server-side JWT authentication and RBAC dependency guards.

### 2.1 Project Portfolio Management (`/api/v1/projects`)

| Method | Endpoint | Allowed Roles | Description | Status Codes |
|---|---|:---:|---|:---:|
| `POST` | `/api/v1/projects` | `ADMIN` | Creates a new environmental project with center coordinates, uppercase code, and optional GeoJSON polygon. | `201`, `400`, `403`, `409`, `422` |
| `GET` | `/api/v1/projects` | `ADMIN`, `PM`, `FIELD_OFFICER` | Scoped portfolio listing. `ADMIN` sees all projects; `PM` and `FIELD_OFFICER` see only assigned projects. Supports `search` and `status` query filters. | `200`, `401` |
| `GET` | `/api/v1/projects/{id}` | `ADMIN`, Assigned `PM`, Assigned `FO` | Retrieves full project workspace details, including target balance sheets and team rosters. | `200`, `401`, `403`, `404` |
| `PUT` | `/api/v1/projects/{id}` | `ADMIN`, Assigned `PM` | Updates project metadata, coordinates, boundary polygon, and lifecycle status with strict transition checks. | `200`, `400`, `401`, `403`, `404`, `422` |

### 2.2 Project Team Allocations (`/api/v1/projects/{id}/assignments`)

| Method | Endpoint | Allowed Roles | Description | Status Codes |
|---|---|:---:|---|:---:|
| `POST` | `/api/v1/projects/{id}/assignments` | `ADMIN`, Assigned `PM` | Allocates an active user to the project roster as `PROJECT_MANAGER` or `FIELD_OFFICER`. Rejects inactive users and prevents duplicates. | `201`, `400`, `401`, `403`, `404`, `409` |
| `GET` | `/api/v1/projects/{id}/assignments` | `ADMIN`, Assigned `PM`, Assigned `FO` | Lists all team personnel allocated to this project roster with user profile details. | `200`, `401`, `403`, `404` |
| `DELETE` | `/api/v1/projects/{id}/assignments/{userId}` | `ADMIN`, Assigned `PM` | Removes a user from the project's active roster. | `204`, `401`, `403`, `404` |

### 2.3 Environmental Targets & Catalog (`/api/v1/projects/{id}/targets` & `/api/v1/metrics`)

| Method | Endpoint | Allowed Roles | Description | Status Codes |
|---|---|:---:|---|:---:|
| `POST` | `/api/v1/projects/{id}/targets` | `ADMIN`, Assigned `PM` | Attaches a dimensional environmental target. Validates unit compatibility and prevents duplicate active targets for the same metric. | `201`, `400`, `401`, `403`, `404`, `409`, `422` |
| `GET` | `/api/v1/projects/{id}/targets` | `ADMIN`, Assigned `PM`, Assigned `FO` | Lists dimensional targets enriched with category, dimension, and canonical unit. | `200`, `401`, `403`, `404` |
| `PUT` | `/api/v1/projects/{id}/targets/{targetId}` | `ADMIN`, Assigned `PM` | Updates target quantity, unit, or completion deadline. | `200`, `400`, `401`, `403`, `404`, `422` |
| `DELETE` | `/api/v1/projects/{id}/targets/{targetId}` | `ADMIN`, Assigned `PM` | Deletes a dimensional target. | `204`, `401`, `403`, `404` |
| `GET` | `/api/v1/metrics/catalog` | Authenticated | Exposes the approved environmental metric catalog for dynamic frontend target configuration. | `200`, `401` |

---

## 3. Database Schema & Migration Status

Milestone 3 leverages the approved schema tables committed in Milestone 1A:
1. `projects`: `id`, `name`, `code` (UNIQUE), `description`, `status`, `latitude`, `longitude`, `boundary_geojson` (JSONB), `created_at`, `updated_at`.
2. `project_assignments`: `id`, `project_id` (FK), `user_id` (FK), `assigned_role`, `assigned_at`, with `UNIQUE (project_id, user_id)`.
3. `project_targets`: `id`, `project_id` (FK), `metric_code`, `target_quantity` (> 0), `target_unit`, `target_date`, `milestone_id` (reserved for Phase 2), with partial unique index `uq_project_targets_no_milestone` on `(project_id, metric_code) WHERE milestone_id IS NULL`.
4. `audit_logs`: Immutable audit log capturing state diffs.

No manual `ALTER TABLE` commands were executed; the existing Alembic migration `0001_initial_schema.py` remains authoritative and 100% reversible.

---

## 4. Role Authorization & Scoping Boundaries

* **Organization-Wide Authority (`ADMIN`):**
  * Create new environmental projects.
  * View, update, or archive any project across the organization.
  * Allocate or remove any active user across any project roster.
  * Define, update, or delete environmental targets on any project.
* **Scoped Project Management (`PROJECT_MANAGER`):**
  * Portfolio listing is strictly scoped to projects where the PM has an active assignment in `project_assignments`.
  * Cannot create new projects.
  * Can edit project metadata, coordinates, and boundaries for assigned projects.
  * Can manage team assignments (assign Field Officers or fellow PMs) for assigned projects.
  * Can define, update, and remove environmental targets for assigned projects.
* **Field Personnel (`FIELD_OFFICER`):**
  * Portfolio listing is strictly scoped to projects where the Field Officer has an active assignment.
  * Can view project workspace, assigned team members, environmental targets, and geographic coordinates.
  * Strictly blocked (`HTTP 403 Forbidden`) from creating projects, editing projects, modifying rosters, or defining targets.
* **Assignment Invariant:**
  * Deactivated users (`is_active == False`) are strictly prohibited from being allocated to project rosters (`HTTP 400 Bad Request`, `INACTIVE_USER_ASSIGNMENT_PROHIBITED`).
  * Duplicate allocations for the same user on the same project are rejected (`HTTP 409 Conflict`, `DUPLICATE_PROJECT_ASSIGNMENT`).

---

## 5. Environmental Target Design & Scientific Integrity

In strict adherence to **ADR-003** and **ADR-015**, VANA prevents greenwashing and mathematical corruption:

### Approved Metric Catalog (`app/domains/projects/metrics.py`)

| Metric Code | Category | Dimension | Canonical Unit | Supported Units | Conversion Factor to Base |
|---|---|:---:|:---:|---|:---:|
| `TREES_PLANTED` | `VEGETATION_PLANTING` | `COUNT` | `trees` | `trees` | $1.0$ |
| `SAPLINGS_PLANTED` | `VEGETATION_PLANTING` | `COUNT` | `saplings` | `saplings` | $1.0$ |
| `AREA_RESTORED` | `LAND_RESTORATION` | `AREA` | `hectares` | `hectares`, `m2`, `acres` | $\text{ha}: 1.0, \text{m}^2: 0.0001, \text{ac}: 0.404686$ |
| `AREA_REVEGETATED` | `LAND_RESTORATION` | `AREA` | `hectares` | `hectares`, `m2`, `acres` | $\text{ha}: 1.0, \text{m}^2: 0.0001, \text{ac}: 0.404686$ |
| `RAINWATER_HARVESTED` | `WATER_CONSERVATION` | `VOLUME` | `liters` | `liters`, `m3` | $\text{l}: 1.0, \text{m}^3: 1000.0$ |
| `RESERVOIR_CAPACITY_CREATED` | `WATER_CONSERVATION` | `VOLUME` | `cubic_meters` | `cubic_meters`, `liters` | $\text{m}^3: 1.0, \text{l}: 0.001$ |
| `WASTE_REMOVED` | `WASTE_REMOVAL` | `MASS` | `kilograms` | `kilograms`, `metric_tons` | $\text{kg}: 1.0, \text{t}: 1000.0$ |

### Mathematical Invariants:
1. **Zero Cross-Metric Aggregation:** Different metric codes are never aggregated together.
2. **Strict Unit Compatibility:** Units must strictly belong to the metric's approved `supported_units`. Attempting to register `trees` in `liters` or `hectares` in `kilograms` is rejected with `HTTP 422 Unprocessable Entity`.
3. **No Synthetic Achievement:** Target creation establishes the goal baseline only; it does not generate synthetic progress or default verified achievements.
4. **Duplicate Prevention:** A project can have at most one active target per `metric_code`. Attempted duplicates trigger `HTTP 409 Conflict` (`DUPLICATE_PROJECT_TARGET`).

---

## 6. Geographic Boundaries & Validation

In accordance with **ADR-005**:
* Coordinates are represented natively as `DOUBLE PRECISION` (`latitude` and `longitude`) with standard range checks:
  * Latitude: $-90.0 \le \text{lat} \le 90.0$
  * Longitude: $-180.0 \le \text{lng} \le 180.0$
* Optional boundary polygons are validated against RFC 7946 GeoJSON Polygon specifications in Pydantic:
  * Geometry type must be `"Polygon"`.
  * Rings must contain at least 4 coordinate pairs.
  * Linear ring closure is strictly enforced: `first_point == last_point`.
  * Every coordinate pair is validated within numeric range bounds `[longitude, latitude]`.
* Zero PostGIS or external C-spatial libraries were introduced, preserving pure PostgreSQL relational portability.

---

## 7. Frontend Screens & User Experience

Built on React 19, TypeScript, Tailwind CSS, and shadcn/ui:

### 1. Project Portfolio (`/projects`)
* **Live Registry:** Dynamic search bar and status filter buttons (`ALL`, `ACTIVE`, `DRAFT`, `COMPLETED`, `ARCHIVED`).
* **Display Modes:** Toggleable between Card Grid View and Dense Data Table View.
* **Card Details:** Code badge, Status pill, Project Name, Description, Latitude/Longitude coordinates, Target count, Staff count, "Open Workspace" action button.
* **Creation Wizard:** Accessible to `ADMIN` only; modal dialog with validation for Name, Code, Description, Status, Coordinates, and optional GeoJSON boundary string.
* **Resilience:** Handles animated skeleton loading, empty state, and error retries.

### 2. Project Workspace (`/projects/:projectId`)
* **Hero Banner:** Breadcrumb trail, project name, uppercase code, status pill, centroid coordinates, and "Edit Project" button for administrators and assigned PMs.
* **Interactive Tabs:**
  1. **Overview:** Initiative scope, governing standard alert, dimensional target balance summary, project leadership card, and centroid coordinate details.
  2. **Environmental Targets:** Grid of dimensional target cards detailing metric category, dimension, target quantity, unit, deadline date, and Edit/Delete controls. "Add Target" modal with dynamic metric selection and unit filtering.
  3. **Team Roster:** Table of allocated personnel detailing full name, email, project role badge, system role, active status, assignment date, and "Remove" control. "Assign Team Member" modal selecting from active organization personnel.
  4. **Geographic Information:** Detailed coordinate inspection, boundary status (Polygon Defined vs Point Only), vertex count, and raw GeoJSON viewer with copy-to-clipboard functionality.

---

## 8. Audit Logging Verification

Every mutation commits an immutable record to PostgreSQL `audit_logs` with sanitized state diffs:
* `PROJECT_CREATED`: Logs project ID, name, code, status, coordinates, and boundary flag.
* `PROJECT_UPDATED`: Captures `previous_state` and `new_state` diffs.
* `PROJECT_STATUS_CHANGED`: Dedicated audit record tracking lifecycle progression.
* `TARGET_CREATED`: Logs metric code, quantity, unit, and deadline.
* `TARGET_UPDATED`: Captures target adjustment diffs.
* `TARGET_DELETED`: Archives deleted target parameters before removal.
* `ASSIGNMENT_CREATED`: Logs allocated user, role, and timestamp.
* `ASSIGNMENT_DELETED`: Records personnel removal.

All credentials and sensitive keys remain completely sanitized (`sanitize_state`).

---

## 9. Verification Tests & Commands

### 9.1 Backend Test Execution

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-8.3.5, pluggy-1.7.0 -- C:\Developers\Sneha\Projects\VANA\backend\.venv\Scripts\python.exe
rootdir: C:\Developers\Sneha\Projects\VANA\backend
configfile: pytest.ini
plugins: anyio-4.16.0, asyncio-0.25.3
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=function
collected 54 items

tests/test_auth_and_rbac.py (28 tests) ............................ PASSED [ 51%]
tests/test_database_connection.py (2 tests) ..                     PASSED [ 55%]
tests/test_migrations.py (1 test) .                                PASSED [ 57%]
tests/test_models_and_constraints.py (5 tests) .....               PASSED [ 66%]
tests/test_projects_and_targets.py (13 tests) .............        PASSED [ 90%]
tests/test_token_lifecycle.py (5 tests) .....                      PASSED [100%]

============================= 54 passed in 19.10s =============================
```

### 9.2 Frontend Test Execution

```bash
npm test --prefix frontend
```

```text
> vana-frontend@0.1.0 test
> node --test tests/*.test.mjs

TAP version 13
# Subtest: Frontend Authentication & RBAC Unit Tests
    ok 1 - validates correct login credentials format
    ok 2 - rejects invalid email in login schema
    ok 3 - rejects empty password in login schema
    ok 4 - enforces minimum 8 characters on provisioning password
    ok 5 - correctly filters role-aware navigation
    1..5
ok 1 - Frontend Authentication & RBAC Unit Tests (4.53ms)

# Subtest: Frontend Project Portfolio & Workspace Unit Tests
    ok 1 - validates valid project creation inputs
    ok 2 - rejects invalid project name shorter than 3 characters
    ok 3 - rejects latitude outside range [-90, 90]
    ok 4 - rejects longitude outside range [-180, 180]
    ok 5 - validates GeoJSON polygon structure and closed rings
    ok 6 - validates environmental target creation inputs
    ok 7 - rejects zero or negative target quantity
    ok 8 - validates project assignment input schema
    ok 9 - enforces role-based permissions in Project Workspace UI
    1..9
ok 2 - Frontend Project Portfolio & Workspace Unit Tests (7.25ms)

1..2
# tests 14
# suites 2
# pass 14
# fail 0
```

### 9.3 Frontend Typecheck & Production Build

```bash
npm run typecheck --prefix frontend
```
* **Result:** Exit code `0` (Zero TypeScript diagnostics).

```bash
npm run build --prefix frontend
```
* **Result:** Exit code `0` (`tsc -b && vite build` transformed 1798 modules in 8.70s).

---

## 10. Scope Boundaries & Remaining Limitations

1. **Deferred Offline Sync:** Mobile field reporting remains an online-first web interface; offline IndexedDB sync is scheduled for Phase 2 (ADR-008).
2. **Interactive Map Canvas:** Full React Leaflet layer controls, vector tile renderers, and spatial clustering are reserved for Milestone 7 (Living Earth Map). Milestone 3 displays centroid coordinates, RFC 7946 GeoJSON geometry metadata, and boundary specifications.
3. **No Field Submissions in M3:** Field activity reporting, photo evidence uploads, verification queues, and official recalculation engines remain un-implemented and isolated for Milestones 4, 5, and 6.

---

## 11. Final Recommendation

Milestone 3 is complete, fully tested, and ready for user review. Development is halted pending authorization for Milestone 4 (Field Operations, Activity Reporting & Evidence Storage).
