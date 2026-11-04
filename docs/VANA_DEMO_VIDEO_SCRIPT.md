# VANA — Demo Video Script
## Checkpoint Data Edition (Recovered Database)

**Version:** 1.0
**Target Duration:** 7–8 minutes
**Audience:** Technical evaluators and stakeholders
**Database:** Neon checkpoint `pre-vana-data-recovery`
**Local backend:** `http://127.0.0.1:8001` (via `run_checkpoint_backend.py`)
**Frontend:** `http://localhost:5173`

> **Pre-recording:** Complete `docs/VANA_DEMO_CHECKLIST.md` before pressing record.

---

## Opening Frame (before recording)

- Browser: Chrome, 1920×1080, 100% zoom, bookmark bar hidden
- Tab 1: `http://localhost:5173/login` — ready to type credentials
- Mic level checked; screen recorder running

---

## Scene 1 — Platform Introduction & Dashboard (0:00–0:40)

**Credentials:** `admin@vana.earth` / `SecurePass123!`

**Narration:**
> "VANA is an Environmental Operations and Impact Intelligence Platform built for Akshaya Vana Climate Ventures. It provides end-to-end management of reforestation field operations, from activity submission through multi-tier verification, real-time monitoring, and an immutable audit ledger. Let me show you the platform using real recovered production data."

**On screen:**
1. Type credentials into the login form → click **Sign In**.
2. Dashboard loads — point out the KPI cards:
   - **9 Active Projects** (or current count)
   - **Pending Verifications** badge (Batch 2 — 750 trees)
   - **Total Verified Trees** (from PRJ-KA-001 Batch 1: 2,500)
   - **Activity statistics** panel
3. Briefly show the Recharts analytics section.

**Talking points:**
- "Every number on this dashboard is computed live from verified data only — Rule 7 of our data integrity policy."
- "The pending verification badge tells me there is work awaiting review."

---

## Scene 2 — Role-Based Access Control (0:40–1:15)

**Stay logged in as:** admin@vana.earth (ADMIN)

**Narration:**
> "VANA enforces three user roles: Admin, Project Manager, and Field Officer. Let me show the team management view."

**On screen:**
1. Click **Team** in the sidebar → `UserManagementView`.
2. Show the three recovered users:
   - `admin@vana.earth` — **ADMIN**
   - `pm.rajesh@vana.earth` — **PROJECT_MANAGER**
   - `fo.aarav@vana.earth` — **FIELD_OFFICER**
3. Hover over invite/role controls to show they are ADMIN-only.

**Talking points:**
- "These are the three roles recovered from the production database."
- "Role assignment is an Admin-only action. Project Managers and Field Officers cannot modify team membership."
- "Every endpoint independently enforces these roles — frontend guards are UX only."

---

## Scene 3 — Project Workspace (1:15–2:00)

**Navigate to:** Projects → **PRJ-KA-001 — Kaveri Basin Agroforestry Restoration**

**Narration:**
> "Let me open our primary restoration project — the Kaveri Basin Agroforestry Restoration. This is the main operational project in the recovered dataset."

**On screen:**
1. Click **Projects** in the sidebar.
2. Click **PRJ-KA-001** from the project list.
3. In the Project Workspace:
   - Show **Project Details** tab: location, description, status.
   - Show **Targets** tab: 2 recovered targets (e.g., trees planted target, hectares restored).
   - Show **Assignments** tab: team members assigned to this project.

**Talking points:**
- "Project targets define what we aim to achieve. VANA tracks progress against these targets using only verified, approved data."
- "Assignment scoping means Project Managers and Field Officers only see the projects they are assigned to."

---

## Scene 4 — Field Operations (2:00–2:50)

**Navigate to:** Field Operations (while still scoped to PRJ-KA-001, or via sidebar)

**Narration:**
> "Field Officers submit their planting and restoration activities here. Let me show you the two recovered activity submissions for the Kaveri Basin project."

**On screen:**
1. Navigate to **Field Operations** view, filter to PRJ-KA-001.
2. Show **Batch 1:**
   - **2,500 trees planted** | Status: **VERIFIED** (green badge)
   - Submitted by `fo.aarav@vana.earth`
3. Show **Batch 2:**
   - **750 trees planted** | Status: **PENDING** (amber badge)
   - Awaiting verification
4. Click Batch 1 to open the activity detail — show submission date, metric code, unit.
5. If evidence thumbnails appear blank: *"Evidence file blobs were not part of the data recovery scope — thumbnails degrade gracefully with no application errors."*

**Talking points:**
- "Batch 1 is fully verified — it contributes to official environmental achievements."
- "Batch 2 is pending — it shows in reported quantities but not in official achievements."
- "VANA separates verified, pending, and rejected quantities explicitly."

---

## Scene 5 — Verification Centre & Anti-Self-Verification (2:50–3:50)

**Narration:**
> "The Verification Centre is where Project Managers review and approve or reject field submissions. VANA enforces a critical integrity rule: a user cannot verify their own submission."

**On screen:**
1. Click **Verification** in the sidebar → `VerificationCentreView`.
2. Show Batch 2 (750 trees) in the pending queue.
3. **Anti-self-verification demo:**
   - Log out as admin.
   - Log in as `fo.aarav@vana.earth` / `SecurePass123!` (the submitter of Batch 2).
   - Navigate to Verification Centre.
   - Attempt to approve Batch 2 — the Approve button should be hidden/disabled (UX guard), or if visible, the backend returns **HTTP 403 Forbidden**.
   - *"The backend independently rejects self-verification with a 403 — the UI guard is secondary."*
