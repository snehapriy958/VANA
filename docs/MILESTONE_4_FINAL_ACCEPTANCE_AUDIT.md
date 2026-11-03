# VANA — Milestone 4 Final Acceptance Audit Report
## Field Operations, Evidence Management & Activity Verification

> **Audit Status:** Verified & Complete  
> **Date:** 2026-11-03  
> **Auditor:** Senior Product Architect & Technical Lead  
> **Scope:** Milestone 4 Codebase, Models, Schemas, Services, Endpoints, Storage Drivers, Frontend Views, and Test Suites  
> **Verdict:** **PASS**  

---

## 1. Executive Summary & Verdict

In accordance with the **Milestone 4 Acceptance Audit** mandate, an independent, comprehensive verification was performed across the VANA backend (FastAPI, SQLAlchemy 2.x, PostgreSQL) and frontend (React 19, TypeScript, Tailwind CSS) implementations. The audit evaluated source code, database models, relational constraints, partial indexes, REST API endpoints, cryptographic storage mechanisms, concurrency locks, RBAC scoping, and test suites.

### Audit Verdict: **PASS**

All twelve critical audit areas specified for Milestone 4 have been verified:
1. **Verified Revisions are Immutable:** Verified revisions cannot be mutated, edited, or re-evaluated via any endpoint. Corrections require submitting an explicit new revision.
2. **Single Active Ledger Entry Enforcement:** Enforced both in service business logic and by PostgreSQL partial unique index `uq_activity_single_active_ledger` (`WHERE is_active_ledger_entry = TRUE`).
3. **Amendment Accounting Precision:** Positive ($\Delta > 0$) and negative ($\Delta < 0$) net pending adjustments are calculated accurately without inflating current verified quantities or double-counting historical submissions.
4. **Amendment Rejection Ledger Preservation:** Rejecting an unreviewed amendment transitions only the rejected revision to `REJECTED`; the previously verified revision remains active in the official ledger.
5. **Anti-Self-Verification Rule (Mandatory Rule 5):** Backend enforces `current_user.id != activity.created_by_id`, returning `HTTP 403 Forbidden` (`SELF_VERIFICATION_PROHIBITED`). Field Officers are blocked from verification entirely. Frontend disables self-verification controls with clear policy tooltips.
6. **Project-Level Authorization Scoping:** All eight operations and verification endpoints enforce project assignment boundaries. Project Managers and Field Officers cannot view, submit, or verify activities for unassigned projects.
7. **Evidence File Security & Path Traversal Prevention:** Uploads enforce a 10 MB ceiling, 5 files per revision limit, MIME type whitelist (JPEG, PNG, WEBP, PDF), SHA-256 content addressing, and directory traversal containment (`is_relative_to(root)`).
8. **Concurrency & Race Condition Safeguards:** Row-level pessimistic locking (`with_for_update()`) on verification decisions and amendment submissions ensures concurrent requests serialize cleanly and return predictable HTTP status codes.
9. **Activity Archival Integrity Investigation:** Archiving an activity cleanly soft-deletes the activity and deactivates any active ledger entry per specification. An architectural recommendation is documented for future distinction between operational archiving and formal environmental retraction.
10. **Append-Only Immutable Audit Logs:** All field mutations (`ACTIVITY_CREATED`, `EVIDENCE_UPLOADED`, `ACTIVITY_AMENDED`, `ACTIVITY_VERIFIED`, `ACTIVITY_REJECTED`, `ACTIVITY_ARCHIVED`) generate immutable audit log rows. No update or delete endpoints exist for audit logs.
11. **Transaction Boundaries:** Atomic database flushes, commits, and rollbacks prevent partial state persistence during failures.
12. **Frontend Workflows & Design System Adherence:** The Field Operations (`/operations`) and Verification Centre (`/verification`) views adhere strictly to VANA brand design tokens, responsive standards, and role-based route guards.
13. **Empirical Test Verification:** Full backend test suite passed with **77/77 tests (100% pass rate in 42.06s)**. Full frontend test suite passed with **21/21 tests (100% pass rate in 0.25s)**. Frontend typecheck reported **0 errors**, and production build succeeded cleanly in **11.65s**.

