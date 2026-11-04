# VANA Phase 6 — Field Monitoring & Follow-up Management: Acceptance Criteria

> **Document Status:** Final Gate Approved with Database Integrity Corrections\
> **Target Release:** VANA Phase 6 (Milestone 6)\
> **Scope:** Testable acceptance criteria, Given-When-Then behavioral specifications, and verification scenarios.\
> **Traceability:** Aligns with `AGENTS.md` (Rules 1, 4, 6, 7, 8, 9), `docs/PHASE_6_FINAL_IMPLEMENTATION_GATE.md`.

---

## 1. Domain 1: Field Inspection Lifecycle & Evidence Retention

### AC-INS-01: Scheduled Inspection Creation with Assignment Validation
* **Given** an authenticated user with `ADMIN` or `PROJECT_MANAGER` role assigned to Project $P$,
* **When** they submit `POST /api/v1/monitoring/inspections` with `project_id`, `scheduled_date`, `inspection_type`, and `assigned_to_id`,
* **Then**:
  * The backend verifies that `assigned_to_id` is an active member of Project $P$ in `project_assignments`.
  * If valid, an inspection is created in `SCHEDULED` status (`201 Created`).
  * If the user is not an active team member of Project $P$, the request is rejected with `400 Bad Request` (`detail: "Assigned inspector is not an active team member of this project"`).

### AC-INS-02: Cross-Project Reference Protection (Composite Foreign Key)
* **Given** an inspection creation payload referencing `linked_activity_id`,
* **When** the referenced activity belongs to Project $B$ while `project_id` is Project $A$,
* **Then**:
  * The request is rejected with `400 Bad Request` (`detail: "Cross-project reference violation: linked activity does not belong to the specified project"`).
  * If attempted directly at the database layer, the composite foreign key `(linked_activity_id, project_id) REFERENCES field_activities(id, project_id)` rejects the transaction.

### AC-INS-03: Composite Foreign Key Deletion Behavior (Column-Specific SET NULL)
* **Given** an inspection $I_1$ with `project_id = P` and `linked_activity_id = A_1`,
* **When** activity $A_1$ is deleted from `field_activities`,
* **Then**:
  * The composite constraint `ON DELETE SET NULL (linked_activity_id)` sets `I_1.linked_activity_id` to `NULL`.
  * `I_1.project_id` remains strictly $P$ and is **never** nullified.
  * No `NOT NULL` constraint violation occurs.

### AC-INS-04: Inspector Ownership & State Transition (`SCHEDULED` $\to$ `IN_PROGRESS`)
* **Given** an inspection in `SCHEDULED` status assigned to Field Officer $U_1$,
* **When** Field Officer $U_2$ (not assigned) attempts to start the inspection via `POST /api/v1/monitoring/inspections/{id}/start`,
* **Then**:
  * The server rejects with `403 Forbidden` (`detail: "Field Officers may only modify inspections assigned to them"`).
* **When** assigned Field Officer $U_1$, or a Project Manager of Project $P$, submits the request,
* **Then**:
  * Status transitions to `IN_PROGRESS` (`200 OK`).
  * Audit log records `MONITORING_INSPECTION_STARTED`.

### AC-INS-05: Inspection Completion & Record Locking
* **Given** an inspection in `IN_PROGRESS` status,
* **When** the assigned inspector or PM submits `POST /api/v1/monitoring/inspections/{id}/complete` with findings and vegetation health score (1–5),
* **Then**:
  * Status transitions to `COMPLETED` and `completed_at` is stamped.
  * Audit log records `MONITORING_INSPECTION_COMPLETED`.
* **When** any user attempts a subsequent `PATCH` or update on this completed inspection,
* **Then**:
  * The request is rejected with `400 Bad Request` ("Completed inspections cannot be modified").