4. Log out as Aarav. Log in as `pm.rajesh@vana.earth` / `SecurePass123!`.
5. Navigate to Verification Centre → open Batch 2.
6. Click **Approve** → confirm → submission transitions to **VERIFIED**.
7. Optionally navigate back to dashboard — show updated KPI (verified trees now includes Batch 2).

**Talking points:**
- "This rule is enforced at the service layer — `verifier_id != creator_id`. No amount of frontend manipulation can bypass it."
- "The audit ledger records this verification event with the verifier's identity and timestamp."

---

## Scene 6 — Field Monitoring (3:50–4:50)

**Navigate to:** Projects → find the monitoring project (PRJ-E2E-7B7C90, or the project owning the inspection/task/survival records)

**Narration:**
> "VANA's monitoring module tracks the ongoing health of restoration sites after planting. Let me show the monitoring records recovered from the database."

**On screen:**

**Inspections tab:**
1. Open the inspection record — **COMPLETED SURVIVAL_CHECK**.
2. Show fields: health score **4/5**, threat type **PEST_PRESSURE**, inspection notes, PM addendum.
3. *"This inspection was completed with a follow-up addendum from the Project Manager — the full record is preserved."*

**Maintenance Tasks tab:**
4. Show the maintenance task: **FENCING_REPAIR** | Priority: **HIGH** | Status: **TODO**.
5. Show `completion_notes` referencing **REOPENED** lifecycle — the task was reopened after initial review.

**Survival Observations tab:**
6. Show two survival observation records (the correction chain):
   - Original: 225 alive / 20 dead
   - Current active: **230 alive / 15 dead = 93.9% survival rate**
7. *"VANA maintains a correction chain — the superseded observation is preserved for audit purposes. Only the active record contributes to survival rate calculations."*

**Talking points:**
- "Monitoring data is linked to the same project and audit system — every update is logged."
- "The survival rate calculation uses only the active observation record."

---

## Scene 7 — Audit History & Immutability Ledger (4:50–6:00)

**Log in as admin** (or stay as PM — both can access audit)

**Navigate to:** **Audit** in sidebar → `AuditWorkspaceView`

**Narration:**
> "The Audit History module is the cornerstone of VANA's data integrity architecture. Every critical state change — verifications, rejections, amendments, role changes — is recorded in an immutable, cryptographically chained ledger."

**On screen:**

**Events Timeline tab:**
1. Show the timeline — **213 audit events** from the recovered database.
2. Apply a filter (e.g., Event Type = `ACTIVITY_VERIFIED`).
3. Click an event to open the **Event Detail Drawer**.
4. Show: event type, actor, timestamp, project ID, affected entity, SHA-256 hash, previous hash (chain link).
5. *"Each event carries the SHA-256 hash of its canonical JSON envelope, chained to the previous event's hash. Tampering with any record breaks the chain."*

**Entity Change History tab:**
6. Switch to this tab.
7. Search for `activity_revisions` or select an entity.
8. Show the before/after diff for the verification approval.

**Integrity Console tab:**
9. Switch to the **Integrity Console**.
10. Click **Verify Chain** → wait for the verification to complete.
11. Show the **green success banner**: "Chain integrity verified — all 213 events valid."

**Talking points:**
- "The hash formula covers every security-relevant field: actor, action, timestamp, project, entity, and payload."
- "The backfill algorithm is deterministic and restart-safe — re-running it on the same data produces identical hashes."
- "This is Milestone 8 of VANA's implementation roadmap — the final Audit & Immutability Ledger milestone."

---

## Scene 8 — Living Earth Map & Closing (6:00–6:45)

**Navigate to:** **Map** in sidebar → `LivingEarthMapView`

**Narration:**
> "Finally, the Living Earth Map gives a geographic view of all restoration projects."

**On screen:**
1. Show the React Leaflet map with project geo-pins.
2. Click a pin to show the project summary popup.
3. Navigate back to the **Dashboard** for the closing frame.

**Closing narration:**
> "VANA delivers a complete Environmental Operations and Impact Intelligence platform:
> role-based access control with independent backend enforcement,
> a full field operations and verification workflow with anti-self-verification,
> comprehensive monitoring with correction chains,
> and a cryptographically immutable audit ledger.
>
> The backend is built on FastAPI and PostgreSQL. The frontend is React 19 with TypeScript, Vite, and Tailwind CSS. The platform is deployed on Render and Vercel, with Neon PostgreSQL as the database.
>
> Thank you."

---

## Disclosure Statement (Verbal, Scene 4)

> *"Evidence file thumbnails appear blank in this demo. The evidence blob content was not included in the data recovery scope. The application degrades gracefully — no errors are thrown, and all other functionality is unaffected."*

---

## Appendix — Recovered Data Reference

| Item | Value |
|------|-------|
| Admin login | `admin@vana.earth` / `SecurePass123!` |
| PM login | `pm.rajesh@vana.earth` / `SecurePass123!` |
| FO login | `fo.aarav@vana.earth` / `SecurePass123!` |
| Primary demo project | PRJ-KA-001 — Kaveri Basin Agroforestry Restoration |
| Monitoring demo project | PRJ-E2E-7B7C90 |
| Batch 1 | 2,500 trees — VERIFIED |
| Batch 2 | 750 trees — PENDING (verify during Scene 5) |
| Survival rate | 93.9% (230 alive / 15 dead, active observation) |
| Inspection | COMPLETED SURVIVAL_CHECK, health 4/5, PEST_PRESSURE |
| Maintenance task | FENCING_REPAIR, HIGH priority, TODO / REOPENED |
| Audit events | 213 total |
| Local frontend | `http://localhost:5173` |
| Local backend | `http://127.0.0.1:8000` (local vana_dev) |
| Checkpoint backend | `http://127.0.0.1:8001` (Neon, via run_checkpoint_backend.py) |
