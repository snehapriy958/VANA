# VANA — Implementation Roadmap

This roadmap outlines the sequential, milestone-based execution plan for engineering the VANA platform. Each milestone represents a discrete, testable increment. In accordance with [AGENTS.md](AGENTS.md), implementation must proceed strictly one approved milestone at a time.

---

## Roadmap Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│  MILESTONE 0: Architecture, Design Specifications & Governance         │
│  [Status: IN PROGRESS / PENDING APPROVAL]                               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  MILESTONE 1: Project Scaffolding, Database Schema & Migrations        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  MILESTONE 2: Authentication, RBAC & User Management                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  MILESTONE 3: Project Portfolio, Geospatial Metadata & Targets         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  MILESTONE 4: Field Operations, Activity Reporting & Evidence Storage  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  MILESTONE 5: Verification Centre, Revision Engine & Anti-Self-Gate    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  MILESTONE 6: Verified Environmental Ledger & Recalculation Engine     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  MILESTONE 7: Living Earth Interactive Map & Geospatial Visualization  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  MILESTONE 8: Organization Dashboard, Analytics & Deployment Hardening │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Milestone Breakdown

### Milestone 0: Documentation, Design System & Architecture
* **Goal:** Establish a complete, verified architectural blueprint and design specification before writing application code.
* **Deliverables:**
  * Complete design specifications in `docs/design/` (01 to 10).
  * Complete engineering specifications in `docs/engineering/` (01 to 07).
  * Complete scalability specifications in `docs/scalability/` (01 to 03).
  * Permanent engineering rules (`AGENTS.md`), Project Overview (`README.md`), Decision Log (`DECISION_LOG.md`), Review Checklist (`DESIGN_REVIEW_CHECKLIST.md`).
* **Verification Criteria:** Consistency review passes across all docs; design review checklist verified; user sign-off obtained.

### Milestone 1: Project Scaffolding, Database Schema & Migrations
* **Goal:** Initialize frontend and backend directories, configure Docker and database connections, and create baseline Alembic migrations.
* **Deliverables:**
  * `backend/`: FastAPI application factory, database connection engine, SQLAlchemy 2.x base models.
  * `frontend/`: Vite + React 19 + TypeScript scaffolding, Tailwind CSS configuration with VANA tokens, shadcn/ui setup.
  * Relational tables: `users`, `projects`, `project_assignments`, `project_targets`, `field_activities`, `activity_revisions`, `evidence_files`, `audit_logs`.
  * Initial Alembic migration script and schema rollback test.
* **Verification Criteria:** `alembic upgrade head` and `alembic downgrade base` execute cleanly against PostgreSQL without error.

### Milestone 2: Authentication, RBAC & User Management
* **Goal:** Implement secure authentication and organization-wide role-based access control.
* **Deliverables:**
  * Argon2 password hashing utility; JWT access and refresh token generation and verification.
  * RBAC dependency guards: `@require_role(["ADMIN", "PROJECT_MANAGER", "FIELD_OFFICER"])`.
  * User management API endpoints (Create user, list users, assign role, deactivate).
  * Project assignment service (assign PMs and Field Officers to projects).
  * Frontend Login page, auth context provider, token persistence, and authenticated layout.
* **Verification Criteria:** Unit and integration tests verify token expiry, invalid token rejection, and role-based route blocking.

### Milestone 3: Project Portfolio, Geospatial Metadata & Targets
* **Goal:** Implement project creation, management, geographic bounding, and dimensional target setting.
* **Deliverables:**
  * Project CRUD API endpoints with status transitions (`DRAFT`, `ACTIVE`, `COMPLETED`, `ARCHIVED`).
  * Center coordinates validation (`-90 <= lat <= 90`, `-180 <= lng <= 180`) and optional GeoJSON boundary storage.
  * Project target definition API with metric code selection, dimension matching, and deadline tracking.
  * Frontend Project Explorer and Project Workspace views with tabbed navigation.
