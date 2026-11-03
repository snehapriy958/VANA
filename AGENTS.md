# VANA — Permanent Engineering Rules & Agent Guidelines

> **Mandatory Policy:** This document defines the permanent engineering boundaries, architectural invariants, and operational rules for the VANA codebase. Every AI agent, engineer, and technical contributor must read and strictly adhere to these instructions before planning or executing any task.

---

## 1. Architectural Invariants

1. **Modular Monolith Architecture:**
   * Maintain the codebase as a domain-driven modular monolith.
   * Maintain strict physical and logical separation between `frontend/` (React 19 SPA) and `backend/` (FastAPI).
   * Do not introduce microservices, distributed task queues (Kafka, RabbitMQ), service meshes, or unnecessary infrastructure without explicit architectural approval.
   * Organize backend modules into cohesive domain packages (`auth`, `projects`, `teams`, `operations`, `verification`, `analytics`, `audit`) with well-defined service interfaces to allow future extraction if justified by scale.

2. **Technology Stack Exclusivity:**
   * Never change the approved technology stack without explicit architectural sign-off.
   * **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, React Router, TanStack Query, React Hook Form, Zod, Recharts, React Leaflet, Axios.
   * **Backend:** Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PostgreSQL, JWT Authentication, Argon2 password hashing.
   * **Infrastructure:** Docker, GitHub, Vercel (frontend deployment), Render (backend deployment), Neon PostgreSQL (database).
   * Never introduce an unapproved third-party dependency, external UI library, or specialized spatial database extension (e.g., PostGIS) into the MVP.

3. **PostgreSQL as the Single Source of Truth:**
   * PostgreSQL is the authoritative system of record.
   * Never store canonical state in ephemeral memory, local files, client local storage, or transient cache stores.
   * Use Alembic for all database migrations. Every schema alteration must have a reversible migration script. Never run manual `ALTER TABLE` commands.

---

## 2. Security & Access Control

4. **Independent Backend Authorization:**
   * Frontend route guards and UI toggles exist solely for user experience.
   * The backend must enforce authentication, role permissions, project assignments, and entity ownership on every single HTTP endpoint independently.
   * Support the three user roles:
     * `ADMIN`: Organization-wide administrative access.
     * `PROJECT_MANAGER`: Scoped strictly to assigned projects.
     * `FIELD_OFFICER`: Scoped strictly to assigned projects for submission.

5. **Anti-Self-Verification Rule:**
   * Under no circumstances may a user verify their own activity submission (`verifier_id != creator_id`).
   * Attempted self-verification must be rejected by backend business logic with `HTTP 403 Forbidden`.

6. **Audit Trail Integrity:**
   * Maintain an immutable audit history for all critical system mutations (verification approvals, rejections, amendments, target updates, and role assignments).
   * Never overwrite or delete historical verification events.

---

## 3. Environmental Accounting & Calculation Logic

7. **Verified-Only Official Achievements:**
   * Only active, approved (`VERIFIED`) activity revisions contribute to official environmental achievements.
   * Maintain a strict separation between:
     * **Current Verified Quantity:** Active approved revisions.
     * **Current Pending Quantity:** Active unreviewed revisions.
     * **Current Rejected Quantity:** Active rejected revisions.
     * **Historical Rejected Submission Count:** Total historical rejection events for audit.
     * **Reported Quantity:** Current Verified + Current Pending.
   * Historical revisions must never be counted multiple times or inflate current quantities.

8. **Strict Unit and Metric Dimensionality:**
   * Never aggregate two different `metric_code` identifiers, even if they share the same dimensional family.
   * Never aggregate incompatible units (e.g., trees with hectares, or kilograms with liters).
   * Conversions are permitted only within the same metric definition using predefined conversion coefficients.

9. **Data Grounding & Scientific Integrity:**
   * Never invent carbon sequestration, soil conservation, biodiversity, or survival-rate calculations.
   * Display only metrics supported by actual recorded data and explicitly documented measurement methodologies.
   * Never hardcode dashboard statistics or environmental achievements.

---

## 4. Engineering Quality & Workflow Discipline

10. **Documentation First:**
    * Always read relevant documentation in `docs/` before implementing any feature.
    * Do not begin implementation until the milestone scope has been reviewed and approved.

11. **Milestone-by-Milestone Execution:**
    * Implement one approved milestone at a time.
    * Never start work on a subsequent milestone while the current milestone has incomplete deliverables or failing tests.
    * Update `IMPLEMENTATION_STATUS.md` immediately upon completing any milestone.
    * Record all significant technical choices and architectural deviations in `DECISION_LOG.md`.

12. **Rigorous Testing Standards:**
    * Write comprehensive unit tests for all business logic, verification state machines, and mathematical calculation engines.
    * Write integration tests for API endpoints verifying authentication, RBAC, and input validation.
    * Never mark an untested feature as complete.

13. **Design System Consistency:**
    * Adhere strictly to the VANA design tokens (Forest Green `#183D32`, Warm Ivory `#F5F3EA`, Sage `#A8B99B`, Earth Gold `#D6A76A`, Charcoal `#29332F`, White `#FFFFFF`).
    * Use `Manrope` for headings and `Inter` for body text.
    * Never duplicate business logic between frontend and backend.
