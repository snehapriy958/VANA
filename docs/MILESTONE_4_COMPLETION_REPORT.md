# VANA — Milestone 4 Completion Report
## Field Operations, Evidence Management & Activity Verification

> **Status:** Completed & Verified  
> **Date:** 2026-11-03  
> **Milestone:** 4  
> **Related Documents:** `AGENTS.md`, `DECISION_LOG.md` (ADR-004, ADR-006, ADR-009, ADR-011, ADR-012, ADR-016), `IMPLEMENTATION_STATUS.md`  

---

## 1. Executive Summary

Milestone 4 has been fully implemented, integrated, and verified across both backend (FastAPI / SQLAlchemy 2.x) and frontend (React 19 / Vite / Tailwind / shadcn) codebases. The platform now delivers an end-to-end field activity reporting, evidence management, and review verification system anchored to PostgreSQL and the 5-ledger environmental math engine.

All deliverables strictly uphold the permanent engineering invariants defined in `AGENTS.md`:
* **Rule 5 (Anti-Self-Verification Gate):** Verifiers are strictly prohibited from verifying their own submissions (`verifier_id != creator_id`), enforced server-side with `HTTP 403 Forbidden` (`SELF_VERIFICATION_PROHIBITED`) and in the UI with disabled actions and policy notices.
* **Single Active Ledger Invariant:** Enforced by PostgreSQL partial unique index `uq_activity_single_active_ledger ON activity_revisions(activity_id) WHERE is_active_ledger_entry = TRUE`. Exactly one active verified revision may exist per logical activity.
* **Amendment Accounting & Lineage:** Amendments maintain the previously verified revision active in the official ledger until formally reviewed. Net adjustments are tracked precisely ($\Delta = Q_{\text{amended}} - Q_{\text{verified}}$) without synthetic inflation.
* **Evidence Security:** Files are validated for MIME type (`image/jpeg`, `image/png`, `image/webp`, `application/pdf`) and size ($\le 10\text{ MB}$), stored with SHA-256 content addressing, and streamed strictly through authenticated, project-authorized API endpoints.
* **Testing & Build Verification:**
  * **Backend:** **76/76 tests passed (100% pass rate in 38.19s)**.
  * **Frontend:** **21/21 tests passed (100% pass rate in 0.19s)**.
  * **TypeScript Typecheck:** Clean (**0 errors**).
  * **Production Build:** Clean (**1801 modules transformed in 9.13s**).

---

## 2. Implemented Endpoints & REST Architecture

All endpoints are mounted under `/api/v1` and protected by independent server-side JWT authentication and RBAC dependency guards.

### 2.1 Field Operations & Reporting (`/api/v1/operations`)

| Method | Endpoint | Allowed Roles | Description | Status Codes |
|---|---|:---:|---|:---:|
| `POST` | `/api/v1/operations/activities` | `ADMIN`, Assigned `PM`, Assigned `FO` | Submits a new field activity report with photo evidence (`multipart/form-data`). Creates parent `FieldActivity` and initial Revision 1 (`PENDING`). | `201`, `400`, `401`, `403`, `404`, `422` |
| `GET` | `/api/v1/operations/activities` | `ADMIN`, Assigned `PM`, Assigned `FO` | Lists field activities scoped to user's permitted projects. Supports `project_id`, `status`, `metric_code`, and `is_archived` filters. | `200`, `401` |
| `GET` | `/api/v1/operations/activities/{id}` | `ADMIN`, Assigned `PM`, Assigned `FO` | Retrieves logical activity container with full immutable revision history, evidence files, and net pending adjustments. | `200`, `401`, `403`, `404` |
| `POST` | `/api/v1/operations/activities/{id}/revisions` | `ADMIN`, Assigned `PM`, Assigned `FO` | Submits an amendment or correction revision (Revision $N+1$). Prevents concurrent duplicate pending revisions (`PENDING_REVISION_EXISTS`). | `201`, `400`, `401`, `403`, `404`, `422` |
| `DELETE` | `/api/v1/operations/activities/{id}` | `ADMIN`, Assigned `PM` | Soft-deletes/archives an activity; deactivates any active ledger entry so it ceases contributing to official achievements. | `200`, `401`, `403`, `404` |
| `GET` | `/api/v1/operations/evidence/{id}` | `ADMIN`, Assigned `PM`, Assigned `FO` | Streams physical evidence file to authorized project team members. Verifies project assignment authorization before serving bytes. | `200`, `401`, `403`, `404` |

