# VANA — REST API Specification

This document details the RESTful API endpoints, request/response schemas, query parameters, authorization requirements, and error status codes for the VANA platform.

---

## 1. Global API Conventions

* **Base URL:** `/api/v1`
* **Transport:** HTTPS exclusively.
* **Authentication:** Stateless Bearer Token (`Authorization: Bearer <jwt_access_token>`).
* **Content Type:** `application/json` (except file uploads: `multipart/form-data`).
* **Standard Error Format:**
  ```json
  {
    "detail": {
      "error_code": "RESOURCE_NOT_FOUND",
      "message": "Project with ID e8a2... not found",
      "field_errors": []
    }
  }
  ```

---

## 2. API Endpoint Matrix

### 2.0 System & Health

| Method | Endpoint | Allowed Roles | Description |
|---|---|:---:|---|
| `GET` | `/health` | Public | Unauthenticated health probe for Render/container monitors. Returns `{"status": "healthy"}`. |

---

### 2.1 Authentication & Profile (`/api/v1/auth`)

| Method | Endpoint | Allowed Roles | Description |
|---|---|:---:|---|
| `POST` | `/auth/login` | Public | Authenticates credentials; returns access & refresh tokens. |
| `POST` | `/auth/refresh` | Public | Exchanges valid refresh token for a new access token. |
| `GET` | `/auth/me` | Authenticated | Retrieves current authenticated user profile and roles. |

---

### 2.2 Project Management (`/api/v1/projects`)

| Method | Endpoint | Allowed Roles | Description |
|---|---|:---:|---|
| `GET` | `/projects` | All Authenticated | Lists projects (scoped to assigned projects for PM/FO). |
| `POST` | `/projects` | `ADMIN` | Creates a new environmental project. |
| `GET` | `/projects/{id}` | Assigned Roles | Retrieves detailed project workspace by ID. |
| `PUT` | `/projects/{id}` | `ADMIN`, Assigned `PM`| Updates project metadata, status, or coordinates. |
| `POST` | `/projects/{id}/targets` | `ADMIN`, Assigned `PM`| Attaches a new dimensional target to a project. |
| `GET` | `/projects/{id}/targets` | Assigned Roles | Lists targets and verified progress for a project. |

---

### 2.3 Team & User Management (`/api/v1/team`)

| Method | Endpoint | Allowed Roles | Description |
|---|---|:---:|---|
| `GET` | `/users` | `ADMIN`, `PM` | Lists organization users (PM sees users assigned to their projects). |
| `POST` | `/users` | `ADMIN` | Provisions a new user account with initial role. |
| `GET` | `/users/{id}` | `ADMIN`, Self | Retrieves specific user profile details and project assignments. |
| `PUT` | `/users/{id}` | `ADMIN` | Updates user role, status (`is_active`), or full name. |
| `POST` | `/projects/{id}/assignments` | `ADMIN`, Assigned `PM` | Allocates a user to a project roster as PM or Field Officer. |
| `DELETE` | `/projects/{id}/assignments/{userId}` | `ADMIN`, Assigned `PM` | Removes a user from a project's active roster. |

#### `POST /projects/{id}/assignments`
* **Request:**
  ```json
  {
    "user_id": "c4d5e6f7-...",
    "assigned_role": "FIELD_OFFICER"
  }
  ```
* **Response (201 Created):**
  ```json
  {
    "id": "1a2b3c4d-...",
    "project_id": "e8a2a14e-...",
    "user_id": "c4d5e6f7-...",
    "assigned_role": "FIELD_OFFICER",
    "assigned_at": "2026-11-02T10:15:00Z"
  }
  ```

---

### 2.4 Field Operations & Activity Reporting (`/api/v1/operations`)

