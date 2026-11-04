# VANA — Demo QA Report

**Generated:** 2026-11-04
**Repository:** `C:\Developers\Sneha\Projects\VANA`
**Branch:** `main` (HEAD: `5e17e4b`)
**Baseline:** `9b13e10`
**Database:** Neon checkpoint branch `pre-vana-data-recovery` (recovered via `migrate_to_neon_checkpoint.py`)
**Local DB:** `vana_dev` on `127.0.0.1:15432`

---

## 1. Test Suite Results

### 1.1 Backend — pytest

| Metric | Result |
|--------|--------|
| **Total tests** | 172 |
| **Passed** | 172 ✅ |
| **Failed** | 0 |
| **Errors** | 0 |
| **Warnings** | 0 |
| **Duration** | 71.10 s |
| **Exit code** | 0 |

**Command:**
```powershell
cd backend
.\.venv\Scripts\pytest.exe -q
```

**Coverage areas confirmed passing:**
- Authentication (login, JWT issuance, token refresh, `me` endpoint)
- RBAC enforcement (ADMIN, PROJECT_MANAGER, FIELD_OFFICER role guards)
- Project CRUD and assignment
- Field activity submission and retrieval
- Activity revision state machine (PENDING → VERIFIED / REJECTED)
- Anti-self-verification constraint (`verifier_id != creator_id`, HTTP 403)
- Activity amendment and archival workflows
- Field inspections, maintenance tasks, survival observations (monitoring domain)
- Evidence file upload, download, checksum validation, MIME/extension enforcement
- PostgreSQL-backed evidence blob storage adapter
- Audit event emission for all operational events
- Audit hash chain integrity (SHA-256 canonical JSON envelope)
- Audit backfill determinism and restart-safety
- Project-ID propagation on all audit events (Finding 8.1-01 remediation)
- Dashboard analytics aggregations (verified-only achievements, Rule 7)
- Alembic migration `0001` → `0004` upgrade/downgrade cycle
- Model constraints (NOT NULL, FK integrity, unique indexes)

### 1.2 Frontend — Vitest

| Metric | Result |
|--------|--------|
| **Total tests** | 99 |
| **Passed** | 99 ✅ |
| **Failed** | 0 |
| **Errors** | 0 |
| **Duration** | ~281 ms |
| **Exit code** | 0 |

**Command:**
```powershell
npm --prefix frontend test -- --run
```

### 1.3 TypeScript Type Check

| Check | Result |
|-------|--------|
| **TypeScript errors** | 0 ✅ |
| **Command** | `npm --prefix frontend run typecheck` |

### 1.4 Production Build

| Metric | Result |
|--------|--------|
| **Build status** | ✅ Success |
| **Duration** | 13.37 s |
| **Warnings** | 0 |
| **Largest chunk** | `vendor-charts-DjCu_fYX.js` — 426 kB raw / 121 kB gzip |
| **Second largest** | `index-C2eSf6Do.js` — 371 kB raw |
| **Chunk size limit** | 600 kB (all chunks within limit) |

**Command:**
```powershell
npm --prefix frontend run build
```

---

## 2. Authentication Verification

All three recovered user accounts were confirmed functional against the local `vana_dev` database.

| Email | Role | UUID (prefix) | Password | Status |
|-------|------|---------------|----------|--------|
| `admin@vana.earth` | ADMIN | `0f1299ac-…` | `SecurePass123!` | ✅ Verified |
| `pm.rajesh@vana.earth` | PROJECT_MANAGER | — | `SecurePass123!` | ✅ Verified |
| `fo.aarav@vana.earth` | FIELD_OFFICER | — | `SecurePass123!` | ✅ Verified |

---

## 3. RBAC Matrix Verification