### 2.2 Activity Verification Centre (`/api/v1/verification`)

| Method | Endpoint | Allowed Roles | Description | Status Codes |
|---|---|:---:|---|:---:|
| `GET` | `/api/v1/verification/queue` | `ADMIN`, Assigned `PM` | Fetches pending activity revisions awaiting review. Field Officers rejected with `HTTP 403 Forbidden` (`INSUFFICIENT_ROLE`). | `200`, `401`, `403` |
| `POST` | `/api/v1/verification/revisions/{id}/decision` | `ADMIN`, Assigned `PM` | Records digital verification decision (`VERIFIED` or `REJECTED`). Strictly enforces Anti-Self-Verification Gate and atomic ledger switches. | `200`, `400`, `401`, `403`, `404`, `422` |

*(Endpoints are additionally accessible under `/api/v1/operations/verification/...` as documented in `04_API_SPECIFICATION.md`)*

---

## 3. Database Schema & Ledger Architecture

Milestone 4 utilizes the authoritative relational schema established in Milestone 1A:

```
┌────────────────────────────────────────────────────────────────────────┐
│  FIELD OPERATIONS RELATIONAL LINEAGE                                   │
│                                                                        │
│  projects ──< field_activities ──< activity_revisions ──< evidence_files│
│                     │                       │                          │
│                     │                       ├── verifier_id (users.id) │
│                     └── created_by_id       └── is_active_ledger_entry │
│                         (users.id)          (Partial Unique Index)     │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Schema Invariants & Constraints Enforced
1. **Partial Unique Index (`uq_activity_single_active_ledger`):**
   `UNIQUE (activity_id) WHERE is_active_ledger_entry = TRUE`
   Mathematically guarantees that no single activity can ever possess more than one active revision contributing to official verified totals.
2. **Active Ledger Verification Constraint (`chk_active_ledger_verified`):**
   `CHECK ((is_active_ledger_entry = FALSE) OR (is_active_ledger_entry = TRUE AND status = 'VERIFIED'))`
   Ensures pending or rejected revisions can never enter the active environmental ledger.
3. **Rejection Audit Requirement (`chk_rejection_reason_required`):**
   `CHECK ((status != 'REJECTED') OR (status = 'REJECTED' AND rejection_reason_code IS NOT NULL AND review_notes IS NOT NULL))`
   Mandates both reason code and feedback comment for all rejections.
4. **Digital Signature Requirement (`chk_verification_signature_required`):**
   `CHECK ((status != 'VERIFIED') OR (status = 'VERIFIED' AND verifier_id IS NOT NULL AND verified_at IS NOT NULL))`
   Guarantees non-repudiation and reviewer identity on all verified revisions.
5. **Foreign Key Restrict (`ondelete="RESTRICT"`):**
   Prevents deleting users who have submitted activities or verified revisions, preserving audit trail integrity.

---

## 4. Environmental Accounting & Calculation Logic

VANA maintains five distinct accounting ledgers per metric code without synthetic multipliers:

1. **Current Verified Quantity ($A_v$):**
   $$\sum_{a \in \mathcal{A}} R_{\text{active}}(a).\text{quantity} \quad \text{where } R.\text{is\_active\_ledger\_entry} = \text{TRUE}$$
2. **Current Pending Quantity ($Q_p$):**
   $$\sum_{a \in \mathcal{A}} \begin{cases} 
   R_{\text{current}}(a).\text{quantity} & \text{if unverified} \\
   \max(0, R_{\text{current}}(a).\text{quantity} - R_{\text{active}}(a).\text{quantity}) & \text{if amendment}
   \end{cases}$$
3. **Current Rejected Quantity ($Q_r$):**
   Sum of current submissions in `REJECTED` state where no subsequent approved revision exists.
4. **Historical Rejected Submission Count:**
   Total historical count of all revision records ever rejected.
5. **Reported Quantity:**
   Sum of claimed quantities across all active non-archived logical activities: Current Verified + Net Pending Claims.

### Net Adjustment Accounting Example:
* **Initial Submission:** Field officer reports $100\text{ trees}$ $\to$ $A_v = 0$, $Q_p = 100$.
* **Initial Approval:** Reviewer verifies Rev 1 $\to$ $A_v = 100$, $Q_p = 0$.
* **Amendment Submission:** Field officer amends to $160\text{ trees}$ $\to$ Rev 1 remains active in ledger ($A_v = 100$), Net Pending Adjustment $= +60\text{ trees}$.
* **Amendment Approval:** Reviewer verifies Rev 2 $\to$ Rev 1 deactivated, Rev 2 activated $\to$ $A_v = 160$, $Q_p = 0$.
* **Alternative (Amendment Rejected):** If Rev 2 is rejected $\to$ Rev 1 remains active ($A_v = 100$). Official progress is untouched.

---

## 5. Security & Authorization Boundaries

### 5.1 Anti-Self-Verification Gate (Rule 5)
* **Backend Enforcement:**
  ```python
  if current_user.id == activity.created_by_id:
      raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail={
              "error_code": "SELF_VERIFICATION_PROHIBITED",
              "message": "Policy Violation: You cannot verify an activity submission you authored."
          }
      )
  ```
* **Frontend Enforcement:**
  In `VerificationCentreView.tsx`, if `item.can_verify === false`, both `Approve` and `Reject` buttons are disabled, and a high-contrast banner cites Rule 5.

### 5.2 Role Scoping & Project Access
* **`ADMIN`:** Organization-wide verification authority; can review any pending revision.
* **`PROJECT_MANAGER`:** Verification authority strictly scoped to projects where an active `ProjectAssignment` row exists. Cross-project reviews are rejected (`HTTP 403 PROJECT_ACCESS_DENIED`).
* **`FIELD_OFFICER`:** Submitter role only. Accessing `/api/v1/verification/queue` or submitting a decision is rejected (`HTTP 403 INSUFFICIENT_ROLE`).
* **Evidence Download:** Accessing `/api/v1/operations/evidence/{id}` validates that the requester has project access before streaming bytes, preventing unauthorized access to field photos.

---

## 6. Frontend Views & User Experience

### 6.1 Field Operations View (`/operations`)
* **Header & Action Bar:** Forest green theme with "Report Field Activity" modal launcher and real-time refresh.
* **Filter Controls:** Search query input, Project selector, Metric selector, and Status pill tabs (`All`, `Pending`, `Verified`, `Rejected`).
* **Activity Card Grid:**
  * Project code and name
  * Metric name and canonical unit
  * Status badge (`Verified`, `Pending Review`, `Rejected`)
  * Verified total vs Net pending adjustment pill (`+60 trees`, `-20 kg`)
  * Date, submitter name, and attached photo count
* **Submission Modal (Screen 06 Mobile-First):**
  * Project and Metric dropdowns
  * Unit picker constrained strictly to supported units
  * Positive quantity validation
  * Browser GPS integration via `navigator.geolocation` with accuracy indicator (warning if $> 25\text{m}$)
  * Multi-photo uploader with instant thumbnail previews and deletion
  * Observation notes textarea
  * Draft persistence via `sessionStorage` (`vana_field_activity_draft`)
* **Inspection & Lineage Drawer:**
  * Verified total balance sheet
  * Complete revision timeline (Rev 1, Rev 2...) showing status, reviewer name, timestamp, and notes
  * Rejection feedback box with reason code and review comments
  * Photo gallery with click-to-zoom Lightbox
  * "Submit Amendment" launcher and "Archive Activity" soft-delete action

### 6.2 Verification Centre View (`/verification`)
* **Split-Screen Layout (Screen 07):**
  * **Left Pane (40%):** Triage queue cards sorted chronologically. Displays submitter, project, metric, claimed quantity, amendment badge, and "Your Submission" lock tag.
  * **Right Pane (60%):** Deep inspection canvas detailing submitter metadata, metric claim, net adjustment comparison, GPS coordinates, field notes, and photo gallery with lightbox.
* **Anti-Self-Verification Protection:** Approve and Reject buttons disabled if `item.can_verify === false` with clear policy feedback.
* **Approval Flow:** Confirmation dialog with optional sign-off notes; immediate removal from queue.
* **Rejection Flow:** Modal requiring selection of calibrated `rejection_reason_code` (`INSUFFICIENT_EVIDENCE`, `COORDINATES_MISMATCH`, `INCORRECT_UNIT_OR_QUANTITY`, `DUPLICATE_SUBMISSION`, `DATA_ENTRY_ERROR`) and mandatory review notes.

---

## 7. Verification & Automated Test Suite Results

### 7.1 Backend Test Results (`backend/tests/`)
* **Command:** `backend\.venv\Scripts\pytest backend\tests`
* **Result:** **76 passed in 38.19s (100% pass rate)**

| Test Module | Tests | Status | Scope |
|---|:---:|:---:|---|
| `test_auth_and_rbac.py` | 28 | PASSED | Authentication, JWT, Argon2id, RBAC boundaries |
| `test_database_connection.py` | 2 | PASSED | Live PostgreSQL connection and `/health` probe |
| `test_migrations.py` | 1 | PASSED | Two-way migration cycle (`upgrade` $\leftrightarrow$ `downgrade`) |
| `test_models_and_constraints.py` | 5 | PASSED | Partial unique index, check constraints, FK restrict |
| `test_operations_and_verification.py` | 17 | PASSED | Activity reporting, amendments, evidence upload/streaming, anti-self-verification gate, active ledger switches, rejection feedback, race conditions, and audit logs |
| `test_projects_and_targets.py` | 18 | PASSED | Projects, assignments, GeoJSON RFC 7946, targets |
| `test_token_lifecycle.py` | 5 | PASSED | Refresh token advisory lock serialization |
| **Total** | **76** | **PASSED** | **100% Pass Rate** |

### 7.2 Frontend Test Results (`frontend/tests/`)
* **Command:** `npm --prefix frontend test`
* **Result:** **21 passed in 0.19s (100% pass rate)**

| Test Suite | Tests | Status | Scope |
|---|:---:|:---:|---|
| `auth.test.mjs` | 5 | PASSED | Auth schemas, password strength, role navigation |
| `projects.test.mjs` | 9 | PASSED | Project schemas, GeoJSON polygon validation, target inputs |
| `operations.test.mjs` | 7 | PASSED | Activity submission schemas, net adjustment calculations, Anti-Self-Verification Gate logic, rejection reason validation |
| **Total** | **21** | **PASSED** | **100% Pass Rate** |

### 7.3 Frontend Typecheck & Build
* `npm --prefix frontend run typecheck`: **0 errors** (exited with code 0).
* `npm --prefix frontend run build`: **0 errors** (1801 modules transformed in 9.13s, production bundle generated in `frontend/dist/`).

---

## 8. Permanent Engineering Compliance Checklist

| Rule # | Invariant / Policy | Enforcement Mechanism | Compliance Verdict |
|---|---|---|:---:|
| **Rule 1** | Modular Monolith Architecture | Domain separation maintained (`operations`, `verification`) in monolith. | **COMPLIANT** |
| **Rule 2** | Approved Tech Stack Only | Zero unapproved dependencies; FastAPI, PostgreSQL, React 19, Vite, Tailwind. | **COMPLIANT** |
| **Rule 3** | PostgreSQL Single Source of Truth | Relational models and constraints authoritative; zero ephemeral state. | **COMPLIANT** |
| **Rule 4** | Server-Side Independent Authorization | Role boundaries and project scoping verified on every endpoint. | **COMPLIANT** |
| **Rule 5** | Anti-Self-Verification Gate | `verifier_id != creator_id` strictly enforced with HTTP 403. | **COMPLIANT** |
| **Rule 6** | Immutable Audit Trail Integrity | State diffs recorded for all activity lifecycle mutations. | **COMPLIANT** |
| **Rule 7** | Verified-Only Official Achievements | Only approved revisions with `is_active_ledger_entry = True` count. | **COMPLIANT** |
| **Rule 8** | Strict Dimensionality & Conversion Rules | Cross-metric aggregation strictly forbidden; units validated against catalog. | **COMPLIANT** |
| **Rule 9** | Data Grounding & Scientific Rigor | Zero synthetic multipliers; real measurement records only. | **COMPLIANT** |
| **Rule 10** | Milestone-by-Milestone Workflow | Milestone 4 fully implemented and audited; Milestone 5 strictly paused. | **COMPLIANT** |
| **Rule 11** | Rigorous Automated Testing | 76 backend tests + 21 frontend tests passing; 100% green. | **COMPLIANT** |
| **Rule 12** | Design Tokens & System Consistency | Forest Green (`#183D32`), Ivory (`#F5F3EA`), Sage (`#A8B99B`), Manrope & Inter fonts. | **COMPLIANT** |

---

## 9. Conclusion & Next Steps

Milestone 4 is complete, fully tested, documented, and ready for acceptance audit.

**Next Milestone:** Milestone 5 (Environmental Ledger & Math Engine / Living Earth Map) remains strictly un-commenced pending explicit user authorization.
