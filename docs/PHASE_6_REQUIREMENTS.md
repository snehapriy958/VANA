# VANA Phase 6 — Field Monitoring & Follow-up Management: Requirements Specification

> **Document Status:** Final Gate Approved\
> **Release Target:** VANA Phase 6 (Milestone 6)\
> **Traceability:** Aligns with `AGENTS.md` (Rules 1, 4, 6, 7, 8, 9), `docs/PHASE_6_FINAL_IMPLEMENTATION_GATE.md`.

---

## 1. Executive Summary & Objective

VANA provides end-to-end lifecycle coverage for environmental interventions:
$$\text{PLAN} \longrightarrow \text{ASSIGN} \longrightarrow \text{EXECUTE} \longrightarrow \text{RECORD} \longrightarrow \text{VERIFY} \longrightarrow \text{MEASURE} \longrightarrow \mathbf{MONITOR}$$

The objective of **Phase 6** is to deliver the **Field Monitoring & Follow-up Management** module. This operational layer empowers Project Managers and Field Officers to conduct periodic field inspections, manage ongoing maintenance tasks, record scientifically grounded vegetation survival observations, track longitudinal health trends by plot/cohort, and evaluate operational alerts in real time without external task queues.

---

## 2. Core Invariants & Engineering Guardrails

1. **Strict Ledger Isolation (Mandatory Policy Rule 7):**
   * Field monitoring observations and mortality counts must **never** mutate historical verified achievements (`activity_revisions.quantity` or `is_active_ledger_entry`).
   * If trees die post-verification, official historical planting metrics remain intact. Mortality is reported exclusively as an operational survival index.
   * Any replacement planting or gap filling must be submitted as a separate operational activity (`TREES_PLANTED`) through the standard verification workflow.
2. **Scientific Data Grounding (Mandatory Policy Rule 9):**
   * Calculations of survival rates must adhere strictly to verified denominators. Sample observations must never use the total project population as a denominator.
   * Division-by-zero is strictly guarded: survival rates are evaluated only when the assessed count $(A + D) > 0$.
   * Extrapolations from sample plots to project-wide populations are prohibited without an approved, statistically validated sampling methodology.
   * Universal arbitrary survival thresholds (such as a generic 70% threshold) are strictly prohibited. The system presents raw counts, assessed denominators, and observed sample rates without unsupported classifications.
3. **Audit Trail & Evidence Retention (Mandatory Policy Rule 6):**
   * All evidence files linked to field inspections are protected under `ON DELETE RESTRICT`. Completed inspections and uploaded evidence cannot be deleted or purged.
   * Historical observations are immutable; corrections must follow an append-only superseding audit pattern (`is_active = FALSE`, `superseded_by_id`).
4. **Cross-Project Referential Integrity (Mandatory Policy Rule 4):**
   * Cross-project entity associations are prohibited at both the database level via composite foreign keys `(entity_id, project_id)` and at the service level.
5. **Modular Monolith Discipline (Mandatory Policy Rule 1):**
   * All monitoring operations execute inside the existing FastAPI backend and PostgreSQL database.
   * No external message brokers, Celery/Redis daemons, or PostGIS spatial engines are permitted.

---

## 3. User Personas & Scoped Responsibilities

| Persona | System Role | Core Monitoring Responsibilities |
| :--- | :--- | :--- |
| **Organization Administrator** | `ADMIN` | Organization-wide visibility, system-wide configuration, cross-project monitoring analytics, and audit log inspection. |
| **Project Manager** | `PROJECT_MANAGER` | Schedule inspections, assign team members, create maintenance tasks, review completed inspections, issue correction addenda, correct survival counts, and monitor project survival trajectories. Scoped strictly to assigned projects. |
| **Field Officer** | `FIELD_OFFICER` | View assigned inspections, execute field checks, record alive/dead counts for designated sample plots, upload geo-tagged photo evidence, and complete assigned maintenance tasks. Restricted to assigned projects and assigned inspections. |