---

## 2. Comprehensive Findings by Audit Area

### Area 1: Immutability of Verified Revisions
* **File/Function:** `backend/app/domains/operations/services.py` (`VerificationService.record_decision`, `ActivityService.amend_activity`)
* **Evidence:** 
  * The API exposes zero `PUT` or `PATCH` endpoints for `ActivityRevision`.
  * In `record_decision`, before any status transition is applied, the system asserts:
    ```python
    if revision.status != ActivityStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "REVISION_ALREADY_REVIEWED",
                "message": f"Revision {revision.revision_number} is already in '{revision.status}' state.",
            },
        )
    ```
  * Once a revision is marked `status = 'VERIFIED'`, its attributes (`quantity`, `activity_date`, `latitude`, `longitude`, `field_notes`) can never be modified. Any subsequent modification requires invoking `POST /api/v1/operations/activities/{id}/revisions` which generates Revision $N+1$ in `PENDING` status.
  * Database constraint `chk_verification_signature_required` guarantees that verified rows permanently record `verifier_id` and `verified_at`.
* **Reproduction/Test Result:** Validated by `backend/tests/test_operations_and_verification.py::test_concurrent_verification_decisions_safeguard` and immutability invariants.
* **Severity:** Verified — No issue found.

---

### Area 2: Single Active Ledger Entry per Activity
* **File/Function:** `backend/app/domains/operations/models.py`, `backend/app/domains/operations/services.py`
* **Evidence:**
  * Double-counting prevention is enforced at the database layer via PostgreSQL partial unique index:
    ```sql
    CREATE UNIQUE INDEX uq_activity_single_active_ledger 
    ON activity_revisions(activity_id) 
    WHERE is_active_ledger_entry = TRUE;
    ```
  * Supplemented by table check constraint:
    ```sql
    CONSTRAINT chk_active_ledger_verified 
    CHECK ((is_active_ledger_entry = FALSE) OR (is_active_ledger_entry = TRUE AND status = 'VERIFIED'));
    ```
  * In `VerificationService.record_decision`, when a revision is approved:
    ```python
    for rev in activity.revisions:
        if rev.is_active_ledger_entry and rev.id != revision.id:
            rev.is_active_ledger_entry = False
    await db.flush()
    revision.status = ActivityStatus.VERIFIED.value
    revision.is_active_ledger_entry = True
    ```
* **Reproduction/Test Result:** Validated by `backend/tests/test_models_and_constraints.py::test_partial_unique_index_active_ledger_prevents_double_counting` and `test_check_constraint_active_ledger_must_be_verified`.
* **Severity:** Verified — No issue found.

---

### Area 3: Amendment Accounting for Positive and Negative Adjustments
* **File/Function:** `backend/app/domains/operations/services.py` (`_build_activity_response`, `get_verification_queue`)
* **Evidence:**
  * The mathematical model strictly adheres to `06_ENVIRONMENTAL_IMPACT_LOGIC.md` Section 3:
    $$\Delta Q_{\text{pending}} = Q_{\text{amended}} - Q_{\text{verified}}$$
  * While an amendment is `PENDING`, the official verified achievement remains $Q_{\text{verified}}$ (the existing active ledger entry). The pending adjustment $\Delta Q_{\text{pending}}$ is reported separately for pipeline forecasting:
    ```python
    active_rev = next((r for r in revision_responses if r.is_active_ledger_entry), None)
    active_verified_qty = active_rev.quantity if active_rev else Decimal("0.0")

    net_pending_adj: Optional[Decimal] = None
    if current_rev and current_rev.status == ActivityStatus.PENDING.value:
        if active_rev:
            net_pending_adj = current_rev.quantity - active_rev.quantity
        else:
            net_pending_adj = current_rev.quantity
    ```
