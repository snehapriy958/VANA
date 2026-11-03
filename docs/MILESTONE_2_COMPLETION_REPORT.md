# VANA — Milestone 2 Completion Report
### Authentication, RBAC & User Management

**Completion Timestamp:** 2026-11-02T22:39:00+05:30  
**Overall Status:** **COMPLETED & VERIFIED (100% Pass Rate)**  
**Engineering Discipline:** Modular Monolith Architecture, Domain Separation, Single Source of Truth in PostgreSQL.

---

## 1. Implemented Endpoints

All endpoints conform to the VANA REST API Specification (`docs/engineering/04_API_SPECIFICATION.md`) with standard error envelopes `{"detail": {"error_code": "...", "message": "..."}}`:

| HTTP Method | Path | Allowed Roles | Description | Status Code |
|---|---|:---:|---|:---:|
| `POST` | `/api/v1/auth/login` | Public | Validates email/password using Argon2id; returns access token (60 min) & refresh token (7 days). Audits login events. | `200 OK` |
| `POST` | `/api/v1/auth/refresh` | Public (Refresh Token) | Validates refresh token claims & JTI; issues a fresh access token without re-entering credentials. | `200 OK` |
| `GET` | `/api/v1/auth/me` | Authenticated | Retrieves current authenticated user's profile, role, and active status. | `200 OK` |
| `POST` | `/api/v1/auth/logout` | Authenticated | Invalidates client session and records an audit log event in PostgreSQL. | `200 OK` |
| `GET` | `/api/v1/users` | `ADMIN`, `PROJECT_MANAGER` | Lists organization users. `ADMIN` sees all users with filters (`role`, `is_active`); `PM` is scoped strictly to personnel assigned to projects they manage; `FIELD_OFFICER` is denied (`403 Forbidden`). | `200 OK` |
| `POST` | `/api/v1/users` | `ADMIN` only | Provisions a new user account with initial role. Enforces duplicate email conflict rejection (`409 Conflict`) and minimum 8-character password. | `201 Created` |
| `GET` | `/api/v1/users/{id}` | `ADMIN`, Self, Assigned `PM` | Retrieves individual user profile. Non-admins cannot access unrelated personnel. | `200 OK` |
| `PUT` | `/api/v1/users/{id}` | `ADMIN`, Self | Updates full_name, role, or activation status. Prohibits self-role alteration (`SELF_ROLE_CHANGE_PROHIBITED`) and privilege escalation (`UNAUTHORIZED_ROLE_ESCALATION`). | `200 OK` |

---

## 2. Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   VANA AUTHENTICATION FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

  [ Client: React 19 SPA ]                                       [ Server: FastAPI Core ]
             │                                                              │
             │─── 1. POST /api/v1/auth/login { email, password } ──────────>│
             │                                                              │─── 2. Argon2id Verify
             │                                                              │─── 3. Check is_active == True
             │                                                              │─── 4. Audit USER_LOGIN_SUCCESS
             │<── 5. 200 OK { access_token, refresh_token, user } ──────────│
             │                                                              │
    [ In-Memory Context ]                                                   │
    [ sessionStorage Tab-Scope ]                                            │
             │                                                              │
             │─── 6. Protected Request (Authorization: Bearer <token>) ────>│
             │                                                              │─── 7. HS256 JWT Verify
             │                                                              │─── 8. DB User Active Check
             │                                                              │─── 9. Role & Project Check
             │<── 10. 200 OK / 401 Unauthorized / 403 Forbidden ────────────│