---

## 4. Functional Requirements

### 4.1 Field Inspection Management (`FR-INS`)

* **FR-INS-01 (Inspection Scheduling):** PMs and Admins can schedule inspections specifying `project_id`, `scheduled_date`, `inspection_type` (`ROUTINE`, `SURVIVAL_CHECK`, `MAINTENANCE_AUDIT`, `EMERGENCY`), `assigned_to_id`, and optional `linked_activity_id`.
* **FR-INS-02 (Project Assignment Validation):** When assigning an inspector, the backend must verify that `assigned_to_id` has an active assignment in `project_assignments` for `project_id`. Unassigned users must be rejected (`400 Bad Request`).
* **FR-INS-03 (Cross-Project Composite Protection):** `linked_activity_id` must match `project_id` via composite foreign key `(linked_activity_id, project_id) REFERENCES field_activities(id, project_id)`. Mismatches are rejected by the database and service layer (`400 Bad Request`).
* **FR-INS-04 (Deterministic State Transitions):**
  * `SCHEDULED` $\to$ `IN_PROGRESS`: Initiated by assigned inspector, PM, or Admin.
  * `SCHEDULED` $\to$ `CANCELLED`: Initiated by PM or Admin with mandatory cancellation reason.
  * `IN_PROGRESS` $\to$ `COMPLETED`: Initiated by assigned inspector, PM, or Admin with mandatory findings and vegetation health score.
  * `IN_PROGRESS` $\to$ `CANCELLED`: Initiated by PM or Admin with reason.
* **FR-INS-05 (Completed Inspection Immutability):** Completed inspections are locked. Findings, health scores, and dates cannot be edited directly via `PATCH`.
* **FR-INS-06 (Post-Completion Correction Addenda):** If factual errors are identified after completion, PMs/Admins can record an immutable **Correction Addendum** (`POST /api/v1/monitoring/inspections/{id}/addendum`) which is audit-logged without modifying original findings.
* **FR-INS-07 (Evidence Retention & Reuse):** Inspection photo evidence reuses the existing `evidence_files` infrastructure with `ON DELETE RESTRICT`, storing SHA-256 hashes, file metadata, optional GPS coordinates, and captions.

### 4.2 Maintenance Task Management (`FR-TSK`)

* **FR-TSK-01 (Task Creation):** PMs and Admins can create tasks with `project_id`, `title`, `description`, `category` (`IRRIGATION`, `WEEDING`, `MULCHING`, `FENCING_REPAIR`, `REPLANTING_PREP`, `PEST_CONTROL`, `SOIL_ENRICHMENT`, `OTHER`), `priority` (`LOW`, `MEDIUM`, `HIGH`, `URGENT`), `due_date`, and optional `assigned_to_id`.
* **FR-TSK-02 (Composite Task Linking):** Tasks can link to an `inspection_id` or `activity_id` within the same project enforced by composite foreign keys `(inspection_id, project_id)` and `(activity_id, project_id)`.
* **FR-TSK-03 (Task Lifecycle):**
  * `TODO` $\to$ `IN_PROGRESS`: Assignee, PM, Admin.
  * `IN_PROGRESS` $\to$ `COMPLETED`: Assignee, PM, Admin with mandatory `completion_notes`.
  * Open $\to$ `CANCELLED`: PM, Admin with cancellation reason.
* **FR-TSK-04 (Task Reopening):** Completed tasks cannot be silently edited. Reopening (`COMPLETED` $\to$ `TODO`) is restricted to PM/Admin with mandatory justification.

### 4.3 Survival Monitoring & Longitudinal Tracking (`FR-SURV`)

* **FR-SURV-01 (Population Categorization):**
  * **Total Planting Population ($N_{\text{total}}$):** Official verified quantity from `activity_revisions`.
  * **Inspected Population ($N_{\text{sample}}$):** Sample plot or census target count.
  * **Alive Count ($A$):** Number of viable plants observed.
  * **Dead Count ($D$):** Number of non-viable/dead plants observed.
  * **Unassessed Count ($U$):** $N_{\text{sample}} - (A + D)$ (plants lost, obscured, or unaccounted for).