### AC-INS-06: Post-Completion Correction Addenda
* **Given** an inspection in `COMPLETED` status,
* **When** a PM or Admin submits `POST /api/v1/monitoring/inspections/{id}/addendum` with correction details,
* **Then**:
  * The addendum is appended to `field_inspections.addenda` with author and timestamp.
  * Historical findings and initial scores remain unaltered.
  * Audit log records `MONITORING_INSPECTION_ADDENDUM_RECORDED`.

### AC-INS-07: Evidence Retention Under Deletion Restriction
* **Given** an inspection with uploaded evidence files in `evidence_files`,
* **When** a database deletion is attempted on `field_inspections`,
* **Then**:
  * The database rejects deletion due to `ON DELETE RESTRICT` on `evidence_files.inspection_id`.
  * Evidence files and inspection records are preserved for audit.

---

## 2. Domain 2: Maintenance Task Lifecycle & State Machine

### AC-TSK-01: Task Creation with Composite Foreign Keys
* **Given** an authorized PM or Admin,
* **When** submitting `POST /api/v1/monitoring/tasks` with valid project, category, priority, and due date,
* **Then**:
  * If `inspection_id` or `activity_id` is supplied, it must belong to the same `project_id`. Cross-project IDs are rejected with `400 Bad Request`.
  * Task is created with status `TODO` (`201 Created`).
  * Audit log records `MONITORING_TASK_CREATED`.

### AC-TSK-02: Task Progression (`TODO` $\to$ `IN_PROGRESS` $\to$ `COMPLETED`)
* **Given** a task in `TODO` status assigned to user $U$,
* **When** user $U$ or PM posts to `/api/v1/monitoring/tasks/{id}/start`,
* **Then**: Status transitions to `IN_PROGRESS`.
* **When** posting to `/api/v1/monitoring/tasks/{id}/complete` with `completion_notes`,
* **Then**:
  * Status transitions to `COMPLETED` with timestamp.
  * Audit log records `MONITORING_TASK_COMPLETED`.

### AC-TSK-03: Task Reopening Guard
* **Given** a task in `COMPLETED` status,
* **When** a Field Officer attempts to reopen the task,
* **Then**: Server rejects with `403 Forbidden`.
* **When** an authorized PM or Admin submits `POST /api/v1/monitoring/tasks/{id}/reopen` with justification reason,
* **Then**:
  * Status reverts to `TODO`.
  * Audit log records `MONITORING_TASK_REOPENED`.

---

## 3. Domain 3: Survival Calculation Methodology & Partial Uniqueness

### AC-SURV-01: Server-Side Survival Rate Derivation & Client Disregard
* **Given** a client payload submitting `sample_size = 250`, `alive_count = 210`, `dead_count = 30`, and a fabricated `survival_rate = 99.9%`,
* **When** `POST /api/v1/monitoring/survival-observations` is submitted,
* **Then**:
  * The client-supplied `survival_rate` is completely ignored (not parsed by Pydantic schema).
  * The backend derives the ground-truth value:
    $$\text{survival\_rate} = \text{round}\left(\frac{210}{210 + 30} \times 100, 2\right) = 87.50\%$$
  * API response returns `survival_rate: 87.50`.

### AC-SURV-02: Zero-Denominator Protection
* **Given** an observation where `alive_count = 0` and `dead_count = 0`,
* **When** submitted,
* **Then**:
  * The backend returns `survival_rate: null`. No division-by-zero or exception occurs.

### AC-SURV-03: Mathematical Integrity Validation
* **Given** an observation payload where `alive_count + dead_count > sample_size` (e.g. sample=100, alive=70, dead=40),
* **When** submitted,
* **Then**:
  * Request is rejected with `422 Unprocessable Entity` (`detail: "alive_count + dead_count cannot exceed sample_size"`).