* **Verification Criteria:** Cannot create a target with invalid metric codes or negative quantities; project scoping restricts PMs to assigned projects.

### Milestone 4: Field Operations, Activity Reporting & Evidence Storage
* **Goal:** Deliver mobile-friendly field reporting and secure file attachment storage.
* **Deliverables:**
  * Abstract storage provider `IStorageService` and implementation `LocalStorageService` (SHA-256 hashed files).
  * Activity submission endpoint creating a logical parent `field_activity` and revision 1 in `activity_revisions`.
  * Input validation: ensures metric category and unit match metric code definitions; records GPS coordinates and accuracy.
  * Mobile-optimized frontend Field Reporting form with touch-friendly controls and file attachment preview.
* **Verification Criteria:** Successful submission creates activity in `PENDING` status; evidence file stored correctly; Pydantic rejects incompatible units.

### Milestone 5: Verification Centre, Revision Engine & Anti-Self-Gate
* **Goal:** Implement the triage verification queue, rejection workflows, and revision lineage tracking.
* **Deliverables:**
  * Verification triage queue API endpoint (filter by project, date, submitter).
  * Approval and Rejection endpoints:
    * Rejection requires mandatory `rejection_reason_code` and review notes.
    * Enforce anti-self-verification gate: `verifier_id != creator_id`.
  * Activity revision endpoint: Field Officer resubmits a corrected revision linked to the parent activity.
  * Frontend Verification Centre with split-screen triage (queue on left, evidence and map pin on right).
* **Verification Criteria:** Attempting to self-verify returns `HTTP 403 Forbidden`; rejecting without a reason code returns `HTTP 422 Unprocessable Entity`; revision creates a new pending record while preserving historical rejected record.

### Milestone 6: Verified Environmental Ledger & Recalculation Engine
* **Goal:** Implement transactionally safe environmental metric rollups with strict unit and dimensional integrity.
* **Deliverables:**
  * Recalculation service: recalculates `current_verified_quantity`, `current_pending_quantity`, `current_rejected_quantity`, and `reported_quantity` inside a database transaction upon verification events.
  * Mathematical unit converter: supports exact conversions only within the same metric code to canonical unit.
  * Zero-cross-metric aggregation rule: prevents summing disparate metric codes.
  * Frontend Project Workspace balance sheet displaying official progress vs. targets.
* **Verification Criteria:** Math tests verify that only active approved revisions contribute to official achievement; pending and rejected quantities do not leak into verified totals; unit conversions match exact mathematical constants.

### Milestone 7: Living Earth Interactive Map & Geospatial Visualization
* **Goal:** Integrate full interactive mapping with project boundaries, markers, and activity pins.
* **Deliverables:**
  * React Leaflet interactive map with custom styling adhering to VANA palette.
  * Layer toggles: Project Markers, Boundary Polygons, Activity Pins (color-coded by verification status).
  * Activity pin click-to-inspect drawer showing photo thumbnail, quantity, and verification state.
  * Responsive mobile bottom-sheet for map pin inspection.
* **Verification Criteria:** Map renders correctly on desktop and mobile; pins render at accurate coordinates; missing boundary polygons gracefully fall back to center marker.

### Milestone 8: Organization Dashboard, Analytics & Deployment Hardening
* **Goal:** Complete executive dashboard, impact analytics visualizations, audit history inspector, and end-to-end deployment verification.
* **Deliverables:**
  * Organization Dashboard with aggregate portfolio health, verified achievement counters, and verification velocity sparklines.
  * Impact Analytics page with Recharts visualizations based strictly on verified historical records.
  * Audit History viewer with chronological filtering and JSON diff modal.
  * Seed data script with realistic, documented demonstration fixtures.
  * Production Dockerfile, Vercel frontend build test, Render backend configuration documentation.
* **Verification Criteria:** Full end-to-end test suite passes; zero linting or TypeScript errors; lighthouse accessibility score $\ge 90$; seed script loads cleanly.