* **FR-SURV-02 (Sample Survival Rate Calculation):**
  $$\text{observed\_sample\_survival\_rate} = \frac{A}{A + D} \times 100$$
  * Evaluated **only** when assessed denominator $(A + D) > 0$. When $A + D = 0$, rate returns `None` (`null`).
  * $N_{\text{total}}$ is never used as the denominator for sample observations.
  * The metric is explicitly labeled as `observed_sample_survival_rate`.
  * Population-wide extrapolation is prohibited without an approved sampling methodology.
* **FR-SURV-03 (Plot, Cohort & Longitudinal Identity):**
  * **Plot Identity (`plot_identifier`):** Physical sampling unit code within a project (e.g., `PLOT-01`). Multiple cohorts may exist within one plot.
  * **Cohort Identity (`cohort_identifier`):** Planting batch or intervention group (e.g., `COHORT-2025-BATCH-1`). One cohort may span multiple plots.
  * **Population Unit Tuple:** The monitored population is uniquely identified by the tuple:
    $$(project\_id, plot\_identifier, cohort\_identifier)$$
  * Longitudinal comparison queries must only group observations sharing the exact 3-tuple and methodology.
* **FR-SURV-04 (Append-Only Historical Corrections):**
  * Historical observation rows are never overwritten or deleted.
  * Corrections submitted by PM/Admin mark the original row `is_active = FALSE`, set `superseded_by_id` pointing to the new correction row, and record `correction_notes`.
* **FR-SURV-05 (Data Integrity Constraints):**
  * $A \ge 0, D \ge 0, N_{\text{sample}} > 0$.
  * $A + D \le N_{\text{sample}}$.
  * Unique constraint: `UNIQUE (project_id, plot_identifier, cohort_identifier, observation_date)`.

### 4.4 Operational Alerts & Notifications (`FR-ALT`)

* **FR-ALT-01 (Scope Separation):** Phase 6 implements **in-database dynamic SQL query alerts** displayed in UI dashboards. Outbound notifications (push, email, SMS, webhooks) are deferred to future milestones.
* **FR-ALT-02 (Active MVP Alerts):**
  1. `OVERDUE_INSPECTION`: `status = 'SCHEDULED' AND scheduled_date < CURRENT_DATE`.
  2. `UPCOMING_INSPECTION`: `status = 'SCHEDULED' AND scheduled_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'`.
  3. `OVERDUE_TASK`: `status IN ('TODO', 'IN_PROGRESS') AND due_date < CURRENT_DATE`.
* **FR-ALT-03 (No Universal Survival Alert):** Arbitrary low-survival classification alerts are removed. Future configurable project-level ecological thresholds are deferred.

### 4.5 Monitoring Dashboard & Analytics (`FR-DASH`)

* **FR-DASH-01 (Project Health Summary):** Inspection counts, maintenance backlog, open alerts, and latest observed survival rate.
* **FR-DASH-02 (Longitudinal Survival Trajectory):** Visual curve showing survival rate over time, explicitly partitioned by plot and cohort, displaying sample size and assessed count.
* **FR-DASH-03 (Organization Overview):** Multi-project monitoring table showing compliance rates and overdue items.

---

## 5. Non-Functional Requirements (`NFR`)

* **NFR-01 (Performance & Query Efficiency):** Alert queries and dashboard aggregations leverage composite B-tree indexes, achieving $< 25\text{ms}$ query latency on PostgreSQL without background caching services.
* **NFR-02 (Auditability):** Every status transition, addendum, task reopen, and survival correction creates an immutable record in `audit_logs`.
* **NFR-03 (Design Token Adherence):** All UI elements adhere to VANA design tokens (`#183D32`, `#F5F3EA`, `#A8B99B`, `#D6A76A`, `#29332F`) and Manrope/Inter typography.
