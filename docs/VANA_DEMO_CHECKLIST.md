# VANA — Pre-Recording Demo Checklist

**Purpose:** Complete every item on this checklist before pressing Record.
**Reference:** `docs/VANA_DEMO_VIDEO_SCRIPT.md` for the scene-by-scene runbook.
**Estimated setup time:** 10–15 minutes

---

## A. Infrastructure

- [ ] **PostgreSQL 17 is running on port 15432**
  ```powershell
  # Test: should return "1"
  & 'C:\Program Files\PostgreSQL\17\bin\psql.exe' -h 127.0.0.1 -p 15432 -U postgres -d vana_dev -c "SELECT 1;" -t -q
  ```
  > If not running, see `docs/LOCAL_DEMO_STARTUP.md` → Section 1.

- [ ] **Backend (local vana_dev) is running on port 8000**
  ```powershell
  # Test: should return {"status":"healthy",...}
  curl http://127.0.0.1:8000/health
  ```
  > If not running, see `docs/LOCAL_DEMO_STARTUP.md` → Section 2.

- [ ] **Frontend dev server is running on port 5173**
  ```powershell
  # Test: browser navigates without error
  # Open: http://localhost:5173/login
  ```
  > If not running, see `docs/LOCAL_DEMO_STARTUP.md` → Section 4.

- [ ] **`frontend/.env` points to the correct backend**
  ```
  VITE_BACKEND_URL=http://localhost:8000
  ```
  > Never modify `.env` directly. Use `.env.local` for overrides (see §F below).

---

## B. Browser Configuration

- [ ] Browser: **Google Chrome** (or Chromium)
- [ ] Window: **maximized**, resolution **1920×1080**, zoom **100%**
- [ ] Bookmark bar: **hidden** (`Ctrl+Shift+B` to toggle)
- [ ] Extensions: **all hidden or disabled** (distraction-free)
- [ ] Browser storage cleared:
  ```
  Chrome → Settings → Privacy → Clear browsing data
  → Cookies and site data ✓
  → Cached images and files ✓
  → Time range: All time
  ```
- [ ] Tab 1: `http://localhost:5173/login` — login page ready
- [ ] Tab 2: `http://127.0.0.1:8000/docs` — Swagger UI (reference only)
- [ ] Tab 3: `https://github.com/snehapriy958/VANA` — GitHub repo

---

## C. Demo Credentials (All use the same password)

| Account | Role | Email | Password |
|---------|------|-------|----------|
| Primary (opens dashboard) | ADMIN | `admin@vana.earth` | `SecurePass123!` |
| Verifier | PROJECT_MANAGER | `pm.rajesh@vana.earth` | `SecurePass123!` |
| Submitter | FIELD_OFFICER | `fo.aarav@vana.earth` | `SecurePass123!` |

- [ ] All three credentials confirmed working (test login for each before recording)
- [ ] Credentials printed or visible on second monitor during recording

---

## D. Demo Data Pre-Navigation

- [ ] **PRJ-KA-001 (Kaveri Basin)** — verify it loads in Projects list
  - [ ] 2 targets visible in Targets tab
  - [ ] Batch 1 (2,500 trees, VERIFIED) visible in Field Operations
  - [ ] Batch 2 (750 trees, PENDING) visible in Verification Centre
- [ ] **Monitoring project (PRJ-E2E-7B7C90)** — verify it loads
  - [ ] 1 inspection record visible (COMPLETED SURVIVAL_CHECK)
  - [ ] 1 maintenance task visible (FENCING_REPAIR, TODO)
  - [ ] 2 survival observations visible (93.9% survival rate active)
- [ ] **Audit workspace** — verify 213 events load on the Events Timeline tab
- [ ] **Living Earth Map** — verify at least one project geo-pin is visible

---

## E. Screen Recorder Configuration

- [ ] Screen recorder installed and test recording done (OBS / Loom / Windows Game Bar)
- [ ] Recording area: **full screen** at 1920×1080
- [ ] Video codec: H.264, 1080p, 30 fps
- [ ] **System audio: OFF** (no notification sounds)
- [ ] **Microphone: ON** and level-tested (speak one sentence, play back)
- [ ] Background apps that may send notifications: **closed or silenced**
  - Slack, Teams, Outlook, Discord — set to Do Not Disturb
- [ ] Script: open in a separate window or printed

---

## F. Optional — Checkpoint Backend (Neon `pre-vana-data-recovery`)

> Use only if you want to demonstrate with the Neon checkpoint branch instead of local `vana_dev`.

- [ ] Start checkpoint backend in a separate terminal:
  ```powershell
  cd C:\Developers\Sneha\Projects\VANA\backend
  .\.venv\Scripts\python.exe run_checkpoint_backend.py
  # Paste Neon checkpoint URI when prompted (input is hidden)
  ```
- [ ] Create `frontend/.env.local` (gitignored — overrides `.env`):
  ```
  VITE_BACKEND_URL=http://localhost:8001
  ```
- [ ] Restart the Vite dev server so the override takes effect.
- [ ] Remove `frontend/.env.local` after the demo session.

> ⚠️ Do **not** modify `frontend/.env` for this override.

---

## G. Final Pre-Recording Checks

- [ ] All checklist items above are ✅
- [ ] Do a dry-run walkthrough of the script (at 2× speed, no recording)
- [ ] Confirm evidence thumbnail blank-out disclosure is rehearsed (Scene 4)
- [ ] Confirm anti-self-verification flow is rehearsed (Scene 5)
- [ ] Confirm Integrity Console "Verify Chain" button works and shows green banner
- [ ] Screen recorder is in **Record** mode — not Preview
- [ ] Take a breath. Begin Scene 1.

---

## H. Post-Recording

- [ ] Stop screen recording
- [ ] Export at 1080p
- [ ] Review first 60 seconds for audio clarity
- [ ] Upload to agreed delivery location
- [ ] Remove `frontend/.env.local` if created (§F)