```

---

## 3. Authorization Matrix & Boundary Invariants

| Action / Resource | `ADMIN` | `PROJECT_MANAGER` | `FIELD_OFFICER` | Invariant Rule |
|---|:---:|:---:|:---:|---|
| **View Own Profile (`/auth/me`)** | **ALLOW** | **ALLOW** | **ALLOW** | Authenticated identity verification. |
| **List Organization Users (`GET /users`)** | **ALLOW** (All) | **ALLOW** (Assigned Projects Only) | **DENY** (`403 INSUFFICIENT_ROLE`) | Field officers have no user-directory privileges. |
| **Provision User (`POST /users`)** | **ALLOW** | **DENY** (`403 INSUFFICIENT_ROLE`) | **DENY** (`403 INSUFFICIENT_ROLE`) | Only organization administrators can provision accounts. |
| **Change Another User's Role** | **ALLOW** | **DENY** (`403 UNAUTHORIZED_ROLE_ESCALATION`) | **DENY** (`403 UNAUTHORIZED_ROLE_ESCALATION`) | Server-side role modification restriction. |
| **Change Own Role (Self-Role Modification)** | **DENY** (`403 SELF_ROLE_CHANGE_PROHIBITED`) | **DENY** (`403 SELF_ROLE_CHANGE_PROHIBITED`) | **DENY** (`403 SELF_ROLE_CHANGE_PROHIBITED`) | Anti-self-lockout / anti-elevation invariant. |
| **Activate / Deactivate Account** | **ALLOW** | **DENY** (`403 UNAUTHORIZED_STATUS_CHANGE`) | **DENY** (`403 UNAUTHORIZED_STATUS_CHANGE`) | Account suspension restricted to administrators. |
| **Project Boundary Access (`verify_project_access`)** | **ALLOW** (All Projects) | **ALLOW** (Assigned Projects) | **ALLOW** (Assigned Projects) | Cross-project access denied with `403 PROJECT_ACCESS_DENIED`. |

---

## 4. Database Changes

- **Schema Re-use:** No schema alterations were needed. The baseline schema created in Milestone 1A (`users`, `audit_logs`, `project_assignments`) already contained the complete structural foundation, indexes, and foreign keys.
- **Data Integrity Preserved:**
  - `users.email` unique index strictly prevents duplicate email addresses.
  - Foreign key delete restrictions on `audit_logs.actor_id` (`ON DELETE SET NULL`) ensure audit trail permanence even if an actor is archived.
- **Zero Raw Migrations:** Database integrity verified across existing migrations (`0001_initial_schema.py`).

---

## 5. Frontend Changes

1. **Authentication Context (`src/context/AuthContext.tsx`):**
   - In-memory token management with tab-scoped `sessionStorage` fallback (strictly avoids persistent `localStorage` vulnerabilities).
   - Global 401 response interceptor clearing expired sessions.
   - Dynamic Axios token injection via `setAuthToken`.
2. **Protected Route Boundary (`src/components/auth/ProtectedRoute.tsx`):**
   - Unauthenticated visitors redirected to `/login` with return target state.
   - Unauthorized roles presented with a clean 403 Forbidden state explaining required roles and a return action.
3. **Login View (`src/views/auth/LoginView.tsx`):**
   - VANA design system styling (Forest `#183D32`, Ivory `#F5F3EA`, Gold `#D6A76A`, Charcoal `#29332F`).
   - React Hook Form + Zod validation with loading spinner and error alert.
4. **Role-Aware Navigation (`src/components/layout/Sidebar.tsx`):**
   - Dynamically filters menu items based on authenticated role (`ADMIN`, `PROJECT_MANAGER`, `FIELD_OFFICER`).
5. **Interactive Header (`src/components/layout/Header.tsx`):**
   - Displays user full name, email, and role badge (`verified` for ADMIN, `pending` for PM, `sage` for FO).
   - Interactive sign-out button calling backend `/auth/logout`.
6. **User Management View (`src/views/team/UserManagementView.tsx`):**
   - Personnel directory table with live status badges.
   - Modal dialog for user provisioning (`ADMIN` only).
   - Activation / deactivation toggle buttons with instant optimistic UI updates and audit logging.

---

## 6. Security Decisions (Recorded in ADR-013)

- **Password Hashing:** Argon2id ($t=3, m=64\text{ MB}, p=4$) enforced via `app.core.security`.
- **Zero `localStorage` Storage Policy:** JWTs are never written to `localStorage`. Stored in in-memory state and active tab `sessionStorage` only.
- **Audit Sanitization:** Automatic recursive scrubbing of sensitive fields (`password`, `hashed_password`, `token`, `secret`) in `sanitize_state()` before inserting into `audit_logs.previous_state` and `audit_logs.new_state`.
- **Stateless Expiration:** 60-minute access token lifespan, 7-day refresh token lifespan.
- **Deactivated Account Invalidation:** Deactivated accounts (`is_active = False`) are rejected on every request by `get_current_active_user` with HTTP 403, instantly invalidating active access tokens.

---

## 7. Test Coverage & Execution Results

### 7.1 Backend Test Suite (Pytest)
Command: `cd backend; .\.venv\Scripts\pytest -v; cd ..`
- **Result:** **28 passed in 7.12s (100% pass rate)**

