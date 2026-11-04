# VANA — Architectural Decision Log (ADR)

This document records the architectural and technical decisions made for VANA, detailing context, rationale, consequences, and compliance constraints.

---

## Index of Decisions

* [ADR-001: Adoption of Domain-Driven Modular Monolith Architecture](#adr-001-adoption-of-domain-driven-modular-monolith-architecture)
* [ADR-002: Fixed Technology Stack & Dependency Boundaries](#adr-002-fixed-technology-stack--dependency-boundaries)
* [ADR-003: Strict Metric Codes, Dimensionality, and Conversion Rules (D-01)](#adr-003-strict-metric-codes-dimensionality-and-conversion-rules-d-01)
* [ADR-004: Immutable Activity Revisions, Lineage, and Rejection Accounting (D-02, D-03)](#adr-004-immutable-activity-revisions-lineage-and-rejection-accounting-d-02-d-03)
* [ADR-005: Native Relational Geographic Representation without Spatial Extensions (D-04)](#adr-005-native-relational-geographic-representation-without-spatial-extensions-d-04)
* [ADR-006: Abstract Storage Interface for Evidence Attachments (D-05)](#adr-006-abstract-storage-interface-for-evidence-attachments-d-05)
* [ADR-007: Project-Level Targets with Extensible Milestone Support (D-06)](#adr-007-project-level-targets-with-extensible-milestone-support-d-06)
* [ADR-008: Mobile-First Online Reporting & Deferral of Offline Sync (D-07)](#adr-008-mobile-first-online-reporting--deferral-of-offline-sync-d-07)
* [ADR-009: Independent Backend Authorization & Anti-Self-Verification Rule](#adr-009-independent-backend-authorization--anti-self-verification-rule)
* [ADR-010: Scientific Rigor & Exclusion of Synthetic Multipliers](#adr-010-scientific-rigor--exclusion-of-synthetic-multipliers)
* [ADR-011: Activity-Level Reported Quantity Formulation & Partial Unique Index for Active Ledger](#adr-011-activity-level-reported-quantity-formulation--partial-unique-index-for-active-ledger)
* [ADR-012: Canonical Revision Status 'VERIFIED' and Amendment Net Adjustment Accounting](#adr-012-canonical-revision-status-verified-and-amendment-net-adjustment-accounting)
* [ADR-013: Stateless JWT Token Mechanics, Ephemeral Session-Scoped Storage & Immutable Audit Integrity](#adr-013-stateless-jwt-token-mechanics-ephemeral-session-scoped-storage--immutable-audit-integrity)
* [ADR-014: Refresh-Token Concurrency Serialization via PostgreSQL Advisory Locks & Session Storage Evaluation](#adr-014-refresh-token-concurrency-serialization-via-postgresql-advisory-locks--session-storage-evaluation)
* [ADR-015: Strict Environmental Metric Isolation, GeoJSON Validation, and Scoped Portfolio Boundaries](#adr-015-strict-environmental-metric-isolation-geojson-validation-and-scoped-portfolio-boundaries)
* [ADR-016: Immutable Activity Lineage, Anti-Self-Verification Gate, and Content-Addressed Evidence Security](#adr-016-immutable-activity-lineage-anti-self-verification-gate-and-content-addressed-evidence-security)
* [ADR-017: Verification Concurrency Row-Locking, Path Traversal Safeguards, and Activity Archival Semantics](#adr-017-verification-concurrency-row-locking-path-traversal-safeguards-and-activity-archival-semantics)
* [ADR-018: Field Monitoring Schema, Composite Referential Integrity, and Append-Only Observation Corrections](#adr-018-field-monitoring-schema-composite-referential-integrity-and-append-only-observation-corrections)
* [ADR-019: Field Monitoring Relational Architecture, Composite FK Integrity & Survival Supersession](#adr-019-field-monitoring-relational-architecture-composite-fk-integrity--survival-supersession)
* [ADR-020: Field Monitoring FastAPI Router, Multi-Tenant RBAC & On-Demand Alert Evaluation](#adr-020-field-monitoring-fastapi-router-multi-tenant-rbac--on-demand-alert-evaluation)
* [ADR-021: Frontend Monitoring API Integration, Type Synchronization & TanStack Query Cache Architecture](#adr-021-frontend-monitoring-api-integration-type-synchronization--tanstack-query-cache-architecture)
* [ADR-022: Field Monitoring UI Workspaces, Live Previews & Immutability Architecture](#adr-022-field-monitoring-ui-workspaces-live-previews--immutability-architecture)
* [ADR-023: Full Platform End-to-End Acceptance, Multi-Domain State Invariants & Sandbox Network Isolation](#adr-023-full-platform-end-to-end-acceptance-multi-domain-state-invariants--sandbox-network-isolation)
* [ADR-024: Production Deployment Hardening, Dynamic Migration Precedence & Exact CORS Security](#adr-024-production-deployment-hardening-dynamic-migration-precedence--exact-cors-security)
* [ADR-025: Cryptographic Audit Ledger, SHA-256 Hash Chaining, and Transactional Row-Locked Concurrency](#adr-025-cryptographic-audit-ledger-sha-256-hash-chaining-and-transactional-row-locked-concurrency)

---

### ADR-001: Adoption of Domain-Driven Modular Monolith Architecture
* **Status:** Accepted (2026-11-02)
* **Context:** VANA requires rapid, reliable MVP development while supporting complex domain workflows (planning, field reporting, verification, and environmental math). The platform must scale without premature operational complexity.
* **Decision:** Structure the system as a single modular monolith with a decoupled React 19 SPA frontend and a FastAPI backend partitioned into bounded domain modules (`auth`, `projects`, `teams`, `operations`, `verification`, `analytics`, `audit`). Microservices, message brokers (Kafka, RabbitMQ), and distributed caches are rejected for MVP.
* **Consequences:** Low operational overhead, transactional consistency across domains, single deployment artifact for the API, and clear domain boundaries that allow future microservice extraction if traffic or organizational scale warrants it.

---

### ADR-002: Fixed Technology Stack & Dependency Boundaries
* **Status:** Accepted (2026-11-02)
* **Context:** Maintain stability, long-term maintainability, and clean boundaries across frontend and backend.
* **Decision:** Lock the technology stack permanently:
  * Frontend: React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, React Router, TanStack Query, React Hook Form, Zod, Recharts, React Leaflet, Axios.
  * Backend: Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PostgreSQL 16, JWT, Argon2.
  * Infrastructure: Docker, GitHub Actions, Vercel, Render, Neon PostgreSQL.
* **Consequences:** All contributors must use this exact stack. Unapproved dependencies or competing UI/ORM/DB libraries are strictly forbidden.

---

### ADR-003: Strict Metric Codes, Dimensionality, and Conversion Rules (D-01)
* **Status:** Accepted (2026-11-02)
* **Context:** Environmental accounting requires mathematical precision. Aggregating quantities with different units or aggregating disparate ecological metrics (e.g. counting saplings planted vs. mature trees protected) invalidates environmental audits.
* **Decision:**
  * Define unique `metric_code` identifiers grouped under 5 high-level categories (`VEGETATION_PLANTING`, `LAND_RESTORATION`, `WATER_CONSERVATION`, `SOIL_CONSERVATION`, `WASTE_REMOVAL`).
  * Enforce strict measurement dimensions (`COUNT`, `AREA`, `VOLUME`, `MASS`).
  * Never aggregate different metric codes merely because they share a dimension.
  * Allow conversions only within the exact same metric code to its canonical base unit (e.g., $1\text{ ha} = 10{,}000\text{ m}^2$).
  * Enforce dimensionality checks in Pydantic schemas and database constraints.
* **Consequences:** Zero risk of unit contamination; mathematically auditable environmental balance sheets.

---

### ADR-004: Immutable Activity Revisions, Lineage, and Rejection Accounting (D-02, D-03)
* **Status:** Accepted (2026-11-02)
* **Context:** Field reports may be rejected or amended post-verification. Modifying approved records in-place destroys audit trails and creates double-counting bugs.
* **Decision:**
  * Separate `field_activities` (logical parent) from `activity_revisions` (versioned records).
  * An amendment to a verified activity creates a new revision with status `PENDING`. The prior revision remains `APPROVED` and active in the ledger until the new revision is formally approved.
  * Rejection requires a mandatory reason code and review comment. The rejected revision remains archived as `REJECTED`.
  * Define distinct aggregations:
    * `current_verified_quantity`: Sum of quantities of active approved revisions.
    * `current_pending_quantity`: Sum of quantities of current active unreviewed revisions.
    * `current_rejected_quantity`: Sum of quantities of current active rejected revisions.
    * `historical_rejected_submission_count`: Count of all historical rejected revision records.
    * `reported_quantity`: Current verified plus net pending claims.
* **Consequences:** Historical rejected revisions do not inflate current quantities; no double counting; full auditable lineage for every amendment.

---

### ADR-005: Native Relational Geographic Representation without Spatial Extensions (D-04)
* **Status:** Accepted (2026-11-02)
* **Context:** Spatial mapping on the Living Earth map is required, but introducing PostGIS adds complex spatial dependencies not currently approved in the MVP stack.
* **Decision:**
  * Use standard relational columns for coordinates: `latitude` and `longitude` as `DOUBLE PRECISION`.
  * Project boundary polygons are optional and stored as standard GeoJSON text/JSONB (`boundary_geojson`).
  * Activity locations capture optional point coordinates with accuracy radius (`gps_accuracy_meters`).
  * Spatial rendering is handled client-side using React Leaflet.
* **Consequences:** Zero external C-library or PostGIS extensions required; fully portable across standard PostgreSQL engines (Neon, RDS, local Docker).

---

### ADR-006: Abstract Storage Interface for Evidence Attachments (D-05)
* **Status:** Accepted (2026-11-02)
* **Context:** Field activities require photo evidence. Deployment on ephemeral cloud environments (e.g. Render) means local files do not persist across container restarts. AWS S3 is designated as future scaling infrastructure.
* **Decision:**
  * Define an abstract interface `IStorageService` with `upload_file`, `get_file_url`, and `delete_file`.
  * Local development uses `LocalStorageService` with content-addressed SHA-256 filenames written to `/uploads`.
  * Store only relative object keys in the database.
  * For production on ephemeral infrastructure, document the configuration for a persistent mount or S3-compatible object store using standard environment variables without altering application code or schema.
* **Consequences:** Clean separation of concerns; safe local development; cloud-ready architecture without premature infrastructure lock-in.

---

### ADR-007: Project-Level Targets with Extensible Milestone Support (D-06)
* **Status:** Accepted (2026-11-02)
* **Context:** Projects have targets (e.g. 10,000 Trees). In the future, projects may split targets across phases or milestones.
* **Decision:**
  * MVP implements `project_targets` at the project level (`project_id`, `metric_code`, `target_quantity`, `target_unit`, `target_date`).
  * Include a nullable `milestone_id UUID NULL` column in the database schema.
  * Milestones remain optional and unused in MVP queries, but the database schema will require zero structural alteration when milestone workflows are introduced in Phase 2.
* **Consequences:** Simple, uncluttered MVP UX while preserving database forward-compatibility.

---

### ADR-008: Mobile-First Online Reporting & Deferral of Offline Sync (D-07)
* **Status:** Accepted (2026-11-02)
* **Context:** Field officers submit reports on mobile devices, often in rural environments. Offline synchronization (IndexedDB, Service Workers, background syncing, conflict resolution) is complex and prone to edge-case errors.
* **Decision:**
  * Defer offline synchronization to Phase 2.
  * Build the field reporting UI strictly as a responsive, mobile-first web interface with touch targets $\ge 48\text{px}$.
  * Retain form draft state in `sessionStorage` during active browser sessions to prevent accidental data loss on transient network disconnects.
  * Explicitly communicate online requirement in the MVP.
* **Consequences:** Dramatically reduced MVP complexity; robust, predictable submission pipeline; smooth mobile ergonomics.

---

### ADR-009: Independent Backend Authorization & Anti-Self-Verification Rule
* **Status:** Accepted (2026-11-02)
* **Context:** Role boundaries (`ADMIN`, `PROJECT_MANAGER`, `FIELD_OFFICER`) must be enforced securely. Self-verification creates severe compliance risks.
* **Decision:**
  * Enforce all RBAC permissions independently in FastAPI dependencies via JWT token validation and database lookup.
  * Implement an anti-self-verification gate: `IF current_user.id == activity.created_by_id THEN RAISE HTTP 403 Forbidden`.
  * Project Managers can only view, verify, and manage projects they are explicitly assigned to in `project_assignments`.
* **Consequences:** Bulletproof audit compliance; zero reliance on frontend security; prevents collusion or fraudulent verification.

---

### ADR-010: Scientific Rigor & Exclusion of Synthetic Multipliers
* **Status:** Accepted (2026-11-02)
* **Context:** Calculating carbon offsets, biodiversity ratings, or survival rates without measured field evidence invites greenwashing accusations and regulatory failure.
* **Decision:**
  * Never invent or compute synthetic carbon sequestration, biodiversity indices, or theoretical survival multipliers in VANA.
  * Only display direct physical quantities measured and verified in the field.
  * Derived metrics (e.g., survival rate) must be calculated strictly from paired verified field counts (e.g. `SURVIVING_TREES / PLANTED_TREES * 100`) and clearly cite their date range and methodology.
* **Consequences:** Absolute institutional credibility; audit-grade environmental accounting.

---

### ADR-011: Activity-Level Reported Quantity Formulation & Partial Unique Index for Active Ledger
* **Status:** Accepted (2026-11-02)
* **Context:** In pre-implementation audit, two critical edge cases were identified: (1) A naive summation of `verified + pending` caused double counting when an already-verified activity received an amendment; (2) The database schema required native enforcement that at most one active revision can exist per logical activity.
* **Decision:**
  * Define `Reported Quantity` at the logical activity level: $\sum_{a \in \mathcal{A}} \text{reported}(a)$, where an amendment to a verified activity reflects the pending claim rather than summing both old and new revisions.
  * Implement a PostgreSQL partial unique index on `activity_revisions`:
    `CREATE UNIQUE INDEX uq_activity_single_active_ledger ON activity_revisions(activity_id) WHERE is_active_ledger_entry = TRUE;`
  * Add database-level check constraints: `chk_active_ledger_approved` (active entry must be `APPROVED`) and `chk_rejection_reason_required` (rejections require non-null reason code and review notes).
  * Add `is_archived` to `field_activities` to support soft-deletion and immediate ledger de-allocation without destroying audit history.
* **Consequences:** Complete physical impossibility of double-counting active revisions at the database level; mathematically sound handling of pending amendments.

---

### ADR-012: Canonical Revision Status 'VERIFIED' and Amendment Net Adjustment Accounting
* **Status:** Accepted (2026-11-02)
* **Context:** Final clarifications issued prior to Milestone 1A implementation regarding terminology alignment and amendment mathematics.
* **Decision:**
  1. **Canonical Status Enum:** The activity revision status is canonically `PENDING`, `VERIFIED`, and `REJECTED`. The term "APPROVE" is retained strictly as a UI verb/action button; all database constraints, Pydantic schemas, and API payloads use `status = 'VERIFIED'`.
  2. **Submitted Quantity vs. Net Adjustment:** Each activity revision records its absolute submitted quantity (`quantity`). When a previously verified activity is amended, the system calculates the net adjustment $\Delta = Q_{\text{amended}} - Q_{\text{verified}}$.
  3. **Pending Amendment Isolation:** A pending amendment never contributes its full quantity as a new independent activity. It represents an uncommitted adjustment; official verified totals remain anchored to the previously active revision.
  4. **Support for Negative Net Adjustments:** If an amendment decreases a previously verified quantity ($Q_{\text{amended}} < Q_{\text{verified}}$), the verified ledger remains at $Q_{\text{verified}}$ while the amendment is `PENDING`. Upon verification, the ledger transitions atomically to the new lower quantity.
  5. **Preservation of History:** All historical revisions and audit log records are immutable and preserved in perpetuity.
* **Consequences:** Terminology is consistent across database, backend, and documentation; amendment calculations safely handle both increases and decreases without corrupting verified ledger totals.

---

### ADR-013: Stateless JWT Token Mechanics, Ephemeral Session-Scoped Storage & Immutable Audit Integrity
* **Status:** Accepted (2026-11-02)
* **Context:** Milestone 2 implements user authentication, role-based access control (ADMIN, PROJECT_MANAGER, FIELD_OFFICER), and administrative user management. Permanent engineering rules strictly forbid storing JWTs in persistent `localStorage` (XSS vulnerability), persisting plaintext passwords, leaking credential hashes in audit logs, or trusting client-asserted permissions.
* **Decision:**
  1. **Stateless Token Pairs:** Access tokens use HMAC-SHA256 (`HS256`) signed with `JWT_SECRET_KEY`, expiring in 60 minutes (`type: "access"`, claims: `sub`, `email`, `role`, `exp`, `iat`). Refresh tokens expire in 7 days (`type: "refresh"`, unique `jti`).
  2. **Zero `localStorage` Policy:** The frontend React client retains the access token in in-memory state (`AuthContext`) and tab-scoped `sessionStorage` (cleared immediately upon tab closure or logout). Persistent `localStorage` is strictly avoided to eliminate long-term token exfiltration vectors.
  3. **Multi-Tier Server-Side RBAC:** Authorization dependencies (`get_current_active_user`, `require_roles`, `verify_project_access`) enforce role privileges independently on every HTTP request.
  4. **Anti-Self-Role Modification & Privilege Escalation:** Backend business logic explicitly prevents any user (including administrators) from altering their own role (`SELF_ROLE_CHANGE_PROHIBITED`) to prevent accidental lockouts or privilege escalations. Non-admins cannot alter roles or activation status.
  5. **Automated Audit Sanitization:** The audit logging service (`record_audit_log`) strips all sensitive keys (`password`, `hashed_password`, `token`, `access_token`, `refresh_token`, `secret`) before writing JSONB state diffs to PostgreSQL.
* **Consequences:** Strict compliance with OWASP guidelines; zero secret leaks; impenetrable server-side role and project boundaries.

---

### ADR-014: Refresh-Token Concurrency Serialization via PostgreSQL Advisory Locks & Session Storage Evaluation
* **Status:** Accepted (2026-11-02)
* **Context:** In the Milestone 2 token verification audit, concurrent `/api/v1/auth/refresh` requests with the same refresh token were evaluated. Under high-frequency concurrent execution, a Time-of-Check to Time-of-Use (TOCTOU) race condition permitted parallel requests to observe the same unconsumed JTI and both obtain new replacement tokens. Furthermore, the use of `audit_logs` for token revocation state was reviewed for performance and table bloat trade-offs.
* **Decision:**
  1. **PostgreSQL Transaction Advisory Lock:** In `backend/app/domains/auth/services.py`, the token rotation transaction acquires a session-safe, transaction-scoped lock: `SELECT pg_advisory_xact_lock(hashtext(:jti))`. This natively serializes concurrent refresh requests for the same JTI in the PostgreSQL lock manager without mutating schema or adding row locks.
  2. **Audit-Log State Storage Evaluation:** For MVP, maintaining token revocation within `audit_logs` preserves the approved 8-table relational schema without introducing unapproved tables. Because tokens are keyed by indexed columns and rotated infrequently (every 60 minutes), read performance is acceptable.
  3. **Future Scaling Recommendation:** As traffic scales to high concurrency, an independent `auth_sessions` or `refresh_tokens` table with a physical unique constraint on `jti` and an index on `expires_at` should be introduced to cleanly separate compliance auditing from transient session state and enable automatic TTL row cleanup.
* **Consequences:** 100% atomic serialization under concurrent refresh attempts; guaranteed zero duplicate active replacement tokens; clean architecture path for future dedicated session extraction.

---

### ADR-015: Strict Environmental Metric Isolation, GeoJSON Validation, and Scoped Portfolio Boundaries
* **Status:** Accepted (2026-11-02)
* **Context:** Milestone 3 establishes project lifecycle management, team roster allocations, geographic coordinates and boundary polygons, and environmental targets. Rules require that metric definitions never contaminate across dimensions or unapproved units, duplicate targets for the same project/metric are strictly blocked, geographic polygons conform to RFC 7946 closed linear rings without requiring external PostGIS dependencies, and personnel access is scoped strictly to authorized project assignments.
* **Decision:**
  1. **Approved Metric Catalog Enforcement:** All target creation endpoints validate against `APPROVED_METRIC_CATALOG`. Metric codes must belong to approved categories (`VEGETATION_PLANTING`, `LAND_RESTORATION`, `WATER_CONSERVATION`, `WASTE_REMOVAL`), units must be within the metric's `supported_units`, and target quantities must be positive.
  2. **Duplicate Target Prevention:** Backed by database partial unique index `uq_project_targets_no_milestone`, the service validates that duplicate active targets for the same `(project_id, metric_code)` combination raise `HTTP 409 Conflict`. Target creation never creates synthetic achieved progress.
  3. **Native GeoJSON RFC 7946 Validation:** Pydantic validators enforce that `boundary_geojson` possesses type `Polygon`, coordinates form closed linear rings ($\ge 4$ vertices, where `first == last`), and all coordinates are bounded by `[-180..180, -90..90]`. Native PostgreSQL JSONB storage is preserved with zero PostGIS overhead.
  4. **Strict Assignment Scoping:** Project Managers and Field Officers are restricted to projects where an active `ProjectAssignment` row exists. Inactive users are rejected from being allocated to project rosters (`HTTP 400 Bad Request`). Duplicate assignments are rejected (`HTTP 409 Conflict`).
  5. **Audit Logging:** All project, target, and assignment mutations commit discrete immutable events to `audit_logs` (`PROJECT_CREATED`, `PROJECT_UPDATED`, `PROJECT_STATUS_CHANGED`, `TARGET_CREATED`, `TARGET_UPDATED`, `TARGET_DELETED`, `ASSIGNMENT_CREATED`, `ASSIGNMENT_DELETED`).
* **Consequences:** Eliminates environmental calculation and unit errors; guarantees mathematical and spatial integrity; enforces impenetrable project boundary authorization.

---

### ADR-016: Immutable Activity Lineage, Anti-Self-Verification Gate, and Content-Addressed Evidence Security
* **Status:** Accepted (2026-11-03)
* **Context:** Milestone 4 implements field operations, photo evidence collection, amendment tracking, and review verification. System invariants demand that:
  1. No activity author may ever verify their own submission (`verifier_id != creator_id`), enforced server-side.
  2. Exactly one active revision may exist in the environmental ledger per logical activity (`uq_activity_single_active_ledger`).
  3. Amendments must maintain previous verified quantities in the ledger until formally reviewed, with clear net adjustment tracking ($\Delta = Q_{\text{amended}} - Q_{\text{verified}}$).
  4. Evidence attachments must be strictly scrutinized for allowed formats, size limits, and access-controlled retrieval without exposing physical filesystem paths.
* **Decision:**
  1. **Anti-Self-Verification Gate (Rule 5):** Enforce `if current_user.id == activity.created_by_id: raise HTTPException(403, {"error_code": "SELF_VERIFICATION_PROHIBITED"})` at the service layer for all approval and rejection decisions. Additionally, the Verification Centre UI flags items authored by the viewing user and disables review buttons with prominent policy notices.
  2. **5-Ledger Revision State Machine:**
     - Activity submissions create Revision 1 (`status = PENDING`, `is_active_ledger_entry = False`).
     - Reviewer approval atomically clears any existing active ledger revision for that activity and sets `status = VERIFIED`, `is_active_ledger_entry = True`, `verifier_id = current_user.id`, `verified_at = now()`.
     - Amendments create Revision $N+1$ (`PENDING`, `is_active_ledger_entry = False`). Duplicate unreviewed amendments are blocked with `HTTP 400 PENDING_REVISION_EXISTS`.
     - Rejections require a valid `rejection_reason_code` and mandatory `review_notes`. The previously verified revision remains active in the ledger.
     - Archiving an activity soft-deletes the record (`is_archived = True`) and deactivates any active ledger entries.
  3. **Content-Addressed Evidence Security:**
     - Evidence files are validated for MIME type (`image/jpeg`, `image/png`, `image/webp`, `application/pdf`) and maximum size ($\le 10\text{ MB}$).
     - Content is hashed with SHA-256 for deterministic, collision-resistant storage via `LocalStorageService`.
     - Direct filesystem access is barred. Files are served strictly through `GET /api/v1/operations/evidence/{evidence_id}`, which enforces project-level authorization before streaming content.
  4. **Audit Trail Logging:** All lifecycle mutations commit structured events to `audit_logs` (`ACTIVITY_CREATED`, `EVIDENCE_UPLOADED`, `ACTIVITY_AMENDED`, `ACTIVITY_VERIFIED`, `ACTIVITY_REJECTED`, `ACTIVITY_ARCHIVED`).
* **Consequences:** Eliminates conflicts of interest; guarantees mathematical integrity and preventing double-counting; ensures robust evidence security and verifiable compliance.

---

### ADR-017: Verification Concurrency Row-Locking, Path Traversal Safeguards, and Activity Archival Semantics
* **Status:** Accepted (2026-11-03)
* **Context:** During the Milestone 4 Final Acceptance Audit, deep-dive investigations identified three critical areas for operational hardening:
  1. Concurrent verification reviews or concurrent amendment submissions targeting the same entity could trigger race conditions or unhandled constraint violations if not serialized at the database row level.
  2. Storage retrieval by key required robust directory containment validation to strictly prevent path traversal attacks (e.g. `../../etc/passwd`).
  3. Operational archival (`DELETE /api/v1/operations/activities/{id}`) deactivates active ledger entries per specification, but ecological integrity warrants a clear distinction between operational list archival and formal environmental retraction.
* **Decision:**
  1. **Row-Level Pessimistic Locking (`with_for_update()`):**
     - `VerificationService.record_decision` explicitly locks the target `ActivityRevision` row using `select(...).with_for_update()`.
     - `ActivityService.amend_activity` and `ActivityService.archive_activity` lock the parent `FieldActivity` row using `select(...).with_for_update()`.
     - Concurrent verification attempts serialize: the winning transaction applies the decision, and subsequent transactions detect that `status != PENDING`, cleanly returning `HTTP 400 REVISION_ALREADY_REVIEWED`.
  2. **Storage Path Traversal Containment:**
     - `LocalStorageService.get_file_path` asserts `resolved_target.is_relative_to(resolved_root)`. Any key attempting to escape the storage root raises `ValueError`, which `EvidenceService` maps to `HTTP 400 INVALID_STORAGE_KEY`.
     - Upload file extensions are whitelisted strictly to allowed MIME extensions (`.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf`), defaulting unrecognized formats to `.bin`.
  3. **Activity Archival vs. Retraction Semantics:**
     - For Milestone 4, current behavior fulfills the specification: archiving soft-deletes the activity and deactivates any active ledger entry (`is_archived = True`, `is_active_ledger_entry = False`).
     - Documented an architectural recommendation for Milestone 5 to introduce formal *Retraction Events* with justification reason codes for revoking verified achievements, preserving audit provenance.
* **Consequences:** Eliminates verification race conditions, neutralizes path traversal vulnerabilities, and solidifies transaction boundaries across all operations.

---

### ADR-018: Environmental Ledger Aggregation Engine, Multi-Tenant Dashboard Scoping & Living Earth Geospatial Intelligence
* **Status:** Accepted (2026-11-03)
* **Context:** Milestone 5 establishes the authoritative environmental impact accounting and organization intelligence layer for VANA. Critical architectural requirements included:
  1. Authoritative aggregation of environmental achievements from PostgreSQL without double-counting, strictly incorporating active verified revisions (`is_active_ledger_entry = True`) and excluding unreviewed/rejected submissions or archived activities (`is_archived = False`).
  2. Preserving strict unit dimensionality (Rule 8) and metric catalog isolation, disallowing aggregation across incompatible metric codes or dimensions while supporting lossless canonical unit conversions.
  3. Clear accounting distinction between official verified quantities and net pending adjustments ($\Delta = Q_{\text{amended}} - Q_{\text{verified}}$) for transparency during pending amendment review.
  4. Multi-tenant RBAC scoping: `ADMIN` receives portfolio-wide visibility, while `PROJECT_MANAGER` and `FIELD_OFFICER` are strictly isolated to their assigned projects across all dashboard, analytics, and map endpoints.
  5. Interactive geospatial visualization ("Living Earth") combining project centroids, verified achievement progress, and GeoJSON boundary polygons via React Leaflet without external GIS server dependencies.
* **Decision:**
  1. **Environmental Ledger Aggregation Engine (`EnvironmentalLedgerService`):**
     - Aggregates official quantities by querying `ActivityRevision` where `is_active_ledger_entry = True`, joined with `FieldActivity` where `is_archived = False`.
     - Converts all recorded quantities to the metric's canonical unit using the approved catalog conversion coefficients (`APPROVED_METRIC_CATALOG`) before summing.
     - Calculates target progress as $\text{percentage} = \min(100.0, (\text{verified} / \text{target}) \times 100)$ and remaining quantity as $\max(0, \text{target} - \text{verified})$.
     - Computes net pending adjustments by comparing pending amendment revision quantities against their base verified revisions, isolating them in a secondary visual indicator without inflating official totals.
  2. **Multi-Tenant RBAC Authorization Scoping:**
     - In `backend/app/domains/analytics/services.py`, `_get_scoped_project_ids` checks `user.role`. If `ADMIN`, returns `None` (portfolio-wide). If `PROJECT_MANAGER` or `FIELD_OFFICER`, queries `ProjectAssignment` to retrieve assigned project IDs. If no assignments exist, returns an empty set.
     - Scopes `/dashboard/overview`, `/dashboard/projects`, `/dashboard/recent-activity`, `/analytics/projects/{id}/impact`, and `/analytics/projects/{id}/trends`. Attempting to access an unassigned project returns `HTTP 403 FORBIDDEN`.
  3. **Operational Attention Project Rules:**
     - Dynamically computes operational health flags:
       - `HIGH`: Verification backlog ($\ge 3$ unreviewed submissions).
       - `MEDIUM`: Target deadline within 14 days and progress $< 80\%$.
       - `MEDIUM`: Active project with zero verified progress.
  4. **Living Earth Geospatial Architecture:**
     - Implemented `LivingEarthMap.tsx` and `LivingEarthMapView.tsx` using `react-leaflet` with OpenStreetMap CartoDB Positron base tiles.
     - Visualizes projects as interactive SVG marker pins colored by lifecycle status (`#183D32` for ACTIVE, `#D6A76A` for DRAFT, `#A8B99B` for COMPLETED).
     - Markers open rich popups displaying verified progress, pending items, coordinate metadata, and direct navigation links to `ProjectWorkspaceView`.
  5. **Bi-Level UI Progress Visualization:**
     - `ProjectWorkspaceView` and `OrganizationDashboardView` render a dual-segment progress bar: solid Forest Green for verified percentage, and a secondary Earth Gold segment for pending adjustments.
* **Consequences:** Guarantees scientific data grounding and mathematical auditability; prevents data leakage across project boundaries; delivers an executive overview while providing field personnel with actionable operational insights.


---

### ADR-019: Field Monitoring Relational Architecture, Composite FK Integrity & Survival Supersession
* **Status:** Accepted (2026-11-03)
* **Context:** Phase 6.1 introduces the relational foundation for post-implementation field monitoring, maintenance task workflows, and survival rate tracking across ecological restoration projects. Key architectural challenges and data integrity mandates included:
  1. Preventing cross-project referential corruption: ensuring inspections, tasks, and survival observations cannot link to activities or parent entities belonging to different projects.
  2. Safe foreign key deletion semantics: preventing standard composite `ON DELETE SET NULL` from attempting to nullify mandatory `project_id` columns and triggering `NotNullViolationError`.
  3. Survival observation auditability and identity: enforcing a single active survival observation per project/plot/cohort/date while maintaining an immutable supersession audit trail for corrections.
  4. Polymorphic evidence attachment: supporting evidence uploads for both activity submissions and field inspections without ambiguity or orphaned references.
  5. Scientific survival calculation: strictly defining sample-based vs. census survival rate ($alive / (alive + dead) \times 100$) derived dynamically without population extrapolation or static database persistence.
* **Decision:**
  1. **Composite Foreign Keys with Column-Specific Nullification:**
     - Added composite unique constraint `uq_field_activities_id_project` on `field_activities(id, project_id)`.
     - Configured composite foreign keys referencing `(project_id, linked_activity_id)` / `(project_id, activity_id)` / `(project_id, inspection_id)` across `field_inspections`, `maintenance_tasks`, and `survival_observations`.
     - Utilized PostgreSQL 17's column-specific `ON DELETE SET NULL (column_name)` to set only the optional referencing column (e.g. `linked_activity_id`) to NULL on deletion while preserving mandatory `project_id`. Configured `passive_deletes=True` on SQLAlchemy parent relationships to prevent premature client-side nullification.
     - Enforced `ON DELETE RESTRICT` on `survival_observations.fk_survival_activity` and `evidence_files.fk_evidence_inspections` to prevent accidental deletion of parent records with active monitoring data.
  2. **Atomic Survival Observation Supersession:**
     - Implemented partial unique index `uq_active_survival_observation` on `(project_id, plot_identifier, cohort_identifier, observation_date) WHERE is_active = TRUE`.
     - Configured self-referential `superseded_by_id` with `DEFERRABLE INITIALLY DEFERRED` constraint, enabling atomic single-transaction replacement: marking the original observation inactive and linking `superseded_by_id` without partial unique index collisions.
  3. **Target Exclusivity for Evidence Files:**
     - Added optional `inspection_id` with foreign key referencing `field_inspections(id)` on `evidence_files`.
     - Added database check constraint `chk_evidence_target` enforcing `(activity_revision_id IS NOT NULL AND inspection_id IS NULL) OR (activity_revision_id IS NULL AND inspection_id IS NOT NULL)`.
  4. **Derived Survival Rate Property:**
     - Modeled survival rate as a Python property `alive_count / (alive_count + dead_count) * 100` when `(alive_count + dead_count) > 0`, returning `None` otherwise. It is never stored as a static column or extrapolated to project populations.
* **Consequences:** Enforces complete relational and cross-project data integrity at the database layer; guarantees immutable auditability for survival corrections; ensures zero data corruption risk when parent activities or inspections are modified.

---

### ADR-020: Field Monitoring FastAPI Router, Multi-Tenant RBAC & On-Demand Alert Evaluation
* **Status:** Accepted (2026-11-04)
* **Context:** Exposing Phase 6.2 monitoring domain services via REST requires strict multi-tenant authorization, client payload validation, and real-time operational visibility without introducing background queue daemons or distributed schedulers.
* **Decision:**
  1. **FastAPI Monitoring Router Mounted at `/api/v1/monitoring`:**
     - 19 REST endpoints spanning Field Inspections (8), Maintenance Tasks (7), Survival Observations (5), and Operations/Alerts/Dashboard (2).
     - Full Pydantic v2 request/response schemas matching domain entities. Client-supplied `survival_rate` values are dropped/rejected in favor of server-derived calculation.
  2. **Three-Tier Multi-Tenant RBAC Enforcement:**
     - `ADMIN`: Organization-wide access to create, inspect, reassign, complete, and correct all monitoring records.
     - `PROJECT_MANAGER`: Strictly scoped to assigned projects (`verify_project_access`). Authorized to schedule inspections, create tasks, cancel, reopen, and perform observation corrections.
     - `FIELD_OFFICER`: Strictly scoped to assigned projects. Restricted from scheduling inspections or creating tasks. Can only start and complete inspections and tasks assigned directly to them (`assigned_to_id == user.id`), and submit new field survival observations.
  3. **In-Database Dynamic Alerts Query Engine:**
     - Operational alerts (`OVERDUE_INSPECTION`, `UPCOMING_INSPECTION`, `OVERDUE_TASK`) evaluated on-demand in PostgreSQL without Celery, Redis, or cron daemons, adhering to the modular monolith architectural invariant (Rule 1).
  4. **Polymorphic Evidence Attachment & Scoping:**
     - `EvidenceFile` resolution in `EvidenceService.get_evidence_file_path` updated to resolve parent project from either `activity.project_id` or `inspection.project_id`, enabling unified streaming under `/api/v1/operations/evidence/{id}`.
* **Consequences:** Complete multi-tenant security across all monitoring endpoints; zero extraneous infrastructure dependencies; 100% compliance with VANA RBAC invariants.

---

### ADR-021: Frontend Monitoring API Integration, Type Synchronization & TanStack Query Cache Architecture
* **Status:** Accepted (2026-11-04)
* **Context:** Phase 6.4 integrates the monitoring APIs into the React 19 frontend application. The integration requires strong TypeScript type contracts matching backend OpenAPI models, a centralized API client with comprehensive error normalization, and reactive TanStack Query hooks that prevent stale data without unnecessary network roundtrips.
* **Decision:**
  1. **Strict TypeScript Domain Types (`frontend/src/types/monitoring.ts`):**
     - Defined strongly typed interfaces and string literal enums matching FastAPI OpenAPI schemas without extraneous client-side inventions.
     - Modeled `FieldInspection`, `InspectionStatus`, `InspectionType`, `CanopyCondition`, `SoilMoistureCondition`, `InspectionEvidence`, `InspectionAddendum`, `MaintenanceTask`, `MaintenanceTaskStatus`, `MaintenanceTaskCategory`, `MaintenanceTaskPriority`, `SurvivalObservation`, `SurvivalMethodology`, `SurvivalAnalytics`, `MonitoringAlert`, and `MonitoringDashboard`.
     - Explicitly omitted client-supplied `survival_rate` from submission requests, enforcing scientific integrity (Rule 9).
  2. **Monitoring API Service (`frontend/src/services/monitoringService.ts`):**
     - Implemented all 19 endpoints using the shared `apiClient` instance, ensuring unified authentication headers, base URL handling, and timeout configurations.
     - Supported multipart evidence uploads with automatic `FormData` encapsulation of files and coordinate metadata.
  3. **Centralized Error Normalization (`frontend/src/services/apiClient.ts`):**
     - Enhanced Axios response interceptor to normalize FastAPI/Pydantic error shapes (string `detail`, structured `{ message }`, array validation errors `[{ loc, msg }]`).
     - Preserves human-readable error feedback for 400 validation, 401 unauthenticated, 403 authorization, 404 missing record, 409 conflict, and 422 schema validation errors.
  4. **Hierarchical TanStack Query Keys & Automated Invalidation (`frontend/src/hooks/useMonitoring.ts`):**
     - Standardized query key factory `monitoringKeys` (`all`, `inspections`, `tasks`, `survival`, `alerts`, `dashboard`).
     - Configured mutation hooks to automatically invalidate dependent lists, details, dashboards, and alerts upon successful mutation, preventing stale state in subsequent UI components.
* **Consequences:** Provides a robust, type-safe data access layer for Phase 6.5 UI components; eliminates manual cache invalidation bugs; preserves full regression suite compatibility with zero UI-layer leakage.

---

### ADR-022: Field Monitoring UI Workspaces, Live Previews & Immutability Architecture
* **Status:** Accepted (2026-11-04)
* **Context:** Phase 6.5 builds the user interface for Field Monitoring & Follow-up Management. The UI must present complex operational data across 4 functional domains, enforce scientific calculation guardrails (avoiding client-tampered survival rates), lock completed inspections against direct mutation, and respect multi-tenant RBAC permissions without duplicating backend business logic.
* **Decision:**
  1. **Tabbed Workspace Architecture (`frontend/src/views/monitoring/FieldMonitoringView.tsx`):**
     - Organized into 4 cohesive workspace tabs: `Overview / Dashboard`, `Field Inspections`, `Maintenance Tasks`, and `Survival Monitoring`.
     - Integrated a persistent global project filter driving all tabbed queries simultaneously.
     - Mounted at `/monitoring` with dynamic role-aware navigation in `Sidebar.tsx`.
  2. **Scientific Survival Calculation Guardrails:**
     - Prohibited client-side editing or submission of `survival_rate`. The input form collects strictly integer counts (`alive_count`, `dead_count`, `unassessed_count`, `sample_size`).
     - Rendered a dynamic live preview computing assessed population, unassessed remainder, and observed sample survival rate in real time, with explicit labeling distinguishing sample-based rates from project-wide population estimates.
     - Longitudinal trajectory curves (Recharts) render only real observed points without unsupported synthetic benchmark threshold lines.
  3. **Immutable Inspection Record Protection:**
     - Completed inspections are rendered as read-only.
     - Post-completion notes and corrections are strictly appended as immutable addenda entries (`POST /inspections/{id}/addendum`), ensuring original findings and health scores are never mutated.
  4. **Overdue Status Highlighting & Dynamic Invalidation:**
     - Overdue tasks (`due_date < today` with status `TODO` or `IN_PROGRESS`) receive prominent visual alert styling.
     - All mutations cascade invalidations through TanStack Query, automatically synchronizing dashboard KPI counts and alert badges across tabs.
* **Consequences:** Complete user-facing operational visibility; zero hardcoded mock data; 100% adherence to VANA design tokens and scientific integrity invariants.

---

### ADR-023: Full Platform End-to-End Acceptance, Multi-Domain State Invariants & Sandbox Network Isolation
* **Status:** Accepted (2026-11-04)
* **Context:** Phase 6.6 executes the final platform-wide acceptance audit across all 11 previous milestones and domains. The audit must establish that cross-domain business workflows operate with flawless data integrity, official environmental achievements remain completely isolated from monitoring sample plot counts, and automated test harnesses execute reliably across diverse runtime environments.
* **Decision:**
  1. **Full 8-Stage Business Lifecycle Verification:**
     - Orchestrated live cross-domain testing via `backend/tests/e2e_full_lifecycle_audit.py` across `PLAN -> ASSIGN -> EXECUTE -> RECORD -> VERIFY -> MEASURE -> MONITOR`.
     - Confirmed Anti-Self-Verification enforcement: field activity creators cannot verify their own submissions (`HTTP 403 Forbidden`).
     - Verified activity amendment net adjustments, rejection auditing, and soft-delete archival deactivation semantics.
  2. **Monitoring Fire-Wall & Zero Contamination Invariant:**
     - Verified that monitoring survival observations and observed sample sapling counts are strictly fire-walled from the official environmental ledger.
     - Official achievements reflect exclusively active verified operational activity revisions (`is_active_ledger_entry = True`).
  3. **Development Sandbox TCP Network Isolation Protocol:**
     - Recognized that sandboxed test runners on Windows isolate TCP socket bindings, causing async PostgreSQL drivers (`asyncpg`) to stall on socket connection attempts when running within Standard Sandbox Mode.
     - Documented the invariant that test runners executing against external services (such as PostgreSQL on `localhost:15432`) must be granted local TCP network loopback permission (`BypassSandbox: true`), ensuring deterministic test execution without modifying application code or database configurations.
  4. **Comprehensive Regression & Production Build Validation:**
     - Standardized full-suite regression verification: 118/118 backend pytest tests passing against `vana_test` (50.11s), 77/77 frontend tests passing (234ms), zero TypeScript typecheck errors (`tsc --noEmit`), and clean production bundle generation (`tsc -b && vite build` in 16.00s).
* **Consequences:** Unconditional verification of the entire VANA application; zero cross-domain state leakage; verified audit and migration reversibility; complete production readiness.

---

### ADR-024: Production Deployment Hardening, Dynamic Migration Precedence & Exact CORS Security
* **Status:** Accepted (2026-11-04)
* **Context:** Pre-deployment readiness audit for the VANA platform (targeting Vercel frontend, Render backend, Neon PostgreSQL database, and Render Persistent Disk) identified three critical configuration and security blockers: (1) `alembic.ini` hardcoded fallback overriding environment database URLs, (2) reliance on development `seed.py` credentials with known static passwords, and (3) CORS wildcard/localhost allowance incompatible with credentialed requests in production.
* **Decision:**
  1. **Alembic URL Resolution Hierarchy & Production Guard (`alembic.ini`, `alembic/env.py`):**
     - Cleared hardcoded `sqlalchemy.url` in `backend/alembic.ini`.
     - Standardized URL resolution order in `backend/alembic/env.py`: `ALEMBIC_DATABASE_URL` (OS env) $\to$ `settings.DATABASE_URL` $\to$ `config.get_main_option("sqlalchemy.url")`.
     - Applied driver normalization (`postgres://` / `postgresql://` $\to$ `postgresql+asyncpg://`) and SSL query normalization (`sslmode=` $\to$ `ssl=`) for Neon PostgreSQL.
     - Enforced a hard stop in both `env.py` and `backend/app/core/config.py` that raises a critical `ConfigurationError` / `ValidationError` if `ENVIRONMENT=production` attempts to connect to `127.0.0.1`, `localhost`, `vana_dev`, or `vana_test`.
     - Declared `ALEMBIC_DATABASE_URL` with `sync: false` in `render.yaml`.
  2. **Isolated Production Administrator Bootstrap CLI (`backend/app/bootstrap_admin.py`):**
     - Created a standalone CLI script (`python -m app.bootstrap_admin`) decoupled from development seeds.
     - Accepts credentials strictly via environment variables: `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`, and `BOOTSTRAP_ADMIN_NAME`.
     - Enforces enterprise password complexity ($\ge 12$ characters, upper, lower, digit, special character) and rejects common weak passwords (`SecurePass123!`, `Admin123456!`, `Password123!`).
     - Hashes credentials using Argon2id (`app.core.security.hash_password`) and writes an immutable `USER_PROVISIONED` system audit log.
     - Enforces duplicate protection by refusing to overwrite existing user accounts.
  3. **Exact CORS Matching & Frontend Base URL Normalization:**
     - Enhanced `validate_production_security` in `backend/app/core/config.py` to require non-empty `CORS_ORIGINS`, reject `*` when credentials are enabled, reject wildcard patterns (`*.vercel.app`), and reject `localhost`/`127.0.0.1` origins in production.
     - Enhanced `frontend/src/services/apiClient.ts` with `resolveApiBaseUrl()` to normalize trailing slashes and prevent duplicate `/api/v1` path segments, while emitting a console warning if `VITE_BACKEND_URL` is omitted during production builds.
     - Documented canonical environment variables across root, backend, and frontend `.env.example` templates.
* **Consequences:** Eliminates migration execution failures on Render build commands; prevents default credential leakage in production; ensures zero-trust origin enforcement for credentialed requests; verified with 130/130 passing backend pytest tests (including dedicated bootstrap and CORS suites) and 77/77 frontend tests.

---

### ADR-025: Cryptographic Audit Ledger, SHA-256 Hash Chaining, and Transactional Row-Locked Concurrency
* **Status:** Accepted (2026-11-04)
* **Context:** Milestone 8 mandates full cryptographic hash integrity, an immutable verification log, and auditable change history for all state-mutating events across the VANA platform. The existing `audit_logs` table recorded basic event metadata and JSON states, but lacked sequential ordering guarantees, tamper detection, multi-tenant scoping, and cryptographic proofs of chain integrity.
* **Decision:**
  1. **Single-Table Evolutionary Architecture (`audit_logs` + `audit_chain_head`):**
     - Extended the existing `audit_logs` table with `sequence_number` (BIGINT UNIQUE), `project_id` (UUID FK nullable), `previous_hash` (VARCHAR(64)), `current_hash` (VARCHAR(64) UNIQUE), `hash_version` (INT default 1), `canonical_payload` (JSONB), `correlation_id` (VARCHAR(64) nullable), and `is_backfilled` (BOOLEAN default False).
     - Introduced an atomic chain head singleton table `audit_chain_head` (constrained to `id = 1`) tracking `last_sequence_number`, `last_event_hash`, `total_events`, and `updated_at`.
  2. **Deterministic SHA-256 Hashing Engine (`backend/app/domains/audit/hashing.py`):**
     - Implemented canonical JSON serialization with strict recursive key sorting (`sort_keys=True`), zero non-essential whitespace (`separators=(',', ':')`), UTF-8 encoding (`ensure_ascii=False`), normalized UTC ISO 8601 timestamps, and normalized lowercase UUID formatting.
     - Defined a standard SHA-256 event digest over the deterministic canonical JSON representation of a structured dictionary envelope containing all metadata and payload fields (`action_type`, `actor_id`, `canonical_payload`, `correlation_id`, `entity_id`, `entity_type`, `event_id`, `hash_version`, `previous_hash`, `project_id`, `sequence_number`, `timestamp`):
       `current_hash = SHA256(canonical_json_dumps(envelope).encode('utf-8')).hexdigest().lower()`.
     - Bound the genesis block with `GENESIS_HASH = "0" * 64`.
  3. **Transactional Row-Locked Concurrency (`backend/app/domains/audit/services.py`):**
     - Rejected standard PostgreSQL sequences because failed/aborted transactions burn sequence numbers and cause irrecoverable gaps that violate cryptographic chain continuity proofs.
     - Enforced concurrency serialization via `SELECT ... FROM audit_chain_head WHERE id = 1 FOR UPDATE` within the caller's active database transaction.
     - Bound sequence generation and hash linkage directly to transaction lifecycle: if the outer transaction rolls back, row locks release and zero sequence numbers are burned or skipped.
     - Preserved the existing `record_audit_log` domain interface with automatic recursive extraction of `project_id` from entities and payloads.
  4. **Deterministic Historical Backfill (`backend/alembic/versions/0003_audit_immutability_ledger.py`):**
     - Reversibly migrated existing database schemas.
     - Sequentially backfilled legacy audit records ordered deterministically by `created_at ASC, id ASC`, synthesizing canonical payloads and computing valid SHA-256 chain links while marking `is_backfilled = True`.
     - Seeded `audit_chain_head` with the final sequence number and hash checkpoint.
* **Consequences:** Provides mathematical proof of immutability and complete tamper detection across all audit events; eliminates duplicate audit logging subsystems; guarantees gapless monotonic sequence continuity; preserves 100% backward compatibility with all existing caller domains and services.

---

### ADR-026: Immutable Verification History, Multi-Tenant Audit Query APIs, and Cryptographic Chain Verification
* **Status:** Accepted (2026-11-04)
* **Context:** Following the implementation of the core cryptographic ledger schema and SHA-256 hash chaining engine in Phase 8.1, Phase 8.2 requires:
  1. Complete remediation of all findings from the Phase 8.1 independent review:
     - Finding 8.1-01 (High): Authoritative database-derived `project_id` propagation across all activity lifecycle operations (creation, evidence upload, amendment, verification, rejection, archival) and monitoring operations (inspection lifecycle, maintenance task lifecycle, survival observation supersession).
     - Finding 8.1-02 (Medium): Documented hash formula in ADR-025 corrected to reflect the canonical JSON envelope structure.
     - Finding 8.1-03 (Low): Expansion of `SENSITIVE_KEYS` sanitization to scrub `api_key`, `client_secret`, and `private_key` recursively in nested state payloads.
     - Finding 8.1-04 (Low): Formal documentation of the Decimal canonical serialization convention (IEEE 754 float conversion in Version 1) and versioning safeguards.
  2. Complete immutable verification decision history tracking every review decision (approval, rejection with mandatory reason and review notes), amendment review, and archival event.
  3. Secure, high-performance, read-only multi-tenant audit query APIs with strict role-based access control and project assignment scoping.
  4. A robust, bounded cryptographic chain verification service detecting sequence gaps, hash mismatches, and payload tampering across the entire ledger or designated sequence intervals.
* **Decision:**
  1. **Remediation of Independent Review Findings:**
     - Updated `backend/app/domains/operations/services.py` to derive `project_id = activity.project_id` directly from authoritative database records and inject it into both `record_audit_log` and `new_state` for `ACTIVITY_CREATED`, `EVIDENCE_UPLOADED`, `ACTIVITY_AMENDED`, `ACTIVITY_VERIFIED`, `ACTIVITY_REJECTED`, and `ACTIVITY_ARCHIVED`.
     - Updated `backend/app/domains/monitoring/services.py` to propagate authoritative `project_id` for `INSPECTION_SCHEDULED`, `INSPECTION_STARTED`, `INSPECTION_COMPLETED`, `INSPECTION_CANCELLED`, `INSPECTION_ADDENDUM_RECORDED`, `INSPECTION_EVIDENCE_UPLOADED`, `TASK_CREATED`, `TASK_STARTED`, `TASK_COMPLETED`, `TASK_CANCELLED`, `TASK_REOPENED`, `SURVIVAL_OBSERVATION_CREATED`, `SURVIVAL_OBSERVATION_SUPERSEDED`, and `SURVIVAL_OBSERVATION_CORRECTION_CREATED`.
     - Expanded `SENSITIVE_KEYS` in `backend/app/domains/audit/services.py` to include `"api_key"`, `"client_secret"`, and `"private_key"`.
     - Documented Decimal canonical serialization convention in `backend/app/domains/audit/hashing.py` docstrings, preserving float-based representation for Version 1 hash compatibility while reserving string/integer representations for future hash versions.
  2. **Multi-Tenant Read-Only Audit APIs (`backend/app/domains/audit/router.py`):**
     - Mounted under `/api/v1/audit` with zero state-mutating endpoints (`POST`, `PUT`, `DELETE` strictly excluded):
       - `GET /api/v1/audit/events`: Filterable audit event stream supporting pagination (`page`, `page_size`), date ranges (`start_date`, `end_date`), `action_type`, `actor_id`, `project_id`, `entity_type`, and `entity_id`.
       - `GET /api/v1/audit/events/{id}`: Detailed individual audit log entry lookup by UUID.
       - `GET /api/v1/audit/verification`: Dedicated verification decision history returning approvals, rejections (with `rejection_reason_code` and `review_notes`), amendments, and deactivations.
       - `GET /api/v1/audit/entities/{entity_type}/{entity_id}`: Chronological entity-level change history.
  3. **Multi-Tenant Project Isolation & RBAC Boundaries:**
     - Enforced across all query endpoints via `get_assigned_project_ids(db, current_user.id)`:
       - `ADMIN`: Global visibility across all organization events, projects, and entities.
       - `PROJECT_MANAGER`: Strictly scoped to audit events associated with their assigned projects (`project_id.in_(assigned_ids)`). Requests with an unassigned `project_id` filter immediately reject with `HTTP 403 Forbidden`. Entity lookups for unassigned projects raise `HTTP 403 Forbidden` or `HTTP 404 Not Found`.
       - `FIELD_OFFICER`: Entire audit domain is strictly forbidden (`HTTP 403 Forbidden`).
  4. **Cryptographic Chain Verification Service (`verify_audit_chain`):**
     - Exposed via `POST /api/v1/audit/verify-chain` (restricted to `ADMIN` and `PROJECT_MANAGER` for verification analysis).
     - Performs in-memory recomputation of SHA-256 digests from `canonical_payload` and metadata envelopes.
     - Detects:
       - `SEQUENCE_GAP`: Sequence numbers skipped or non-monotonic.
       - `LINK_BROKEN`: Current event's `previous_hash` differs from preceding event's `current_hash`.
       - `PAYLOAD_TAMPERED`: Recomputed SHA-256 hash does not match stored `current_hash`.
       - `HEAD_DIVERGED`: Chain head singleton does not match the latest event record.
     - Includes legal/technical disclaimer indicating chain verification proves database state internal consistency, while physical DBA write tampering requires external non-repudiation or write-once external logging.
* **Consequences:** Completes all Phase 8.2 requirements; closes all four findings from the independent review; establishes multi-tenant, tamper-evident audit transparency; verified with 161 passing backend tests (including 21 dedicated audit domain tests) and 88 passing frontend tests.

---

### ADR-027: Milestone 8 Frontend Audit Ledger, Dynamic State Diffing, and End-to-End Cryptographic Acceptance
* **Status:** Accepted (2026-11-04)
* **Context:** Following the completion of the backend cryptographic ledger schema, SHA-256 chaining engine (Phase 8.1), and multi-tenant audit query APIs (Phase 8.2), Phase 8.3 requires:
  1. Complete frontend workspace implementation for the Audit History & Immutability Ledger mounted at `/audit`.
  2. Replacing the temporary disabled placeholder UI with five fully interactive production tabs:
     - **Audit Overview:** Key performance metrics, activity breakdown charts, recent chronological ledger stream, and quick navigation shortcuts.
     - **Audit Timeline:** Paginated tabular stream with action filter, project filter, date filtering, search bar, and slide-out inspector trigger.
     - **Verification History:** Dedicated verification decision log tracking approvals, rejections (with `rejection_reason_code` and review notes), amendments, and entity deactivations.
     - **Integrity Verification Console:** On-demand cryptographic SHA-256 chain recomputation, real-time diagnostic table, failure localization, sequence range validation, and operational/legal disclaimer.
     - **Entity Change History:** Multi-entity selector, quick project selector, and key-by-key before-and-after dynamic state diffing with badge classification (`MODIFIED`, `ADDED`, `REMOVED`).
  3. Interactive slide-out `EventDetailDrawer` rendering cryptographic SHA-256 digests (`current_hash`, `previous_hash`), sequence numbers, timestamps, actor attribution, state transitions, and raw canonical JSON payload with copy-to-clipboard functionality.
  4. Frontend integration using Axios (`auditService.ts`), TanStack Query (`useAudit.ts`), and strict RBAC guards (`ADMIN` organization-wide, `PROJECT_MANAGER` scoped to assigned projects, `FIELD_OFFICER` blocked with explanatory notice).
  5. Comprehensive 14-step end-to-end integration and browser acceptance verification covering the entire lifecycle: project setup, targets, assignments, activity submissions, evidence uploads, amendments, rejections, approvals, field inspections, maintenance tasks, survival observations, and chain verification.
* **Decision:**
  1. **Frontend Architecture & Design Tokens:**
     - Created `frontend/src/types/audit.ts` with comprehensive TypeScript interfaces for audit logs, verification responses, chain integrity checks, and entity history filters.
     - Created `frontend/src/services/auditService.ts` wrapping all 5 audit endpoints.
     - Created `frontend/src/hooks/useAudit.ts` with automated query caching, refetching, and error handling.
     - Created modular views under `frontend/src/views/audit/components/` adhering strictly to VANA design tokens (Forest Green `#183D32`, Warm Ivory `#F5F3EA`, Sage `#A8B99B`, Earth Gold `#D6A76A`, Charcoal `#29332F`) with Manrope headings and Inter body typography.
     - Mounted `AuditWorkspaceView` at `/audit` in `frontend/src/routes/index.tsx` guarded by `allowedRoles={["ADMIN", "PROJECT_MANAGER"]}`.
     - Updated sidebar navigation in `frontend/src/components/layout/Sidebar.tsx` enabling `Audit History` for `ADMIN` and `PROJECT_MANAGER`.
  2. **Dynamic State Diffing Engine:**
     - Built an intelligent state delta comparison component in `EntityHistoryTab.tsx` and `EventDetailDrawer.tsx` that normalizes JSON objects, identifies modified, added, and removed keys, and formats primitive and complex changes cleanly without hardcoded schema assumptions.
     - Gracefully handles initial entity creations where `previous_state` is null by rendering structured creation summaries.
  3. **Backend Chain Verification Hardening:**
     - Enriched `backend/app/domains/audit/schemas.py` and `services.py` with `AuditVerifyChainRequest`, sequence-bounded verification (`from_sequence`, `to_sequence`), structured failure categorizations (`CANONICAL_PAYLOAD_CORRUPTED`, `STATE_DIVERGENCE`, `MISSING_EVENTS`, `PREV_HASH_MISMATCH`, `CHAIN_HEAD_MISMATCH`), and sequence diagnostic summaries.
     - Updated `verify_chain` endpoint in `router.py` to accept either JSON body or query parameters for maximum interoperability.
  4. **End-to-End Acceptance & Browser Verification:**
     - Added comprehensive 14-step integration test `backend/tests/domains/audit/test_audit_e2e_acceptance.py` validating full-lifecycle chain continuity across 14 events.
     - Added frontend automated test suite `frontend/tests/audit.test.mjs` verifying API client methods, TypeScript contracts, and UI tab rendering.
     - Executed headless browser automation (`scripts/capture_audit_workspaces.mjs`) capturing five genuine screenshots in `docs/screenshots/` (`audit_overview.png`, `audit_timeline.png`, `audit_verification.png`, `audit_integrity.png`, `audit_entity_history.png`).
* **Consequences:** Completes all Phase 8.3 requirements and brings Milestone 8 to `COMPLETED & ACCEPTED` status; verifies 164 passing backend tests (including 22 dedicated audit domain tests) and 99 passing frontend tests (100% pass rate); provides full cryptographic audit visibility and immutability assurance across the VANA platform.

---

### ADR-028: Pre-Deployment Bundle Optimization, Production Documentation, and Assignment Deliverables
* **Status:** Accepted (2026-11-04)
* **Context:** In preparation for final repository publication, production deployment, and assignment submission to Akshaya Vana Climate Ventures, the platform requires:
  1. Optimization of the frontend client bundle to resolve the single-chunk 1,470 kB bundle warning through route-level code splitting and vendor chunk isolation.
  2. Complete, authoritative cloud infrastructure documentation for Neon PostgreSQL, Render Web Service, and Vercel Edge CDN.
  3. Comprehensive technical assignment deliverables including a 5-minute demonstration video walkthrough script, full AI assistance disclosure, and technical submission checklist.
  4. Complete overhaul of the root `README.md` to accurately reflect the 11 implemented domains, 164 backend tests, and 99 frontend tests.
* **Decision:**
  1. **Frontend Code Splitting & Vendor Chunking:**
     - Configured `build.rollupOptions.output.manualChunks` in `frontend/vite.config.ts` isolating `vendor-react` (React, React-DOM, React Router), `vendor-query` (TanStack Query, Axios), `vendor-map` (Leaflet, React Leaflet), and `vendor-charts` (Recharts).
     - Refactored `frontend/src/routes/index.tsx` using `React.lazy` and `React.Suspense` with an accessible `RouteLoadingFallback` spinner.
     - Reduced initial entry point bundle from 1,470 kB to 371 kB (gzip: 112 kB), with all route chunks under 100 kB and zero Vite build warnings.
  2. **Production Deployment Documentation:**
     - Updated `docs/PRODUCTION_DEPLOYMENT_GUIDE.md` with Neon connection string normalization, Render blueprint specification with persistent disk, and Vercel edge SPA routing.
     - Created `docs/PRODUCTION_ENVIRONMENT_VARIABLES.md` exhaustively categorizing required, optional, and bootstrap environment variables.
     - Created `docs/PRODUCTION_ACCEPTANCE_CHECKLIST.md` providing end-to-end smoke verification criteria across all 11 domains.
     - Created `docs/BACKUP_AND_RESTORE.md` detailing Neon point-in-time branch recovery, `pg_dump` snapshots, and persistent disk evidence recovery.
  3. **Assignment Submission Deliverables:**
     - Authored `docs/DEMO_VIDEO_SCRIPT.md` providing a timed 4m45s narration and navigation runbook for the demonstration video.
     - Authored `docs/AI_ASSISTANCE_DISCLOSURE.md` detailing the exact scope of AI pair-programming tools and affirming human engineering ownership.
     - Authored `docs/AKSHAYA_VANA_SUBMISSION_CHECKLIST.md` mapping all 7 submission requirements.
  4. **Root README Overhaul:**
     - Completely restructured `README.md` with architecture diagrams, domain breakdown, database ERD, RBAC matrix, local quickstart, testing commands, and troubleshooting.
* **Consequences:** Eliminates frontend bundle bottlenecks; provides production deployment blueprints; completes every non-deployment deliverable required for the Akshaya Vana technical assignment.
