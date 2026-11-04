# VANA — 5-Minute Technical Demonstration Video Script & Walkthrough Runbook

> **Target Platform:** VANA Environmental Operations & Impact Intelligence\
> **Submission Target:** Akshaya Vana Climate Ventures Private Limited\
> **Video Target Duration:** 4 minutes 45 seconds ($\le 5$ minutes maximum)\
> **Presenter:** Sneha Priya\
> **Recording Setup:** 1080p 60fps fullscreen capture, system audio muted, clear microphone narration.

---

## 1. Video Production Checklist & Setup

- [ ] Local PostgreSQL database running on port 15432 with clean seeded test data.
- [ ] Backend running: `uvicorn app.main:app --port 8000` (FastAPI).
- [ ] Frontend running: `npm run dev` (`http://localhost:5173`).
- [ ] Browser window: Google Chrome maximized at 1920x1080, zoom 100%, bookmark bar hidden.
- [ ] Browser tabs prepared:
  - Tab 1: VANA Login (`http://localhost:5173/login`)
  - Tab 2: Backend Swagger docs (`http://localhost:8000/docs`)
  - Tab 3: GitHub repository (`https://github.com/snehapriy958/VANA`)

---

## 2. Timed Scene-by-Scene Script & Narration

### Scene 1: Platform Introduction & Problem Statement (0:00 – 0:35)
* **Screen View:** Organization Dashboard at `http://localhost:5173/dashboard` (logged in as Admin).
* **On-Screen Actions:**
  - Mouse moves smoothly across the KPI cards (Verified Net Quantity, Target Completion, Pending Reviews, Active Projects).
  - Hover over the Living Earth map showing project restoration sites.
* **Spoken Narration:**
  > "Hello everyone. Welcome to VANA, an Environmental Operations and Impact Intelligence Platform engineered for Akshaya Vana Climate Ventures.
  >
  > Nature-based carbon and reforestation projects face a fundamental trust crisis: double counting, opaque verification, self-reporting bias, and unverified data presented as official environmental progress.
  >
  > VANA solves this through a domain-driven modular monolith built with FastAPI, React 19, and PostgreSQL 17. The system enforces three immutable architectural invariants:
  > 1. Only verified, active ledger revisions contribute to official environmental achievements.
  > 2. Strict anti-self-verification guarantees that field officers cannot approve their own submissions.
  > 3. An append-only cryptographic immutability ledger chains every critical system mutation using SHA-256."

---

### Scene 2: Role-Based Access Control & Navigation (0:35 – 1:05)
* **Screen View:** Sidebar navigation and Team Directory (`http://localhost:5173/team`).
* **On-Screen Actions:**
  - Point out the active user badge: `ADMIN` with "Global Organization Scope".
  - Click on **Team Directory**, showing the roster of Administrators, Project Managers, and Field Officers.
  - Highlight the activation toggles and role-based permissions.
* **Spoken Narration:**
  > "VANA implements strict three-tier role-based access control:
  > - **Administrators** have organization-wide visibility across all projects and governance controls.
  > - **Project Managers** are strictly isolated to their assigned projects.
  > - **Field Officers** are scoped exclusively to data collection and evidence submissions.
  >
  > Every backend endpoint independently validates JWT tokens and database permissions, ensuring frontend route guards remain purely user-experience conveniences."

---

### Scene 3: Project Portfolio & Environmental Target Catalog (1:05 – 1:45)
* **Screen View:** Project Portfolio (`http://localhost:5173/projects`) $\to$ Project Workspace (`/projects/{id}`).
* **On-Screen Actions:**
  - Click into the *Western Ghats Agroforestry Corridor* project.
  - Display the project geographic coordinates, active targets, and assigned team members.
  - Hover over the Environmental Metric: 25,000 Native Saplings (`TREES`).
* **Spoken Narration:**
  > "In the Project Workspace, projects are bound to environmental targets defined in our standardized metric catalog.
  >
  > VANA enforces strict dimensional unit integrity: metric codes like trees planted, mangrove restoration, or carbon tons can never be cross-aggregated, and conversions operate strictly through predefined conversion coefficients.
  >
  > Here we see our target of 25,000 native saplings, with our team of assigned field officers and project managers."

---

### Scene 4: Field Activity Submission & Secure Evidence (1:45 – 2:30)
* **Screen View:** Switch user or demonstrate Field Operations (`http://localhost:5173/operations`).
* **On-Screen Actions:**
  - Click **Submit Activity**.
  - Fill out form: Select Project, Metric (`Native Saplings`), Quantity (`500`), GPS coordinates, and attach a geotagged site photo.
  - Click **Submit Report**.
  - Show the submitted activity appearing in the queue with badge `PENDING`.