```
tests/test_auth_and_rbac.py::test_login_valid_credentials PASSED         [  3%]
tests/test_auth_and_rbac.py::test_login_invalid_password PASSED          [  7%]
tests/test_auth_and_rbac.py::test_login_unknown_email PASSED             [ 10%]
tests/test_auth_and_rbac.py::test_login_deactivated_user PASSED          [ 14%]
tests/test_auth_and_rbac.py::test_auth_me_protected_endpoint_without_token PASSED [ 17%]
tests/test_auth_and_rbac.py::test_auth_me_with_valid_token PASSED        [ 21%]
tests/test_auth_and_rbac.py::test_auth_me_with_expired_token PASSED      [ 25%]
tests/test_auth_and_rbac.py::test_auth_me_with_malformed_token PASSED    [ 28%]
tests/test_auth_and_rbac.py::test_refresh_token_exchange PASSED          [ 32%]
tests/test_auth_and_rbac.py::test_logout_endpoint PASSED                 [ 35%]
tests/test_auth_and_rbac.py::test_admin_can_provision_new_user PASSED    [ 39%]
tests/test_auth_and_rbac.py::test_non_admin_cannot_provision_user PASSED [ 42%]
tests/test_auth_and_rbac.py::test_duplicate_email_rejected_with_409 PASSED [ 46%]
tests/test_auth_and_rbac.py::test_admin_cannot_change_own_role PASSED    [ 50%]
tests/test_auth_and_rbac.py::test_non_admin_cannot_escalate_role PASSED  [ 53%]
tests/test_auth_and_rbac.py::test_field_officer_cannot_list_users PASSED [ 57%]
tests/test_auth_and_rbac.py::test_admin_can_activate_and_deactivate_user PASSED [ 60%]
tests/test_auth_and_rbac.py::test_audit_logs_never_leak_passwords_or_hashes PASSED [ 64%]
tests/test_auth_and_rbac.py::test_verify_project_access_boundaries PASSED [ 67%]
tests/test_auth_and_rbac.py::test_pm_user_listing_is_scoped_to_assigned_projects PASSED [ 71%]
tests/test_database_connection.py::test_direct_database_connection PASSED [ 75%]
tests/test_database_connection.py::test_health_check_endpoint PASSED     [ 78%]
tests/test_migrations.py::test_alembic_two_way_migration_cycle PASSED    [ 82%]
tests/test_models_and_constraints.py::test_insert_and_query_all_tables PASSED [ 85%]
tests/test_models_and_constraints.py::test_partial_unique_index_active_ledger_prevents_double_counting PASSED [ 89%]
tests/test_models_and_constraints.py::test_check_constraint_active_ledger_must_be_verified PASSED [ 92%]
tests/test_models_and_constraints.py::test_check_constraint_rejection_requires_reason_and_notes PASSED [ 96%]
tests/test_models_and_constraints.py::test_foreign_key_delete_restrict_on_activity_creator PASSED [100%]
```

### 7.2 Frontend Unit Tests (Node Test Runner)
Command: `npm test --prefix frontend`
- **Result:** **5 passed in 0.12s (100% pass rate)**
- Verified login validation, email validation, minimum 8-char password, and role-aware navigation filtering for all three roles.

### 7.3 Frontend Typecheck & Build
- `npm run typecheck --prefix frontend` $\to$ **Exit code 0 (0 errors, 0 warnings)**
- `npm run build --prefix frontend` $\to$ **Exit code 0 (1794 modules transformed, built in 8.06s)**

---

## 8. Known Limitations

1. **Project Roster Assignment Management:** The `/projects/{id}/assignments` endpoint is designed in the API spec and will be activated alongside Project CRUD in Milestone 3. The authorization boundary dependency (`verify_project_access`) is already fully implemented and verified.
2. **Audit Log UI Viewer:** Administrative users can inspect audit records in PostgreSQL; the dedicated frontend table for `/audit` will be fully activated in Milestone 8.

---

## 9. Manual Verification Instructions

To verify the implementation end-to-end:

1. **Start Backend Server:**
   ```powershell
   cd backend
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
   ```
2. **Start Frontend Development Server:**
   ```powershell
   cd frontend
   npm run dev
   ```
3. **Open Browser at `http://localhost:5173/login`:**
   - Attempt login with invalid credentials $\to$ Observe 401 error alert in UI.
   - Sign in with an `ADMIN` account $\to$ Verify access to Dashboard and Team Management.
   - Navigate to `/team` $\to$ Observe personnel directory, open Provision User modal dialog, and provision a new Field Officer.
   - Toggle Activation/Deactivation on a non-self user $\to$ Verify immediate status change and corresponding audit log row in PostgreSQL `audit_logs`.
   - Sign out using the Header logout button $\to$ Verify redirection to `/login` and session clearance.

---

**Next Milestone:** Milestone 3 (Project Portfolio, Boundary Definitions & Targets). Implementation is paused awaiting review and explicit sign-off.
