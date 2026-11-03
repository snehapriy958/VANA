# VANA — MVP Design Scope & Boundaries

This document formalizes the explicit boundary between the minimum viable product (MVP) scope and deferred future enhancements.

---

## 1. Prioritized MVP Scope Matrix (P1–P11)

| Priority | Module / Capability | MVP Scope Commitment | Technical Implementation Boundary |
|---|---|---|---|
| **P1** | **Authentication & RBAC** | Secure JWT auth, Argon2 password hashing, role enforcement (`ADMIN`, `PROJECT_MANAGER`, `FIELD_OFFICER`). | Standard email/password flow; no MFA in MVP; backend authorization independently guards every endpoint. |
| **P2** | **Organization Dashboard** | High-level portfolio cards, verified totals, active projects breakdown, verification velocity ticker. | Relational SQL rollups; cached aggregates; strictly verified data displayed. |
| **P3** | **Project Management** | Project creation, status lifecycle (`DRAFT`, `ACTIVE`, `COMPLETED`, `ARCHIVED`), center coordinates, optional polygon boundary, project targets. | Stored in PostgreSQL with standard relational types; boundary stored as GeoJSON text/JSONB. |
| **P4** | **Project Workspace** | Tabbed project command center, target vs. verified balance sheet, team allocation list, localized map. | Target progress calculated strictly from active approved revisions. |
| **P5** | **Team & User Management** | User roster, role assignment, project assignment matrix. | Admin can invite users and assign roles; PMs can assign field officers to their assigned projects. |
| **P6** | **Field Activity Reporting** | Mobile-first activity submission: project selector, metric code, quantity, GPS coordinates, photo upload, notes. | Fully responsive web UI; requires active internet connection; photo stored via `IStorageService`. |
| **P7** | **Activity Verification Centre** | Triage review queue, photo lightbox, coordinate review, approve/reject state machine with mandatory reasons. | Enforces anti-self-verification gate (`verifier_id != creator_id`); records immutable verifier signature. |
| **P8** | **Verified Achievement Engine** | Transactional ledger updating project progress upon approval. Strict dimensional matching and conversion rules. | Unit conversions permitted only within same metric code to canonical unit; zero cross-metric aggregation. |
| **P9** | **Basic Living Earth Map** | Interactive React Leaflet map with project markers, boundary polygons, and status-coded activity pins. | Standard Leaflet tiles; client-side rendering of GeoJSON boundaries and coordinate markers. |
| **P10** | **Basic Impact Analytics** | Verified metric rollups by project, dimensional progress charts (Recharts), CSV export. | Purely empirical charts based on verified history; zero synthetic or speculative multipliers. |
| **P11** | **Audit History** | Chronological ledger of all verifications, revisions, target edits, and role changes with JSON diff modal. | Immutable append-only audit log table. |

---

## 2. Explicitly Deferred Features (Phase 2 Roadmap)

The following capabilities are acknowledged for future scaling but are strictly excluded from the MVP:

1. **Offline Synchronization & Background Service Workers:**
   * *Reason for Deferral:* Edge-case sync conflicts, IndexedDB complexity, and mobile browser background sync variations. The MVP requires an online cellular connection.
2. **Multi-Factor Authentication (MFA):**
   * *Reason for Deferral:* High initial friction for field officers; standard secure JWT and Argon2 are sufficient for MVP.
3. **Advanced GIS & Multi-Band Satellite Analysis:**
   * *Reason for Deferral:* PostGIS spatial indexing, NDVI spectral analysis, and external satellite APIs introduce unapproved dependencies and heavy computational overhead.
4. **Automated EXIF Image Forensics:**
   * *Reason for Deferral:* Algorithmic metadata tampering detection requires specialized Python image libraries. In the MVP, photos and coordinates are inspected manually by the verifying Project Manager.
5. **What-If Impact Simulator:**
   * *Reason for Deferral:* Predictive modeling sandboxes require empirical regression models that have not yet been calibrated.
6. **Templated PDF Reporting Engine:**
   * *Reason for Deferral:* Server-side headless browser PDF rendering (e.g., Puppeteer/WeasyPrint) introduces substantial operational weight. MVP provides clean CSV exports of raw verified records.

---

## 3. Demonstration Data & Scientific Grounding Standard

* **Demonstration Data Marking:** All seed scripts, fixtures, mock project locations (e.g. "Sundarbans Delta Conservation", "Nilgiri Highlands"), and demo metrics must be explicitly marked as `IS_DEMONSTRATION_FIXTURE = True` in code and documentation.
* **No Speculative Carbon or Biodiversity Multipliers:** VANA will never calculate or present "Estimated Tons of $\text{CO}_2$ Sequestered" or "Biodiversity Index" based on unvalidated standard ratios. Only directly recorded, verified physical interventions (`TREES_PLANTED`, `AREA_RESTORED`, `WATER_CONSERVED`) are computed.
