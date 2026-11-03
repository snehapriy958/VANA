# VANA — Design & Architecture Review Checklist

This checklist audits the technical, architectural, and design compliance of the VANA platform prior to the authorization of application development.

---

## 1. Architectural & Technology Stack Compliance

- [x] **Modular Monolith Integrity:** The platform is architected as a domain-driven modular monolith with strict separation between `frontend/` and `backend/`.
- [x] **No Unapproved Infrastructure:** No microservices, Kafka, RabbitMQ, or unauthorized message brokers are introduced.
- [x] **Approved Frontend Stack:** Strictly utilizes React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, React Router, TanStack Query, React Hook Form, Zod, Recharts, React Leaflet, and Axios.
- [x] **Approved Backend Stack:** Strictly utilizes Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PostgreSQL, JWT authentication, and Argon2 hashing.
- [x] **Single Source of Truth:** PostgreSQL is the sole authoritative system of record; no canonical state resides in memory or transient caches.
- [x] **Alembic Exclusivity:** All database changes require version-controlled, reversible Alembic migrations.

---

## 2. Visual Design & Design System Standards

- [x] **Brand Palette Compliance:** Design uses Forest Green (`#183D32`), Warm Ivory (`#F5F3EA`), Sage (`#A8B99B`), Earth Gold (`#D6A76A`), Charcoal (`#29332F`), and White (`#FFFFFF`).
- [x] **Typography Pairing:** Headings use `Manrope` (tight tracking `-0.02em`, bold weights); body text and tabular figures use `Inter`.
- [x] **No Superficial Dashboards:** Excessive gradients, neon accents, heavy glassmorphism, and disruptive animations are explicitly prohibited.
- [x] **Consistent Spacing Grid:** Interfaces follow a strict 4px/8px modular spacing system.
- [x] **Accessible Contrast:** Text and interactive elements meet WCAG 2.1 AA standards (minimum 4.5:1 for body text, 3:1 for large headings).

---

## 3. Screen Specifications & Wireframe Coverage

- [x] **10 MVP Screens Specified:** Comprehensive specifications prepared for Login, Organization Dashboard, Project Explorer, Project Workspace, Living Earth Map, Field Reporting, Verification Centre, Impact Analytics, Team Management, and Audit History.
- [x] **Wireframe Fidelity:** Detailed structural ASCII wireframes provided for both Desktop (1440px) and Mobile (375px) viewports.
- [x] **Component Inventory:** Core reusable components (buttons, input fields, badge pills, split-screen queues, map drawers) cataloged with all states.
- [x] **State Handling:** Loading skeletons, empty states, error banners, optimistic UI updates, and disabled interactions fully documented.

---

## 4. Authorization, RBAC & Verification Security

- [x] **Independent Backend Authorization:** FastAPI endpoints enforce JWT and RBAC checks independently of client-side routing.
- [x] **Three User Roles:** `ADMIN` (organization-wide), `PROJECT_MANAGER` (assigned projects only), and `FIELD_OFFICER` (assigned projects only) clearly partitioned.
- [x] **Anti-Self-Verification Gate:** System prevents any user from verifying an activity they submitted (`verifier_id != creator_id`).
- [x] **Immutable Audit Record:** Verification records capture `verifier_id`, `verified_at`, `decision`, `rejection_reason_code`, and `review_notes`.

---

## 5. Environmental Accounting & Calculation Logic

- [x] **Verified-Only Official Achievements:** Only active approved revisions contribute to official project totals.
- [x] **Distinct Accounting Categories:** Strict mathematical separation maintained between:
  - Current Verified Quantity
  - Current Pending Quantity
  - Current Rejected Quantity
  - Historical Rejected Submission Count
  - Reported Quantity (`Current Verified + Current Pending`)
- [x] **No Incompatible Unit Aggregation:** Aggregations across differing dimensions (`COUNT`, `AREA`, `VOLUME`, `MASS`) are strictly blocked.
- [x] **Metric Code Isolation:** Different metric codes (e.g. `TREES_PLANTED` vs `SAPLINGS_PLANTED`) are never aggregated together, even if sharing the same dimension.
- [x] **Explicit Conversion Rules:** Unit conversions are permitted only within the same metric code to its canonical base unit.
- [x] **Revision Lineage & Deduplication:** Revisions do not cause duplicate counting; active approved revisions supersede prior revisions cleanly.
- [x] **Data Grounding Standard:** No synthetic carbon sequestration, soil conservation, biodiversity, or theoretical survival multipliers are calculated or displayed.

---

## 6. Storage, Infrastructure & Deployment

- [x] **Storage Abstraction:** `IStorageService` interface abstracts local development storage (`LocalStorageService`) from cloud object stores.
- [x] **Deployment Safety:** Storage paths stored as relative keys; documentation specifies production persistence configuration to avoid data loss on ephemeral filesystems.
- [x] **Native Relational GIS:** Standard relational columns (`DOUBLE PRECISION` for coordinates) and GeoJSON text/JSONB for optional boundary polygons; no unapproved PostGIS dependencies.
- [x] **Mobile-Friendly Online Submission:** Field reporting is responsive and mobile-first with touch-friendly ergonomics ($\ge 44\text{px}$); offline synchronization is cleanly deferred to Phase 2.

---

## 7. Sign-off Status

* **Design Review Completed By:** Senior Product Architect, UI/UX Designer & Technical Lead
* **Date:** 2026-11-02
* **Compliance Status:** **100% COMPLIANT WITH USER DIRECTIVES**
* **Next Action:** Finalize documentation generation and present for user sign-off prior to Milestone 1 coding.
