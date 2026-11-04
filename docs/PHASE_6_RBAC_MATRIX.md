# VANA Phase 6 — Field Monitoring & Follow-up Management: RBAC Matrix & Security Boundaries

> **Document Status:** Final Gate Approved\
> **Target Release:** VANA Phase 6 (Milestone 6)\
> **Traceability:** Aligns with `AGENTS.md` (Rules 4, 6), `docs/PHASE_6_FINAL_IMPLEMENTATION_GATE.md`.

---

## 1. Principles of Independent Authorization

1. **Server-Side Enforcement (Rule 4):**
   * Every monitoring endpoint independently validates JWT tokens, system roles (`UserRole`), project assignments (`ProjectAssignment`), entity ownership, and cross-project references.
2. **Project Scoping (Mandatory Rule 4):**
   * `ADMIN`: Organization-wide access to all projects, monitoring data, and configurations.
   * `PROJECT_MANAGER`: Strictly scoped to projects where the user has an active `ProjectAssignment`. Accessing unassigned projects returns `403 Forbidden`.
   * `FIELD_OFFICER`: Strictly scoped to projects where the user has an active `ProjectAssignment`.
3. **Inspector Ownership Protection:**
   * A Field Officer may only start, upload evidence to, or complete inspections where `assigned_to_id == current_user.id`.
   * Field Officers cannot modify or complete inspections assigned to other officers.
4. **Cross-Project Reference Integrity:**
   * Cross-project entity associations (e.g., linking an activity from Project A to an inspection in Project B) are blocked at the database level by composite foreign keys and rejected at the service layer with `400 Bad Request`.

---

## 2. Granular Endpoint Permission Matrix

| Endpoint Route | Operation | Method | `ADMIN` | `PROJECT_MANAGER` | `FIELD_OFFICER` | Enforcement Rule |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| `/api/v1/monitoring/inspections` | Schedule inspection | `POST` | ALLOW | ALLOW (Assigned) | DENY (`403`) | Validates inspector belongs to project |
| `/api/v1/monitoring/inspections` | List inspections | `GET` | ALLOW | ALLOW (Assigned) | ALLOW (Assigned) | Filtered by project assignment |
| `/api/v1/monitoring/inspections/{id}` | Get inspection details | `GET` | ALLOW | ALLOW (Assigned) | ALLOW (Assigned) | Scoped to assigned project |
| `/api/v1/monitoring/inspections/{id}/start` | Transition to `IN_PROGRESS` | `POST` | ALLOW | ALLOW (Assigned) | ALLOW (Owner Only) | Inspector must match `assigned_to_id` |
| `/api/v1/monitoring/inspections/{id}/complete` | Submit findings & complete | `POST` | ALLOW | ALLOW (Assigned) | ALLOW (Owner Only) | Findings mandatory; locks record |
| `/api/v1/monitoring/inspections/{id}/cancel` | Cancel inspection | `POST` | ALLOW | ALLOW (Assigned) | DENY (`403`) | Mandatory cancellation reason |
| `/api/v1/monitoring/inspections/{id}/addendum` | Record post-completion correction | `POST` | ALLOW | ALLOW (Assigned) | DENY (`403`) | Immutable addendum; audits change |
| `/api/v1/monitoring/inspections/{id}/evidence` | Upload photo evidence | `POST` | ALLOW | ALLOW (Assigned) | ALLOW (Owner Only) | Protected by `ON DELETE RESTRICT` |
| `/api/v1/monitoring/tasks` | Create maintenance task | `POST` | ALLOW | ALLOW (Assigned) | DENY (`403`) | Scoped to assigned project |
| `/api/v1/monitoring/tasks` | List maintenance tasks | `GET` | ALLOW | ALLOW (Assigned) | ALLOW (Assigned) | Filtered by project assignment |
| `/api/v1/monitoring/tasks/{id}/start` | Transition task to `IN_PROGRESS` | `POST` | ALLOW | ALLOW (Assigned) | ALLOW (Owner Only) | Assignee or PM |
| `/api/v1/monitoring/tasks/{id}/complete` | Complete maintenance task | `POST` | ALLOW | ALLOW (Assigned) | ALLOW (Owner Only) | Mandatory completion notes |
| `/api/v1/monitoring/tasks/{id}/cancel` | Cancel maintenance task | `POST` | ALLOW | ALLOW (Assigned) | DENY (`403`) | Mandatory cancellation reason |
| `/api/v1/monitoring/tasks/{id}/reopen` | Reopen completed task | `POST` | ALLOW | ALLOW (Assigned) | DENY (`403`) | Mandatory justification note |
| `/api/v1/monitoring/survival-observations` | Record survival observation | `POST` | ALLOW | ALLOW (Assigned) | ALLOW (Assigned) | Math validation: $(A + D) \le N$ |
| `/api/v1/monitoring/survival-observations/{id}/correct` | Record corrected observation | `POST` | ALLOW | ALLOW (Assigned) | DENY (`403`) | Append-only superseding pattern |
| `/api/v1/monitoring/survival-analytics` | Get survival trajectory | `GET` | ALLOW | ALLOW (Assigned) | ALLOW (Assigned) | Filtered by plot & cohort tuple |
| `/api/v1/monitoring/alerts` | Query dynamic alerts | `GET` | ALLOW | ALLOW (Assigned) | ALLOW (Assigned) | Evaluated on-demand in SQL |
| `/api/v1/monitoring/dashboard` | View monitoring KPIs | `GET` | ALLOW (Org) | ALLOW (Assigned) | ALLOW (Assigned) | Project or Org aggregate |