* **Spoken Narration:**
  > "Now let's submit a field activity. The field officer inputs the quantity, date, GPS coordinates, and uploads photographic evidence.
  >
  > Behind the scenes, the file is content-addressed with SHA-256 and stored via our persistent storage abstraction. A new activity revision is created with status PENDING.
  >
  > Notice that our official verified dashboard quantity has NOT changed: unreviewed submissions never inflate official numbers."

---

### Scene 5: Verification Decision, Rejection & Anti-Self-Verification (2:30 – 3:20)
* **Screen View:** Verification Centre (`http://localhost:5173/verification`).
* **On-Screen Actions:**
  - Show the pending activity in the Verification Queue.
  - Demonstrate Anti-Self-Verification: Attempting verification by the creator yields a clear `403 Forbidden` error.
  - Switch to Project Manager: Click **Reject**, choose reason code `INSUFFICIENT_EVIDENCE`, and input review note: 'Please provide high-resolution canopy boundary photograph.'
  - Show activity changing to `REJECTED`.
  - Open the activity revision history: Show the Field Officer's subsequent amendment revision with updated evidence.
  - Click **Approve / Verify**. Show revision transition to `VERIFIED` and `Active Ledger Entry`.
* **Spoken Narration:**
  > "In the Verification Centre, Project Managers review pending submissions alongside evidence photos.
  >
  > Rule 5 is absolute: Anti-Self-Verification prevents any user from verifying their own submission.
  >
  > When rejecting an activity, VANA requires both a standardized reason code and detailed review notes. When the field officer submits an amendment revision, historical rejected submissions remain immutably preserved in the audit log.
  >
  > Upon verification approval, this revision becomes the single active ledger entry, automatically updating the official environmental achievement."

---

### Scene 6: Field Monitoring & Longitudinal Survival Tracking (3:20 – 4:00)
* **Screen View:** Field Monitoring Workspace (`http://localhost:5173/monitoring`).
* **On-Screen Actions:**
  - Navigate to the **Monitoring Workspace**.
  - Show the three operational streams: Inspections, Maintenance Tasks, and Survival Observations.
  - Open a completed survival check: Show sample plot size, live stems, dead stems, and derived 92.5% survival rate.
  - Display the interactive Recharts survival curve tracking longitudinal seedling vitality over time.
* **Spoken Narration:**
  > "Post-planting verification is only half the battle. VANA's Field Monitoring domain tracks ongoing ecosystem health:
  > - Scheduled field inspections verify ground truth with photographic check-ins.
  > - Maintenance tasks manage weed clearing, pest control, and drip irrigation.
  > - Survival observations track sample plot populations over time.
  >
  > Survival rates and monitoring metrics remain completely isolated from official planting ledger tallies, preserving scientific accounting integrity."

---

### Scene 7: Cryptographic Audit History & Integrity Console (4:00 – 4:45)
* **Screen View:** Audit History & Immutability Ledger (`http://localhost:5173/audit`).
* **On-Screen Actions:**
  - Click on **Audit History** in the sidebar.
  - Show the **Audit Overview** tab with total sequence numbers and KPI cards.
  - Click into **Audit Timeline**: Inspect an event to reveal the slide-out **Event Detail Drawer** with `sequence_number`, `current_hash`, `previous_hash`, and raw canonical JSON payload.
  - Click into **Entity Change History**: Show key-by-key dynamic before-and-after state diffs with `MODIFIED` badges.
  - Click into **Integrity Console**: Click **Verify Chain**. Show live execution recalculating SHA-256 digests across all records and rendering the green **Cryptographically Valid** banner.
* **Spoken Narration:**
  > "Finally, let's look at Milestone 8: the Audit History and Immutability Ledger.
  >
  > Every mutation—from login events to verification approvals and target updates—is assigned a gapless sequence number and chained with SHA-256 hashes using canonical JSON serialization.
  >
  > In the Event Inspector, we can view the previous hash linkage and the exact state delta.
  >
  > In the Integrity Console, we can execute on-demand cryptographic verification. The engine recomputes every SHA-256 digest from raw database payloads, checking sequence monotonicity, previous-hash linkage, and state-payload equivalence.
  >
  > The result is a green, 100% verified status, proving complete internal ledger integrity.
  >
  > With 164 passing backend tests and 99 frontend tests, VANA provides an enterprise-ready, mathematically grounded foundation for environmental intelligence. Thank you."

---

## 3. Video Recording Runbook & Technical Parameters

1. **Resolution:** 1920x1080 (16:9 ratio).
2. **Audio:** High-quality vocal capture (clear, noise-cancelled narration).
3. **Pacing:** Calm, confident, technical delivery without filler words.
4. **File Output:** `docs/demo/vana_platform_walkthrough.mp4` (H.264 video, AAC audio, $\le 75$ MB).
5. **YouTube / Google Drive Link:** Unlisted link added to assignment submission email.