| Method | Endpoint | Allowed Roles | Description |
|---|---|:---:|---|
| `POST` | `/operations/activities` | `FIELD_OFFICER`, `PM`, `ADMIN` | Submits a new field activity report with photo evidence (`multipart/form-data`). |
| `GET` | `/operations/activities` | Assigned Roles | Lists activity reports with filters (`status`, `project_id`). |
| `GET` | `/operations/activities/{id}` | Assigned Roles | Retrieves logical activity container with full revision history. |
| `POST` | `/operations/activities/{id}/revisions` | Assigned Roles | Submits a corrected revision for a rejected activity or an amendment. |
| `DELETE` | `/operations/activities/{id}` | `ADMIN`, Assigned `PM` | Soft-deletes/archives an activity; deactivates active ledger entry. |

#### `POST /operations/activities` (Multipart Form Data)
* **Form Fields:**
  * `project_id`: `e8a2a14e-...`
  * `metric_code`: `TREES_PLANTED`
  * `quantity`: `250.0`
  * `unit`: `trees`
  * `activity_date`: `2026-11-02`
  * `latitude`: `21.9512`
  * `longitude`: `89.1840`
  * `gps_accuracy_meters`: `4.2`
  * `field_notes`: `Planted Avicennia marina saplings in plot 4B.`
  * `evidence_files`: Binary image data (`image/jpeg`, max 3 files)
* **Response (201 Created):**
  ```json
  {
    "activity_id": "3b2c1d0e-...",
    "revision_id": "9a8b7c6d-...",
    "revision_number": 1,
    "status": "PENDING",
    "is_active_ledger_entry": false,
    "quantity": 250.0,
    "unit": "trees",
    "created_at": "2026-11-02T10:30:00Z"
  }
  ```

---

### 2.5 Activity Verification Centre (`/api/v1/verification`)

| Method | Endpoint | Allowed Roles | Description |
|---|---|:---:|---|
| `GET` | `/verification/queue` | `ADMIN`, `PM` (assigned) | Fetches pending activity revisions awaiting review. |
| `POST` | `/verification/revisions/{id}/decision` | `ADMIN`, `PM` (assigned) | Approves or rejects an activity revision (**Anti-Self-Verification Enforced**). |

#### `POST /verification/revisions/{id}/decision`
* **Request (Approval):**
  ```json
  {
    "decision": "APPROVED",
    "review_notes": "Coordinates verified within zone; clear photo evidence of sapling tags."
  }
  ```
* **Request (Rejection):**
  ```json
  {
    "decision": "REJECTED",
    "rejection_reason_code": "INSUFFICIENT_EVIDENCE",
    "review_notes": "Sapling photo is out of focus; unable to verify tree count."
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "revision_id": "9a8b7c6d-...",
    "status": "APPROVED",
    "is_active_ledger_entry": true,
    "verifier_id": "1d2e3f4a-...",
    "verified_at": "2026-11-02T11:00:00Z",
    "project_verified_total_recalculated": 64500.0
  }
  ```
* **Error Response (403 Forbidden - Anti-Self-Verification Gate Violation):**
  ```json
  {
    "detail": {
      "error_code": "SELF_VERIFICATION_PROHIBITED",
      "message": "Policy Violation: You cannot verify an activity submission you authored."
    }
  }
  ```

---

### 2.6 Environmental Impact Analytics (`/api/v1/analytics`)

| Method | Endpoint | Allowed Roles | Description |
|---|---|:---:|---|
| `GET` | `/analytics/portfolio` | `ADMIN`, `PM` | Retrieves organization-level verified environmental totals. |
| `GET` | `/analytics/projects/{id}` | Assigned Roles | Retrieves time-series verified metric history for a project. |
| `GET` | `/analytics/export` | `ADMIN`, `PM` | Exports verified environmental ledger data to CSV format. |

---

### 2.7 Audit History (`/api/v1/audit`)

| Method | Endpoint | Allowed Roles | Description |
|---|---|:---:|---|
| `GET` | `/audit` | `ADMIN` only | Retrieves chronological system audit log with state diffs. |