* **Empirical Verification:**
  * **Positive Amendment Scenario:**
    * Initial: 100 trees verified $\to$ Active Verified Quantity $= 100$.
    * Amendment submitted: 160 trees $\to$ Active Verified Quantity $= 100$, Net Pending Adjustment $= +60$.
    * Upon verification $\to$ Active Verified Quantity $= 160$, Net Pending Adjustment $= \text{null}$.
  * **Negative Amendment Scenario:**
    * Initial: 100 trees verified $\to$ Active Verified Quantity $= 100$.
    * Amendment submitted: 50 trees $\to$ Active Verified Quantity $= 100$, Net Pending Adjustment $= -50$.
    * Upon verification $\to$ Active Verified Quantity $= 50$, Net Pending Adjustment $= \text{null}$.
* **Reproduction/Test Result:** Validated by `test_amendment_net_adjustment_accounting` and `test_negative_amendment_net_adjustment`.
* **Severity:** Verified — No issue found.

---

### Area 4: Preserving Verified Revisions on Amendment Rejection
* **File/Function:** `backend/app/domains/operations/services.py` (`VerificationService.record_decision`)
* **Evidence:**
  * When an amendment is rejected by a reviewer:
    ```python
    elif data.decision == ActivityStatus.REJECTED.value:
        revision.status = ActivityStatus.REJECTED.value
        revision.is_active_ledger_entry = False
        revision.verifier_id = current_user.id
        revision.verified_at = now
        revision.rejection_reason_code = data.rejection_reason_code
        revision.review_notes = data.review_notes.strip()
    ```
  * The earlier verified revision's `is_active_ledger_entry` flag remains `True`. It is never cleared during a rejection.
* **Reproduction/Test Result:**
  * Initial Revision 1: 100 trees, verified, `is_active_ledger_entry = True`.
  * Amendment Revision 2: 150 trees, submitted.
  * Revision 2 rejected with `REASON = DATA_ENTRY_ERROR`.
  * Querying the activity reveals: Current Revision is Revision 2 (`REJECTED`), while Revision 1 remains `VERIFIED` and `is_active_ledger_entry = True`. Active verified quantity remains 100 trees.
  * Validated by `backend/tests/test_operations_and_verification.py::test_rejection_preserves_previously_verified_revision`.
* **Severity:** Verified — No issue found.

---

### Area 5: Anti-Self-Verification Gate
* **File/Function:** `backend/app/domains/operations/services.py` (`VerificationService.record_decision`), `frontend/src/views/verification/VerificationCentreView.tsx`
* **Evidence:**
  * Permanent Engineering Rule 5 states: Under no circumstances may a user verify their own activity submission (`verifier_id != creator_id`). Attempted self-verification must return `HTTP 403 Forbidden`.
  * Backend implementation:
    ```python
    if current_user.id == activity.created_by_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "SELF_VERIFICATION_PROHIBITED",
                "message": "Policy Violation: You cannot verify an activity submission you authored.",
            },
        )
    ```
  * In addition, Field Officers are prohibited from verification entirely (`HTTP 403 INSUFFICIENT_ROLE`).
  * In frontend `VerificationCentreView.tsx`:
    ```typescript
    const isAuthor = currentUser?.id === selectedItem.created_by_id;
    // Disables Action buttons and displays amber badge:
    // "Anti-Self-Verification Policy: You authored this activity submission and cannot verify it."
    ```
* **Reproduction/Test Result:** Validated by `test_anti_self_verification_gate_strictly_enforced` and frontend unit test `enforces Rule 5: Anti-Self-Verification Gate in UI authorization logic`.
* **Severity:** Verified — No issue found.

---

