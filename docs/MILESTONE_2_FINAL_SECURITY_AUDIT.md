# VANA — Milestone 2 Final Security Audit
### Authentication, RBAC, JWT Lifecycle, and Audit Integrity

**Audit Execution Timestamp:** 2026-11-02T22:48:00+05:30  
**Target Milestone:** Milestone 2 — Authentication, RBAC & User Management  
**Lead Auditor:** VANA Security Architect & Lead Software Engineer  
**Audit Scope:** Independent, code-level and runtime verification of authentication protocols, JWT mechanics, Argon2id hashing, role-based access control, project-level authorization boundaries, audit trail immutability, and frontend token handling.

---

## 1. Source Files Inspected

The following source files were thoroughly audited:

| Component | File Path | Scope of Inspection |
|---|---|---|
| **Core Security** | [`backend/app/core/security.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/core/security.py) | Argon2id parameters, JWT claims payload, algorithm restriction (`HS256`), signing, and decoding logic. |
| **Configuration** | [`backend/app/core/config.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/core/config.py) | Environment settings, production refusal of default secrets, JWT lifespan, and CORS origins. |
| **Auth Domain** | [`backend/app/domains/auth/router.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/auth/router.py) | Login, refresh, profile (`/me`), and logout endpoints. |
| **Auth Services** | [`backend/app/domains/auth/services.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/auth/services.py) | Password verification, token issuance, refresh token rotation/revocation, duplicate checks, and user updates. |
| **Auth Dependencies**| [`backend/app/domains/auth/dependencies.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/auth/dependencies.py) | `get_current_user`, `get_current_active_user`, `require_roles`, and `verify_project_access`. |
| **User Management** | [`backend/app/domains/auth/users_router.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/auth/users_router.py) | User directory listing, provisioning, profile lookup, and status toggle endpoints. |
| **Audit Service** | [`backend/app/domains/audit/services.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/audit/services.py) | Audit logging, event persistence, and automated credential/hash sanitization (`sanitize_state`). |
| **Database Models** | [`backend/app/models.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/models.py) | Relational constraints, foreign keys, indexes, and unique constraints on `users` and `audit_logs`. |
| **Frontend Auth** | [`frontend/src/context/AuthContext.tsx`](file:///c:/Developers/Sneha/Projects/VANA/frontend/src/context/AuthContext.tsx) | In-memory token management, `sessionStorage` scope, login/logout lifecycles, and 401 interceptor. |
| **Frontend Client** | [`frontend/src/services/apiClient.ts`](file:///c:/Developers/Sneha/Projects/VANA/frontend/src/services/apiClient.ts) | Dynamic Bearer token header injection, URL sanitization, and 401 callback listener. |
| **Route Boundary** | [`frontend/src/components/auth/ProtectedRoute.tsx`](file:///c:/Developers/Sneha/Projects/VANA/frontend/src/components/auth/ProtectedRoute.tsx) | Client-side route blocking, loading state, unauthenticated redirection, and 403 Forbidden UI. |
| **Login View** | [`frontend/src/views/auth/LoginView.tsx`](file:///c:/Developers/Sneha/Projects/VANA/frontend/src/views/auth/LoginView.tsx) | React Hook Form, Zod schema validation, error display, and secure input handling. |

---

## 2. Actual JWT Lifecycle & Session Security

### 2.1 Complete Token Lifecycle: LOGIN → ACCESS → REFRESH → LOGOUT

1. **Authentication (`POST /api/v1/auth/login`):**
   - Credentials validated via `verify_password(login_data.password, user.hashed_password)`.
   - Generates signed Access Token:
     - Algorithm: strictly `HS256`.
     - Claims: `sub` (User UUID), `email`, `role`, `exp` (+60 min), `iat` (now), `type: "access"`.
   - Generates signed Refresh Token:
     - Algorithm: strictly `HS256`.
     - Claims: `sub` (User UUID), `jti` (unique UUIDv4 string), `exp` (+7 days), `iat` (now), `type: "refresh"`.
   - Records audit event `REFRESH_TOKEN_ISSUED` in PostgreSQL associating `entity_id = jti_uuid` with the user.
   - Records audit event `USER_LOGIN_SUCCESS`.

2. **Access Token Usage on Protected Endpoints:**
   - Transport: `Authorization: Bearer <access_token>`.
   - Decoded with `algorithms=["HS256"]`.
   - Validates `payload["type"] == "access"` (refresh tokens rejected with `401 INVALID_TOKEN_TYPE`).
   - Fetches live database record `user = await db.get(User, user_uuid)`.
   - If user is deactivated (`is_active == False`): rejected immediately with `403 ACCOUNT_DEACTIVATED`.

3. **Token Refresh (`POST /api/v1/auth/refresh`):**
   - Decodes refresh token with `algorithms=["HS256"]`.
   - Validates `payload["type"] == "refresh"` (access tokens rejected with `401 INVALID_TOKEN_TYPE`).
   - Validates `jti` claim exists and is valid UUID.
   - **Anti-Replay Verification:** Checks PostgreSQL `audit_logs` table for existing `REFRESH_TOKEN_CONSUMED` or `REFRESH_TOKEN_REVOKED` records for `entity_id = old_jti`. If found, rejects with `401 TOKEN_REVOKED`.
   - **Logout Verification:** Checks PostgreSQL `audit_logs` table for any `USER_LOGOUT` events for this user with `created_at >= token_iat`. If found, rejects with `401 TOKEN_REVOKED`.
   - **Single-Use Rotation:** Marks `old_jti` as `REFRESH_TOKEN_CONSUMED` in PostgreSQL.
   - Issues new access token and newly rotated refresh token with new `new_jti`.
   - Marks `new_jti` as `REFRESH_TOKEN_ISSUED` in PostgreSQL.

4. **Session Logout (`POST /api/v1/auth/logout`):**
   - Accepts optional `refresh_token` in body.
   - If provided, decodes `jti` and records `action_type="REFRESH_TOKEN_REVOKED"` for that `jti`.
   - Persists immutable `USER_LOGOUT` audit log in PostgreSQL with exact timestamp.
   - All refresh tokens issued prior to this timestamp are rejected upon presentation at `/auth/refresh`.

---

## 3. Refresh-Token Revocation Strategy & Findings

### 3.1 Investigation Findings: Does Logout Revoke Refresh Tokens?

- **Initial State:** Initially, stateless refresh tokens had no revocation mechanism beyond client-side deletion, meaning a stolen refresh token would technically remain valid until its 7-day cryptographic expiration.
- **Architectural Fix Implemented:** Designed and implemented a database-backed, audit-anchored JTI tracking mechanism leveraging the existing `audit_logs` PostgreSQL table:
  1. Every refresh token embeds an immutable `jti` UUID.
  2. Single-use rotation is strictly enforced: consuming a refresh token records `REFRESH_TOKEN_CONSUMED`. Replay attempts fail with `401 TOKEN_REVOKED`.
  3. Session termination on logout is strictly enforced: `/auth/logout` records both an explicit `REFRESH_TOKEN_REVOKED` for the provided JTI and an immutable `USER_LOGOUT` timestamp that invalidates all previously issued refresh tokens for that user.
- **Verification Result:** Fully verified by automated tests `test_refresh_token_reuse_after_rotation_is_denied` and `test_refresh_token_after_logout_is_denied`.

---

## 4. Token Storage Analysis & Frontend Security

### 4.1 Token Storage Audit

| Storage Mechanism | Tokens Stored | Lifespan / Scope | XSS Implication |
|---|---|---|---|
| **React Memory State** | `accessToken` | Component lifecycle (cleared on page reload) | Protected from disk persistence; accessible to in-page XSS. |
| **`sessionStorage`** | `vana_session_access_token`<br>`vana_session_refresh_token` | Browser Tab session (destroyed on tab close) | **Accessible to in-page XSS**. Does NOT protect against active tab XSS; eliminates persistent storage on shared field devices. |
| **`localStorage`** | **NONE (0% usage)** | N/A | **Compliant:** Persistent `localStorage` is completely avoided. |
| **URL Parameters** | **NONE (0% usage)** | N/A | **Compliant:** Zero tokens appear in URLs or query strings. |
| **Console Logs** | **NONE (0% usage)** | N/A | **Compliant:** Zero tokens or hashes are logged to browser console. |

### 4.2 XSS Implications of `sessionStorage`

> [!CAUTION]
> **Definitive Security Note on `sessionStorage`:**  
> `sessionStorage` does **not** protect tokens from Cross-Site Scripting (XSS). Any malicious script executing in the document context has full access to `window.sessionStorage`. The exclusive security benefit of `sessionStorage` over `localStorage` is **temporal scope**: tokens are not persisted to non-volatile disk storage across browser restarts, and closing the active browser tab immediately purges the session keys.

### 4.3 Architecture Review: HttpOnly Cookies vs. Bearer Tokens

- **Trade-off Analysis:**
  - **HttpOnly, Secure, SameSite Cookies:** Prevents script-based extraction of refresh tokens. However, it requires a shared origin/domain between frontend and backend, mandates CSRF protection mechanisms (e.g. double-submit cookie or SameSite=Strict), and complicates mobile, CLI, and third-party developer integrations.
  - **Stateless Bearer Tokens in JSON Payload (Current Approved Stack):** Fully cross-origin compatible across Vercel and Render deployments, eliminates CSRF attack vectors, and supports multi-client architecture.
- **Decision:** Retain the approved stateless Bearer token architecture as defined in ADR-002 and ADR-013, with JTI rotation and logout revocation tracking in PostgreSQL.

---

## 5. Role Freshness & Authorization Verification

### 5.1 The Role Downgrade Sequence Test

The following sequence was executed via automated integration test `test_old_access_jwt_after_role_downgrade_is_denied`:
1. Created user with role `PROJECT_MANAGER`.
2. Issued a valid access token claiming `role = "PROJECT_MANAGER"`.
3. An administrator downgraded the user to `FIELD_OFFICER` directly in PostgreSQL.
4. User presented the original valid (non-expired) JWT to `GET /api/v1/users` (a PM-only endpoint).
5. **Result: HTTP 403 Forbidden (`INSUFFICIENT_ROLE`). Access was immediately denied.**

**Root Cause of Success:**  
`backend/app/domains/auth/dependencies.py` queries `user = await db.get(User, user_uuid)` on every single request. The authorization dependency `require_roles` checks `current_user.role`, which is the **live, authoritative role from PostgreSQL**, completely ignoring the stale claim in the JWT.

---

## 6. Project Assignment Isolation

Inspected `verify_project_access` in [`backend/app/domains/auth/dependencies.py`](file:///c:/Developers/Sneha/Projects/VANA/backend/app/domains/auth/dependencies.py):

- **Project Existence Check:** Validates `Project` exists in database first via `await db.get(Project, project_id)`. Nonexistent projects return `404 PROJECT_NOT_FOUND`.
- **Admin Access:** `ADMIN` possesses organization-wide access to any existing project (`return None` bypasses roster check).
- **Project Manager Scope:** `PROJECT_MANAGER` can access only projects where an active `ProjectAssignment` row exists. Unassigned projects produce `403 PROJECT_ACCESS_DENIED`.
- **Field Officer Scope:** `FIELD_OFFICER` can access only assigned projects. Attempting PM-restricted operations produces `403 INSUFFICIENT_PROJECT_ROLE`.
- **Directory Isolation:** `list_users` for a `PROJECT_MANAGER` returns only users who share active project assignments with that PM. Cross-project directory enumeration is impossible.

---

## 7. User Management Security & Invariants

- **Duplicate Email Prevention:** Enforced at both application service level (`409 EMAIL_ALREADY_EXISTS`) and PostgreSQL database level (`UNIQUE INDEX ix_users_email`).
- **Password Strength:** Enforced $\ge 8$ characters in Pydantic schema (`UserCreate`).
- **Argon2id Hashing:** Argon2id ($t=3, m=64\text{ MB}, p=4$) verified.
- **Hash Exposure Prevention:** `UserRead` model explicitly omits `hashed_password`. Verified that password hashes never appear in HTTP response bodies.
- **Audit Sanitization:** `sanitize_state()` automatically strips `password`, `hashed_password`, `token`, and `secret`.
- **Anti-Self-Role Modification:** Users (including administrators) are strictly prohibited from changing their own role (`403 SELF_ROLE_CHANGE_PROHIBITED`).
- **Privilege Escalation Prevention:** Non-admins cannot alter roles (`403 UNAUTHORIZED_ROLE_ESCALATION`) or change activation status (`403 UNAUTHORIZED_STATUS_CHANGE`).
- **Directory Privacy:** `FIELD_OFFICER` cannot list users (`403 INSUFFICIENT_ROLE`).

---

## 8. Audit Log Integrity & Sanitization

- **Failed Logins:** Audited as `USER_LOGIN_FAILED` recording only the normalized email and failure reason. Passwords and credential attempts are never recorded.
- **Successful Logins:** Audited as `USER_LOGIN_SUCCESS`.
- **Role Mutations:** Audited as `USER_ROLE_CHANGED` recording `previous_state` and `new_state` diffs.
- **Account Status Mutations:** Audited as `USER_ACTIVATED` and `USER_DEACTIVATED`.
- **Session Terminations:** Audited as `USER_LOGOUT`.
- **Immutability:** No `PUT`, `PATCH`, or `DELETE` endpoints exist for the `audit_logs` domain. Records are write-once and permanent in PostgreSQL.

---

## 9. Automated Security Test Results

All 36 backend tests and 5 frontend unit tests passed with a **100% pass rate**:

### 9.1 Backend Security Test Suite
- **Command:** `cd backend; .\.venv\Scripts\pytest -v; cd ..`
- **Results:** **36 passed in 9.09s**

| Test Identifier | Category | Result |
|---|---|:---:|
| `test_login_valid_credentials` | Authentication | **PASSED** |
| `test_login_invalid_password` | Authentication | **PASSED** |
| `test_login_unknown_email` | Authentication | **PASSED** |
| `test_login_deactivated_user` | Authentication | **PASSED** |
| `test_auth_me_protected_endpoint_without_token` | Token Validation | **PASSED** |
| `test_auth_me_with_valid_token` | Token Validation | **PASSED** |
| `test_auth_me_with_expired_token` | Token Validation | **PASSED** |
| `test_auth_me_with_malformed_token` | Token Validation | **PASSED** |
| `test_refresh_token_exchange` | Token Lifecycle | **PASSED** |
| `test_logout_endpoint` | Token Lifecycle | **PASSED** |
| `test_admin_can_provision_new_user` | User Management | **PASSED** |
| `test_non_admin_cannot_provision_user` | RBAC Enforcement | **PASSED** |
| `test_duplicate_email_rejected_with_409` | Data Integrity | **PASSED** |
| `test_admin_cannot_change_own_role` | RBAC Invariant | **PASSED** |
| `test_non_admin_cannot_escalate_role` | RBAC Invariant | **PASSED** |
| `test_field_officer_cannot_list_users` | RBAC Invariant | **PASSED** |
| `test_admin_can_activate_and_deactivate_user` | Account Lifecycle | **PASSED** |
| `test_audit_logs_never_leak_passwords_or_hashes` | Audit Security | **PASSED** |
| `test_verify_project_access_boundaries` | Project RBAC | **PASSED** |
| `test_pm_user_listing_is_scoped_to_assigned_projects` | Project Isolation | **PASSED** |
| `test_old_access_jwt_after_role_downgrade_is_denied` | **Role Freshness** | **PASSED** |
| `test_refresh_token_reuse_after_rotation_is_denied` | **Anti-Replay / Revocation** | **PASSED** |
| `test_refresh_token_after_logout_is_denied` | **Session Termination** | **PASSED** |
| `test_access_token_used_as_refresh_token_is_rejected` | **Type Confusion** | **PASSED** |
| `test_refresh_token_used_as_access_token_is_rejected` | **Type Confusion** | **PASSED** |
| `test_deactivated_user_with_existing_valid_token_is_denied` | **Deactivation Guard** | **PASSED** |
| `test_nonexistent_project_access_returns_404` | **Input Boundary** | **PASSED** |
| `test_production_environment_refuses_insecure_default_secret`| **Config Hardening** | **PASSED** |
| `test_direct_database_connection` | Database Core | **PASSED** |
| `test_health_check_endpoint` | Health Probe | **PASSED** |
| `test_alembic_two_way_migration_cycle` | Migrations | **PASSED** |
| `test_insert_and_query_all_tables` | ORM Integrity | **PASSED** |
| `test_partial_unique_index_active_ledger_prevents_double_counting`| Invariant Index | **PASSED** |
| `test_check_constraint_active_ledger_must_be_verified` | Check Constraint | **PASSED** |
| `test_check_constraint_rejection_requires_reason_and_notes` | Check Constraint | **PASSED** |
| `test_foreign_key_delete_restrict_on_activity_creator` | Foreign Key Guard | **PASSED** |

### 9.2 Frontend Tests, Typecheck, and Production Build
- `npm test --prefix frontend`: **5 passed in 0.14s (100% pass rate)**.
- `npm run typecheck --prefix frontend`: **0 errors, 0 warnings (Exit code 0)**.
- `npm run build --prefix frontend`: **1794 modules transformed, built in 8.37s (Exit code 0)**.

---

## 10. Security Audit Findings & Fixes Applied

### 10.1 Critical Findings
- **CRIT-01: Production Acceptance of Insecure Default JWT Secrets**
  - *Risk:* In production mode, the application previously lacked validation enforcing custom high-entropy signing keys.
  - *Fix Applied:* Added `@model_validator(mode="after")` in `backend/app/core/config.py` that raises a fatal `ValueError` if `ENVIRONMENT="production"` is started with a default or $< 32$-character secret. Verified by `test_production_environment_refuses_insecure_default_secret`.

### 10.2 High-Priority Findings
- **HIGH-01: Unenforced Refresh Token Rotation & Session Revocation**
  - *Risk:* Refresh tokens were stateless and lacked server-side rotation/revocation tracking, allowing replay attacks and post-logout refresh token usage.
  - *Fix Applied:* Implemented database-backed JTI tracking and `USER_LOGOUT` timestamp invalidation in `backend/app/domains/auth/services.py` and `router.py`. Reusing consumed refresh tokens or using refresh tokens after logout is now strictly blocked with HTTP 401 `TOKEN_REVOKED`. Verified by `test_refresh_token_reuse_after_rotation_is_denied` and `test_refresh_token_after_logout_is_denied`.
- **HIGH-02: Nonexistent Project ID Handling in Project Access Dependency**
  - *Risk:* When an admin passed a random nonexistent UUID to `verify_project_access`, the dependency returned `None` without checking project existence in PostgreSQL.
  - *Fix Applied:* Added project existence check against `projects` table first. Nonexistent project IDs now consistently return `404 PROJECT_NOT_FOUND`. Verified by `test_nonexistent_project_access_returns_404`.

### 10.3 Medium-Priority Findings
- **MED-01: Trailing Slash URL Inconsistency in API Client**
  - *Risk:* Unsanitized `VITE_BACKEND_URL` environment variables with trailing slashes caused duplicated slashes in endpoint paths.
  - *Fix Applied:* Added `.trim().replace(/\/+$/, "")` normalization in `apiClient.ts`.

---

## 11. Remaining Limitations

1. **Active Access Token Invalidation Window:**
   Because access tokens are stateless JWTs, an access token issued prior to a user logout remains cryptographically valid for up to 60 minutes, unless the account is explicitly deactivated in PostgreSQL (which takes effect immediately on every request).
2. **`sessionStorage` XSS Vulnerability Window:**
   In compliance with security standards, `sessionStorage` protects tokens from persisting to non-volatile disk on shared devices, but does not isolate tokens from active in-tab XSS vulnerabilities.

---

## 12. Final Security Verdict

### **VERDICT: PASS**

All critical and high-priority security findings have been resolved, code-hardened, and validated with automated regression tests. The system enforces role freshness against PostgreSQL on every request, prevents refresh token replay and post-logout reuse, refuses insecure secrets in production, and guarantees zero leakage of credentials or hashes.

Milestone 2 is formally completed and audited. Milestone 3 has **not** been started.
