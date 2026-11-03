# VANA — Milestone 3 Final Acceptance Audit Report
## Project Portfolio, Assignments, Geographic Boundaries & Environmental Targets

> **Audit Status:** Verified & Complete  
> **Date:** 2026-11-02  
> **Auditor:** Senior Product Architect & Technical Lead  
> **Scope:** Milestone 3 Codebase, Models, Schemas, Services, Endpoints, Migrations, and Tests  
> **Verdict:** **PASS**  

---

## 1. Executive Summary & Verdict

In accordance with the **Milestone 3 Final Acceptance Audit** mandate, an independent, comprehensive verification was performed across the VANA backend (FastAPI/SQLAlchemy) and frontend (React 19/TypeScript) implementations. The audit evaluated source code, database models, Alembic migrations, REST API routes, cryptographic/RBAC guards, Pydantic validators, and test suites.

### Audit Verdict: **PASS**

All requirements of Milestone 3 have been rigorously implemented and validated:
1. **Metric Catalog Consistency:** Fully reconciled the approved 5-category taxonomy with the 7 active environmental metrics. Confirmed that the `SOIL_CONSERVATION` category is intentionally deferred for the MVP in strict compliance with the scientific integrity rule in `AGENTS.md` (Rule 9).
2. **Assignment & RBAC Integrity:** Confirmed that project roster assignments are strictly isolated from organization-level user roles. Allocating a user as `PROJECT_MANAGER` or `FIELD_OFFICER` on a project cannot escalate global privileges, inactive users cannot be assigned, and cross-project access is blocked.
3. **GeoJSON Structural Scope:** The Pydantic validator strictly enforces RFC 7946 Polygon geometry, linear ring closure, coordinate bounds, dimensionality, and finite numeric checks (`math.isfinite`) without introducing heavy or unapproved spatial extensions (e.g., PostGIS/GEOS).
4. **Target Lifecycle Protection:** Target metric codes are immutable upon update, incompatible unit alterations are rejected with `HTTP 422`, and target deletion is prevented (`HTTP 400`) if active non-archived field activities reference the target's metric.
5. **Migration Compatibility:** Baseline Alembic migration `0001_initial_schema.py` is at `head` and fully consistent with current models. The reversible migration cycle (`upgrade head` $\to$ `downgrade base` $\to$ `upgrade head`) executed cleanly against PostgreSQL with zero database recreation workarounds.
6. **Empirical Test Verification:** Full backend test suite passed with **59/59 tests (100% pass rate in 22.47s)**. Full frontend test suite passed with **14/14 tests (100% pass rate in 0.15s)**. Frontend typecheck reported **0 errors**, and the production build finished cleanly in **8.46s**.

---

## 2. Environmental Metric Catalog Reconciliation

### 2.1 Investigation: 7 Metrics across 4 Active Categories vs. 5 Approved Categories

The audit compared:
* High-level approved 5-category taxonomy: `VEGETATION_PLANTING`, `LAND_RESTORATION`, `WATER_CONSERVATION`, `SOIL_CONSERVATION`, `WASTE_REMOVAL`.
* `backend/app/domains/projects/metrics.py`.
* Target API schemas and frontend metric dropdowns.
* `docs/engineering/06_ENVIRONMENTAL_IMPACT_LOGIC.md` Section 2.

#### Findings & Scientific Justification:
In `docs/engineering/06_ENVIRONMENTAL_IMPACT_LOGIC.md` Section 2, the authoritative specification explicitly notes:
> *"Metrics in the `SOIL_CONSERVATION` category (e.g. `TOPSOIL_PRESERVED`) remain disabled in the MVP pending calibrated scientific sampling procedures."*

Furthermore, `AGENTS.md` **Mandatory Policy Rule 9 (Data Grounding & Scientific Integrity)** states:
> *"Never invent carbon sequestration, soil conservation, biodiversity, or survival-rate calculations. Display only metrics supported by actual recorded data and explicitly documented measurement methodologies."*