### Area 6: Project-Level Authorization Scoping
* **File/Function:** `backend/app/domains/operations/services.py`, `backend/app/domains/operations/router.py`, `backend/app/domains/operations/verification_router.py`
* **Evidence:**
  * The backend enforces independent authorization on every endpoint:
    | Endpoint | Method | Authorization Scope |
    |---|:---:|---|
    | `/activities` | `POST` | Global `ADMIN` or user with active `ProjectAssignment` on target project. |
    | `/activities` | `GET` | Global `ADMIN` sees all; other roles filtered by assigned projects. |
    | `/activities/{id}` | `GET` | Global `ADMIN` or user assigned to activity's project. |
    | `/activities/{id}/revisions` | `POST` | Global `ADMIN` or user assigned to activity's project. |
    | `/activities/{id}` | `DELETE` | Global `ADMIN` or `ProjectAssignment.assigned_role == "PROJECT_MANAGER"`. |
    | `/evidence/{id}` | `GET` | Global `ADMIN` or user assigned to evidence activity's project. |
    | `/verification/queue` | `GET` | `FIELD_OFFICER` gets 403; `ADMIN` sees portfolio; `PROJECT_MANAGER` sees assigned projects. |
    | `/revisions/{id}/decision` | `POST` | `FIELD_OFFICER` gets 403; `PROJECT_MANAGER` must be assigned to project. |
* **Reproduction/Test Result:** Validated by `test_unassigned_field_officer_cannot_submit_activity`, `test_field_officer_cannot_verify_activities`, `test_cross_project_pm_cannot_verify_unassigned_project`, and `test_evidence_file_upload_and_secure_streaming`.
* **Severity:** Verified — No issue found.

---

### Area 7: Evidence File Security & Path Traversal Prevention
* **File/Function:** `backend/app/core/storage.py` (`LocalStorageService`), `backend/app/domains/operations/services.py`
* **Audit Assessment & Hardening:**
  * **File Size:** Enforces `MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024` (10 MB). Oversized files return `HTTP 400 FILE_TOO_LARGE`.
  * **File Count:** Enforces `MAX_FILES_PER_SUBMISSION = 5`. Excessive files return `HTTP 400 TOO_MANY_FILES`.
  * **MIME Whitelist:** Strictly restricted to `image/jpeg`, `image/png`, `image/webp`, `application/pdf`. Unapproved formats (e.g. `.exe`, `.sh`) return `HTTP 400 UNSUPPORTED_FILE_TYPE`.
  * **Content-Addressing:** Files are saved using `sha256(content) + ext`, completely decoupling disk storage from user-supplied filenames.
  * **Path Traversal Containment:** Added path resolution containment check to `LocalStorageService.get_file_path`:
    ```python
    def get_file_path(self, storage_key: str) -> Path:
        resolved_root = self.root_dir.resolve()
        resolved_target = (self.root_dir / storage_key).resolve()
        if not resolved_target.is_relative_to(resolved_root):
            raise ValueError("Invalid storage key: path traversal detected.")
        return resolved_target
    ```
    Attempted traversal (e.g. `../../../windows/win.ini`) is caught and returns `HTTP 400 INVALID_STORAGE_KEY`.
* **Reproduction/Test Result:** Validated by `backend/tests/test_operations_and_verification.py::test_evidence_file_path_traversal_prevention`.
* **Severity:** Low (Hardened & Verified).

---

### Area 8: Concurrent Verification Behavior
* **File/Function:** `backend/app/domains/operations/services.py` (`VerificationService.record_decision`, `ActivityService.amend_activity`)
* **Evidence:**
  * Verification decision processing uses pessimistic row-level locking:
    ```python
    stmt = (
        select(ActivityRevision)
        .where(ActivityRevision.id == revision_id)
        .options(...)
        .with_for_update()
    )
    revision = await db.scalar(stmt)
    ```
  * When two transactions concurrently attempt to verify or reject the same revision, the second transaction blocks until the first completes. Upon unblocking, the second transaction reads the updated `revision.status` and raises `HTTP 400 REVISION_ALREADY_REVIEWED`.
  * Similarly, `ActivityService.amend_activity` and `ActivityService.archive_activity` lock the parent `FieldActivity` row with `.with_for_update()`, preventing concurrent conflicting revisions.