### AC-SURV-04: Longitudinal 3-Tuple Identity & Isolation
* **Given** Project $P$ with observations for `plot_identifier = 'PLOT-01', cohort_identifier = 'COHORT-A'` and `plot_identifier = 'PLOT-01', cohort_identifier = 'COHORT-B'`,
* **When** querying `GET /api/v1/monitoring/survival-analytics?project_id={P}&plot_identifier=PLOT-01&cohort_identifier=COHORT-A`,
* **Then**:
  * Returns time series containing **only** observations matching that exact 3-tuple.
  * Observations from other cohorts within the same plot are not mixed into the curve.

### AC-SURV-05: Partial Unique Index & Observation Correction Workflow
* **Given** an active observation $O_1$ for `(project_id, plot_identifier, cohort_identifier, observation_date)`,
* **When** a second active observation is inserted for the exact same 4-tuple without superseding $O_1$,
* **Then**:
  * The database partial unique index `uq_active_survival_observation` raises a unique violation error.
* **When** a correction is submitted via `POST /api/v1/monitoring/survival-observations/{id}/correct`,
* **Then**:
  * The transaction marks $O_1$ as `is_active = FALSE`.
  * Creates replacement observation $O_2$ with `is_active = TRUE`.
  * Sets $O_1.\text{superseded\_by\_id} = O_2.\text{id}$.
  * Both records are preserved in the database.
  * Audit log records `SURVIVAL_OBSERVATION_CORRECTED`.

### AC-SURV-06: Supersession Boundary & Anti-Circular Protection
* **Given** a correction request targeting observation $O_1$,
* **When** attempting to supersede across different project, plot, or cohort boundaries, or creating a circular reference ($O_1 \to O_1$ or $O_1 \to O_2 \to O_1$),
* **Then**:
  * The service rejects with `400 Bad Request` or database constraint `chk_survival_no_self_supersede` blocks the operation.

### AC-SURV-07: Strict Ledger Invariant (Policy Rule 7)
* **Given** a verified activity in Kaveri Basin with 2,500 verified trees on the official ledger,
* **When** survival observations record mortality in sample plots,
* **Then**:
  * `activity_revisions.quantity` remains strictly `2500`.
  * `activity_revisions.is_active_ledger_entry` remains `TRUE`.
  * Environmental ledger endpoints continue reporting verified quantity as `2500`.

---

## 4. Domain 4: Operational Alerts

### AC-ALT-01: Dynamic SQL Alert Evaluation (MVP Scope)
* **Given** an inspection in `SCHEDULED` status with `scheduled_date < CURRENT_DATE`,
* **When** calling `GET /api/v1/monitoring/alerts?project_id={P}`,
* **Then**: Returns `OVERDUE_INSPECTION` alert.
* **Given** a maintenance task in `TODO` status with `due_date < CURRENT_DATE`,
* **When** calling `GET /api/v1/monitoring/alerts?project_id={P}`,
* **Then**: Returns `OVERDUE_TASK` alert.
* **Given** an observation with low survival rate,
* **When** queried,
* **Then**: No `LOW_SURVIVAL_RATE` alert is generated (arbitrary threshold removed from MVP).

---

## 5. Domain 5: RBAC & Performance Benchmark

### AC-RBAC-01: Project Manager Scoping (Rule 4)
* **Given** a `PROJECT_MANAGER` assigned to Project $A$ but not Project $B$,
* **When** attempting to schedule an inspection or view monitoring data for Project $B$,
* **Then**: Server returns `403 Forbidden` (`detail: "You do not have access to this project"`).

### AC-RBAC-02: Field Officer Inspection Ownership
* **Given** a `FIELD_OFFICER` assigned to Project $A$,
* **When** attempting to start or complete an inspection assigned to another officer,
* **Then**: Server returns `403 Forbidden` (`detail: "Field Officers may only modify inspections assigned to them"`).

### AC-RBAC-03: Latency Benchmark
* **Given** a database populated with 10,000 inspections and 25,000 tasks,
* **When** executing project alert queries or dashboard aggregations,
* **Then**: Query latency is $< 25\text{ms}$ on PostgreSQL utilizing composite B-tree indexes.