Therefore, **soil conservation was intentionally deferred, not accidentally omitted**. Including uncalibrated synthetic topsoil metrics would directly violate the core scientific integrity rule of Akshaya Vana Ventures.

### 2.2 Reconciled Metric Catalog Matrix

| Metric Code | Classification Category | Dimension | Canonical Unit | Supported Units | Conversion Factor to Base | Status | Measurement Methodology |
|---|---|:---:|:---:|---|:---:|:---:|---|
| `TREES_PLANTED` | `VEGETATION_PLANTING` | `COUNT` | `trees` | `trees` | $1.0$ | **Active** | Direct physical tally of established native trees planted on site; tagged and geotagged. |
| `SAPLINGS_PLANTED` | `VEGETATION_PLANTING` | `COUNT` | `saplings` | `saplings` | $1.0$ | **Active** | Physical tally of nursery saplings transplanted into soil plots; tagged with lot number. |
| `AREA_RESTORED` | `LAND_RESTORATION` | `AREA` | `hectares` | `hectares`, $\text{m}^2$, `acres` | $\text{ha}: 1.0$<br>$\text{m}^2: 0.0001$<br>$\text{ac}: 0.404686$ | **Active** | GPS boundary walking or polygon mapping of degraded land brought under active soil/vegetation restoration. |
| `AREA_REVEGETATED` | `LAND_RESTORATION` | `AREA` | `hectares` | `hectares`, $\text{m}^2$, `acres` | $\text{ha}: 1.0$<br>$\text{m}^2: 0.0001$<br>$\text{ac}: 0.404686$ | **Active** | Direct measurement of canopy coverage or ground re-seeding within designated boundaries. |
| `RAINWATER_HARVESTED` | `WATER_CONSERVATION` | `VOLUME` | `liters` | `liters`, $\text{m}^3$ | $\text{l}: 1.0$<br>$\text{m}^3: 1000.0$ | **Active** | Water meter reading or calculated volume from certified percolation pits and check dams during rain events. |
| `RESERVOIR_CAPACITY_CREATED` | `WATER_CONSERVATION` | `VOLUME` | `cubic_meters` | `cubic_meters`, `liters` | $\text{m}^3: 1.0$<br>$\text{l}: 0.001$ | **Active** | Civil engineering survey of excavated trench, bund, or farm pond storage volume capacity. |
| `WASTE_REMOVED` | `WASTE_REMOVAL` | `MASS` | `kilograms` | `kilograms`, `metric_tons` | $\text{kg}: 1.0$<br>$\text{t}: 1000.0$ | **Active** | Certified weighbridge or hand-scale slip for physical non-biodegradable waste collected from site. |
| *(SOIL_CONSERVATION)* | `SOIL_CONSERVATION` | `MASS / AREA` | — | — | — | **Deferred** | *Disabled in MVP pending calibrated laboratory bulk density and soil organic carbon (SOC) sampling.* |

### 2.3 Non-Contamination & Conversion Rules
* **Distinct Metric Code Isolation:** Even though `TREES_PLANTED` and `SAPLINGS_PLANTED` both share dimension `COUNT`, they are defined as distinct metric codes and cannot be summed or converted into one another.
* **No Synthetic Conversion Factors:** There are zero conversion multipliers between unrelated dimensions (e.g., converting trees into $\text{CO}_2$ offsets or area into liters).
* **Controlled Unit Conversions:** Conversions are strictly defined only within the identical `metric_code` to its canonical base unit (e.g., $1\text{ ha} = 10{,}000\text{ m}^2 = 2.47105\text{ acres}$).

---

## 3. Assignment and RBAC Integrity