| Capability | ADMIN | PROJECT_MANAGER | FIELD_OFFICER |
|-----------|-------|-----------------|---------------|
| View all projects | ✅ | ✅ (assigned only) | ✅ (assigned only) |
| Create / edit project | ✅ | ❌ | ❌ |
| Manage team (invite, role assign) | ✅ | ❌ | ❌ |
| Submit field activity | ✅ | ✅ | ✅ |
| Verify own submission | ❌ 403 | ❌ 403 | ❌ 403 |
| Verify others' submissions | ✅ | ✅ | ❌ |
| View audit ledger | ✅ | ✅ | ❌ |
| Trigger chain integrity check | ✅ | ✅ | ❌ |
| View monitoring records | ✅ | ✅ | ✅ |
| Submit inspections / tasks | ✅ | ✅ | ✅ |

**Anti-self-verification enforcement:** Confirmed at backend service level (`verifier_id != creator_id`). Frontend hides the "Approve" button when the reviewer is the submitter (UX guard only — backend enforces independently).

---

## 4. Recovered Database State

| Entity | Count | Notes |
|--------|-------|-------|
| `users` | 3 | admin, pm, fo |
| `projects` | 9 | 1 primary (PRJ-KA-001) + 8 E2E test artifacts |
| `project_targets` | 15 | |
| `project_assignments` | 14 | |
| `field_activities` | 18 | |
| `activity_revisions` | 22 | Verified + pending |
| `field_inspections` | 1 | COMPLETED SURVIVAL_CHECK, health 4/5 |
| `maintenance_tasks` | 1 | TODO / HIGH priority / FENCING_REPAIR |
| `survival_observations` | 2 | Correction chain: 93.9% survival rate |
| `evidence_files` | 4 | Metadata only — blobs not recovered |
| `evidence_blobs` | 0 | See Known Limitations §5 |
| `audit_logs` | 213 | Full chain, integrity verified |
| `audit_chain_head` | 1 | |

---

## 5. Known Functional Limitations

### 5.1 Evidence Blob Absence (Low severity for demo)

- **Description:** 4 `evidence_files` metadata records exist, all sharing one `file_storage_key`. The corresponding `evidence_blobs` rows were not recovered. `sha256_checksum` is `NULL` for all 4 records.
- **User-visible effect:** Evidence image thumbnails display as blank/broken images. The `onError` handler silently hides the `<img>` element — no crash, no error modal.
- **Download attempt:** Returns HTTP 404 from `EvidenceService.get_evidence_content`.
- **Disclosure:** Verbally acknowledge during demo ("Evidence file blobs were not part of the data recovery scope").

### 5.2 Synthetic Inspection Evidence Button

- **Location:** `frontend/src/views/monitoring/components/InspectionsTab.tsx` lines 1079–1088
- **Description:** "View Attached Media" for inspections passes the inspection ID as evidence ID. This will 404 since there is no evidence file with that ID. The lightbox modal opens with metadata only.
- **User-visible effect:** Media lightbox opens but shows an empty/loading state. No crash.

### 5.3 E2E Test Project Naming

- **Description:** 8 of 9 projects are named "Nilgiri Biosphere Restoration Basin" (E2E test artifacts). The project dropdowns display `name (code)` for disambiguation.
- **Demo mitigation:** Focus on PRJ-KA-001 (operations/verification) and PRJ-E2E-7B7C90 (monitoring).

---

## 6. Final QA Verdict

```
DEMO READY WITH KNOWN LIMITATIONS

Backend:   172/172 tests ✅  |  Exit code 0
Frontend:   99/99 tests ✅  |  Exit code 0
TypeScript: 0 errors ✅
Build:      Clean, 0 warnings ✅  |  All chunks < 600 kB

Limitations:
  1. Evidence file blob content not recovered → blank thumbnails (silent degradation)
  2. Synthetic inspection evidence button → lightbox opens empty (no crash)
  3. 8 of 9 projects are E2E test artifacts → disambiguated by project code

All core workflows — authentication, RBAC, project lifecycle, field operations,
verification workflow, monitoring, audit ledger, and analytics — are fully
operational with the recovered database records.
```
