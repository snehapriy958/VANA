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