* **Reproduction/Test Result:** Validated by `backend/tests/test_operations_and_verification.py::test_concurrent_verification_decisions_safeguard`.
* **Severity:** Verified — No issue found.

---

### Area 9: Archiving a Verified Activity Investigation
* **File/Function:** `backend/app/domains/operations/services.py` (`ActivityService.archive_activity`)
* **Investigation & Architectural Analysis:**
  * In `docs/engineering/04_API_SPECIFICATION.md` Line 99 and `docs/engineering/06_ENVIRONMENTAL_IMPACT_LOGIC.md` Section 3, the specification states:
    > *"Soft-deletes the field activity and deactivates any active ledger entry."*
  * In `archive_activity`:
    ```python
    activity.is_archived = True
    for rev in activity.revisions:
        if rev.is_active_ledger_entry:
            rev.is_active_ledger_entry = False
    ```
  * **Architectural Observation (Medium Severity):**
    From an environmental accounting perspective, permanently deactivating an active ledger entry because an activity container was archived in the operational UI revokes verified achievements from project totals.
    If an activity was verified, revoking it should ideally be a formal retraction event (with a recorded reason and verifier signature) rather than an operational soft-delete.
  * **Status:** Current code strictly fulfills the approved API contract.
  * **Recommendation for Milestone 5 / Backlog:** Distinguish between *Visual Archival* (hide from active operational lists while preserving official ledger entry) and *Formal Environmental Retraction* (explicitly revoke with justification code and audit record).
* **Severity:** Medium (Architectural observation / Non-blocking for Milestone 4 acceptance).

---

### Area 10: Immutable Audit Logging
* **File/Function:** `backend/app/domains/audit/`, `backend/app/domains/operations/services.py`
* **Evidence:**
  * All mutations in Milestone 4 write to `audit_logs` table via `record_audit_log`:
    * `ACTIVITY_CREATED`
    * `EVIDENCE_UPLOADED`
    * `ACTIVITY_AMENDED`
    * `ACTIVITY_VERIFIED`
    * `ACTIVITY_REJECTED`
    * `ACTIVITY_ARCHIVED`
  * The `AuditLog` table contains no `onupdate` triggers, and the backend exposes zero `PUT`, `PATCH`, or `DELETE` endpoints for audit records.
  * Sensitive data (passwords, JWT hashes) are excluded from `new_state` and `old_state` payloads.
* **Reproduction/Test Result:** Validated by `backend/tests/test_operations_and_verification.py::test_audit_logs_record_all_operation_mutations`.
* **Severity:** Verified — No issue found.

---

### Area 11: Transaction Boundaries & Race Conditions
* **File/Function:** `backend/app/domains/operations/services.py`
* **Evidence:**
  * Async sessions provided via `get_db` wrap requests in database transactions.
  * Database operations use `await db.flush()` during multi-step object creation (e.g. creating `FieldActivity`, then `ActivityRevision`, then `EvidenceFile`, then `AuditLog`), followed by atomic commit upon endpoint completion.
  * In case of any exception or HTTP error, SQLAlchemy automatically rolls back the entire transaction, preventing orphaned parent or evidence records.
* **Reproduction/Test Result:** Verified across all error simulation tests.
* **Severity:** Verified — No issue found.

---