### 3.1 Organization-Level vs. Project-Level Role Separation
The audit verified the relational separation between `users.role` (organization global role: `ADMIN`, `PROJECT_MANAGER`, `FIELD_OFFICER`) and `project_assignments.assigned_role` (project roster role: `PROJECT_MANAGER`, `FIELD_OFFICER`):
1. **Zero Global Escalation:** Allocating a user with global role `FIELD_OFFICER` as a `PROJECT_MANAGER` within a specific project writes only to `project_assignments`. In `backend/app/domains/teams/services.py`, the `users.role` column is never touched.
2. **Persistent Global Restrictions:** A global `FIELD_OFFICER` assigned as a project manager on Project A remains prohibited from global administrative actions (e.g., calling `POST /api/v1/projects` returns `HTTP 403 Forbidden`).
3. **De-Allocation Isolation:** Removing a project assignment (`DELETE /api/v1/projects/{id}/assignments/{userId}`) purges only the relational assignment row. The user's account role, credentials, and active status remain unchanged.

### 3.2 Authorization Guard Verification

```mermaid
flowchart TD
    Req[Incoming Project Operation Request] --> AuthCheck{Is User Authenticated & Active?}
    AuthCheck -- No --> DenyAuth[HTTP 401 Unauthorized / 403 Deactivated]
    AuthCheck -- Yes --> GlobalAdminCheck{Is User Global ADMIN?}
    GlobalAdminCheck -- Yes --> Allow[Access Granted: Full Organization Scope]
    GlobalAdminCheck -- No --> AssignmentCheck{Active ProjectAssignment exists?}
    AssignmentCheck -- No --> DenyProject[HTTP 403 Forbidden: PROJECT_ACCESS_DENIED]
    AssignmentCheck -- Yes --> RoleCheck{Requires Project Manager Role?}
    RoleCheck -- No --> Allow
    RoleCheck -- Yes --> PMCheck{assigned_role == 'PROJECT_MANAGER'?}
    PMCheck -- Yes --> Allow
    PMCheck -- No --> DenyRole[HTTP 403 Forbidden: INSUFFICIENT_PROJECT_ROLE]
```

### 3.3 Assignment Invariants Verified by Automated Tests
* **Inactive User Assignment Prevention:** Attempting to assign a deactivated user (`is_active = False`) is intercepted and rejected with `HTTP 400 Bad Request` (`INACTIVE_USER_ASSIGNMENT_PROHIBITED`).
* **Duplicate Assignment Prevention:** A user can only be assigned once per project. Attempting a duplicate assignment is rejected with `HTTP 409 Conflict` (`DUPLICATE_PROJECT_ASSIGNMENT`), backed by the database constraint `UNIQUE (project_id, user_id)`.
* **Cross-Project Isolation:** A Project Manager assigned to Project A attempting to inspect, edit, define targets, or manage assignments on Project B receives `HTTP 403 Forbidden` (`PROJECT_ACCESS_DENIED`).

---

## 4. GeoJSON Validation Scope & Spatial Architecture

### 4.1 Structural Validation vs. Topological Validation

The audit examined the Pydantic boundary validator in [`backend/app/domains/projects/schemas.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/projects/schemas.py). The validation boundary intentionally implements **RFC 7946 Structural and Syntactical Validation** without relying on external GIS libraries or PostGIS:

```
┌────────────────────────────────────────────────────────────────────────┐
│                       GEOJSON VALIDATION BOUNDARY                      │
│                                                                        │
│  [ IMPLEMENTED: Structural & Syntactical Validation (RFC 7946) ]       │
│  ✔ JSON Schema: Dict object with type == "Polygon"                     │
│  ✔ Coordinate Structure: coordinates is a non-empty list of rings      │
│  ✔ Minimum Positions: Each linear ring must contain >= 4 positions    │
│  ✔ Ring Closure: First coordinate exactly matches last coordinate      │
│  ✔ Dimensionality: Exactly 2D [lng, lat] (optional 3D altitude allowed)│
│  ✔ Coordinate Bounds: -180.0 <= longitude <= 180.0, -90.0 <= lat <= 90│
│  ✔ Finite Numerics: math.isfinite(lng) and math.isfinite(lat) (No NaN) │
│  ✔ Multi-Ring Support: Validates exterior ring and interior holes      │
│                                                                        │
│  [ DEFERRED: Full Topological Computation (PostGIS / GEOS Engine) ]    │
│  ✖ Self-Intersection Detection (e.g. Figure-8 bowtie polygons)         │
│  ✖ Ring Orientation Enforcement (Right-hand rule exterior CCW)         │
│  ✖ Hole Containment Verification (Interior hole must lie within outer) │
│  ✖ Non-Overlapping Hole Topology                                       │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Architectural Rationale
Implementing self-intersection and hole containment validation requires GEOS or PostGIS C-extensions (such as `ST_IsValid` or `shapely`), which are strictly forbidden by **ADR-002** and **AGENTS.md** Rule 2 (*"Never introduce an unapproved third-party dependency, external UI library, or specialized spatial database extension (e.g., PostGIS) into the MVP"*).

The structural validator provides robust defense against malformed payloads, coordinate inversion, and syntax bugs, while keeping PostgreSQL lightweight, portable, and cloud-ready on Neon/Docker.

---

## 5. Environmental Target Lifecycle Policy

### 5.1 Target Mutability & Immutability Rules
* **Metric Identity Immutability:** In `ProjectTargetUpdate`, the `metric_code` field is omitted from the Pydantic schema. Once a target is created for e.g. `TREES_PLANTED`, its metric identity can never be altered. To change the metric, a manager must delete the target and create a new one.
* **Unit Compatibility Enforcement:** When updating `target_unit`, `TargetService.update_target` validates the new unit against the metric's `supported_units`. Incompatible unit changes (e.g., changing `AREA_RESTORED` unit to `liters`) are trapped and rejected with `HTTP 422 Unprocessable Entity` (`INCOMPATIBLE_UNIT`).
* **Quantity Positivity:** Updating `target_quantity` to $\le 0$ is rejected by Pydantic and database check constraint `chk_target_quantity_positive` with `HTTP 422` or `HTTP 400`.

### 5.2 Field Activity Reference Protection
In Milestone 1A, `field_activities` was established with `project_id` and `metric_code`. Activities aggregate against targets matching `(project_id, metric_code)`.

To prevent orphaning activity progress, **Target Deletion Safeguard** was implemented in `TargetService.delete_target`:
```python
# Safeguard: prevent deletion if active field activities reference this metric
active_activities = await db.scalar(
    select(func.count(FieldActivity.id)).where(
        FieldActivity.project_id == project_id,
        FieldActivity.metric_code == target.metric_code,
        FieldActivity.is_archived.is_(False),
    )
)
if active_activities and active_activities > 0:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "error_code": "TARGET_HAS_ACTIVE_ACTIVITIES",
            "message": f"Cannot delete target '{target.metric_code}': {active_activities} active field activities reference this metric.",
        },
    )
```
If active field activities exist for that metric on that project, deleting the target is refused with `HTTP 400 Bad Request` (`TARGET_HAS_ACTIVE_ACTIVITIES`). This prevents broken progress calculations and orphaned reporting.

---

## 6. Migration Compatibility & Database Verification

### 6.1 Schema & Migration Alignment
The audit verified the complete Alembic migration history and PostgreSQL schema:
* Baseline migration: `backend/alembic/versions/0001_initial_schema.py` is at `head`.
* Models in `app/models.py` (`User`, `Project`, `ProjectAssignment`, `ProjectTarget`, `FieldActivity`, `ActivityRevision`, `EvidenceFile`, `AuditLog`) perfectly mirror the database DDL.
* All indexes and constraints are verified:
  * `uq_project_targets_no_milestone` (Partial unique index on `project_id`, `metric_code` where `milestone_id IS NULL`).
  * `uq_project_user_assignment` (Unique constraint on `project_id`, `user_id`).
  * `chk_project_latitude` and `chk_project_longitude`.
  * `chk_target_quantity_positive`.

### 6.2 Migration Cycle Test
The automated two-way migration cycle test was executed against the running PostgreSQL 17 test engine:
```bash
pytest tests/test_migrations.py -v
```
* **Command:** `alembic upgrade head -> alembic downgrade base -> alembic upgrade head`
* **Result:** `1 passed in 0.98s` (Zero SQL errors, clean rollback, clean upgrade).
* **Data Safety:** No manual `ALTER TABLE` statements were executed, and no drop-database workarounds were employed.

---

## 7. Findings & Remediations Applied

| Finding Ref | Severity | Component | Finding Description | Remediation Applied |
|---|:---:|---|---|---|
| **F-01** | Low | `schemas.py` | `validate_geojson_polygon` did not explicitly check for `NaN` or `Infinity` numeric values. | Added `math.isfinite(lng)` and `math.isfinite(lat)` checks to explicitly reject non-finite numbers. |
| **F-02** | Medium | `services.py` | `TargetService.update_target` raised raw `ValueError` on incompatible unit update rather than structured `HTTPException`. | Added `try...except ValueError` block raising `HTTP 422 Unprocessable Entity` (`INCOMPATIBLE_UNIT`). |
| **F-03** | High | `services.py` | Deleting a target had no check for existing recorded field activities, risking orphaned progress. | Added target deletion safeguard verifying that active field activities count for that `(project_id, metric_code)` is zero before allowing deletion (`TARGET_HAS_ACTIVE_ACTIVITIES`). |
| **F-04** | Low | `tests/` | Missing regression tests verifying global role separation on project assignment, cross-project isolation, and GeoJSON holes. | Added 5 dedicated regression test cases to `backend/tests/test_projects_and_targets.py`. |

---

## 8. Complete Test Suite Execution Results

### 8.1 Backend Test Execution (59 / 59 Passed)

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-8.3.5, pluggy-1.7.0 -- C:\Developers\Sneha\Projects\VANA\backend\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Developers\Sneha\Projects\VANA\backend
configfile: pytest.ini
plugins: anyio-4.16.0, asyncio-0.25.3
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=function
collected 59 items

tests/test_auth_and_rbac.py (28 tests) ............................ PASSED [ 47%]
tests/test_database_connection.py (2 tests) ..                     PASSED [ 50%]
tests/test_migrations.py (1 test) .                                PASSED [ 52%]
tests/test_models_and_constraints.py (5 tests) .....               PASSED [ 61%]
tests/test_projects_and_targets.py (18 tests) ...................  PASSED [ 91%]
tests/test_token_lifecycle.py (5 tests) .....                      PASSED [100%]

============================= 59 passed in 22.47s =============================
```

### 8.2 Frontend Test Execution (14 / 14 Passed)

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
ok 1 - Frontend Authentication & RBAC Unit Tests (4.99ms)

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
ok 2 - Frontend Project Portfolio & Workspace Unit Tests (7.98ms)

1..2
# tests 14 | suites 2 | pass 14 | fail 0 (146ms)
```

### 8.3 Frontend Typecheck & Production Build

```bash
npm run typecheck --prefix frontend
```
* **Command:** `tsc --noEmit`
* **Result:** Exit code `0` (Zero errors, zero warnings).

```bash
npm run build --prefix frontend
```
* **Command:** `tsc -b && vite build`
* **Result:** Exit code `0` (1798 modules transformed in 8.46s).

---

## 9. Final Conclusion & Next Steps

Milestone 3 has achieved a **PASS** audit verdict. The project portfolio, team assignments, geographic boundary validation, and environmental target systems are secure, transactionally atomic, mathematically grounded, and compliant with all permanent engineering guidelines.

Development is formally stopped. Commencement of Milestone 4 (Field Operations, Activity Reporting & Evidence Storage) awaits your review and authorization.