### Area 12: Frontend Routes & Verification Center Workflows
* **File/Function:** `frontend/src/views/operations/FieldOperationsView.tsx`, `frontend/src/views/verification/VerificationCentreView.tsx`, `frontend/src/routes/index.tsx`
* **Evidence:**
  * **Route Mounting & Protection:**
    * `/operations`: Accessible to `ADMIN`, `PROJECT_MANAGER`, `FIELD_OFFICER`.
    * `/verification`: Accessible strictly to `ADMIN` and `PROJECT_MANAGER`. Unauthorized roles are redirected or blocked by `ProtectedRoute`.
  * **Field Operations Workflow:**
    * Project selector filtered by user permissions.
    * Real-time metric code validation matching configured project targets.
    * Positive quantity validation ($Q > 0$).
    * GPS coordinate capture with numeric finite checks.
    * File upload drag-and-drop supporting JPEG, PNG, WEBP, and PDF.
    * Amendment submission drawer with positive/negative net adjustment calculation preview.
  * **Verification Centre Workflow:**
    * Tabbed filtering: All, Initial Submissions, Amendments.
    * Item inspection drawer with side-by-side evidence viewer, GPS coordinates, submitter metadata, and revision history.
    * Anti-Self-Verification rule UI warning for self-authored activities.
    * Rejection modal requiring structured rejection reason code and mandatory review notes.
  * **Design System Consistency:**
    * Manrope font for headings, Inter for body text.
    * Forest Green (`#183D32`), Warm Ivory (`#F5F3EA`), Sage (`#A8B99B`), Earth Gold (`#D6A76A`), and Charcoal (`#29332F`).
* **Reproduction/Test Result:** 21 frontend unit tests passing; TypeScript typecheck 0 errors; production build succeeded cleanly.
* **Severity:** Verified — No issue found.

---

## 3. Empirical Test Execution Results

### 3.1 Backend Test Suite (Pytest)
```
Command: backend\.venv\Scripts\pytest backend\tests -v
Result: 77 passed in 42.06s (100% pass rate)

Breakdown:
- test_auth_and_rbac.py: 28 passed
- test_database_connection.py: 2 passed
- test_migrations.py: 1 passed
- test_models_and_constraints.py: 5 passed
- test_projects_and_targets.py: 18 passed
- test_token_lifecycle.py: 5 passed
- test_operations_and_verification.py: 18 passed
Total: 77 passed, 0 failed, 0 skipped
```

### 3.2 Frontend Test Suite (Node Test Runner)
```
Command: npm --prefix frontend test
Result: 21 passed in 0.25s (100% pass rate)

Breakdown:
- Frontend Authentication & RBAC Unit Tests: 5 passed
- Frontend Field Operations & Verification Unit Tests: 7 passed
- Frontend Project Portfolio & Workspace Unit Tests: 9 passed
Total: 21 passed, 0 failed
```

### 3.3 Frontend Static Typecheck
```
Command: npm --prefix frontend run typecheck
Result: 0 errors (tsc --noEmit)
```

### 3.4 Frontend Production Build
```
Command: npm --prefix frontend run build
Result: Built in 11.65s (0 errors)
Output:
- dist/index.html (1.04 kB)
- dist/assets/index-D4vbuluM.css (36.66 kB)
- dist/assets/index-UPMi2f_k.js (695.30 kB)
```

---

## 4. Final Verdict and Next Steps

### Verdict: **PASS**

Milestone 4 is complete, verified, secure, and fully compliant with all architectural invariants defined in `AGENTS.md`.

### Recommended Milestone 5 Invariants:
1. **Official Environmental Accounting Engine:** Calculate official project and portfolio totals strictly from active ledger entries (`is_active_ledger_entry = True`).
2. **Dashboard Visualizations:** Implement time-series impact charts using verified dates and target progress bars comparing verified totals against project target quantities.
3. **Interactive Project Maps:** Display verified activity markers and project GeoJSON polygon boundaries using React Leaflet.
4. **Export Engine:** Provide CSV and PDF exports of verified environmental achievements with cryptographic audit references.

*Per agent instructions, all work terminates here. Milestone 5 implementation will commence only upon explicit user approval.*
