# VANA — Production Acceptance & Quality Verification Checklist

> **Document Status:** Authoritative Pre-Deployment Release Gate\
> **Platform:** VANA Environmental Operations Platform\
> **Assignment:** Akshaya Vana Climate Ventures Private Limited Full-Stack Technical Submission\
> **Target Environment:** Neon PostgreSQL + Render Web Service + Vercel Edge SPA

---

## 1. Pre-Deployment Verification Gate (Local & CI)

- [x] **Backend Test Suite:** All 164 pytest tests pass with 100% pass rate (`pytest -q`).
- [x] **Audit Ledger Domain Tests:** All 24 dedicated audit tests pass (`test_audit_ledger.py`, `test_audit_api.py`, `test_audit_e2e_acceptance.py`).
- [x] **Frontend Unit & Integration Tests:** All 99 node test runner tests pass across 8 test suites (`npm --prefix frontend test -- --run`).
- [x] **Frontend TypeScript Typecheck:** Clean compilation with 0 errors (`npm --prefix frontend run typecheck`).
- [x] **Frontend Production Build:** Clean build in under 15s with code splitting (`npm --prefix frontend run build`).
- [x] **Chunk Size Optimization:** All JavaScript chunks under 500 kB; vendor bundles extracted for React, Leaflet, Recharts, and TanStack Query.
- [x] **Two-Way Database Migration:** `0003_audit_immutability_ledger` verified clean (`downgrade -1` $\to$ `upgrade head`).
- [x] **Git Cleanliness & Whitespace:** Clean working tree checks with zero trailing whitespace warnings (`git diff --check`).
- [x] **Secret Audit:** Confirmed no passwords, API tokens, `.env` files, or production credentials are committed.

---

## 2. Neon Database Deployment Gate

- [ ] **Neon Project Created:** `vana-production` created on PostgreSQL 17 in target AWS region.
- [ ] **Pooled Connection URL Configured:** `DATABASE_URL` retrieved from Neon console.
- [ ] **Direct Migration URL Configured:** `ALEMBIC_DATABASE_URL` unpooled direct connection string retrieved.
- [ ] **Alembic Schema Upgrade:** Migrations `0001`, `0002`, and `0003` applied cleanly via `alembic upgrade head`.
- [ ] **Tables Verified:** All domain tables (`users`, `projects`, `project_assignments`, `environmental_targets`, `field_activities`, `activity_revisions`, `evidence_files`, `field_inspections`, `maintenance_tasks`, `survival_observations`, `audit_logs`, `audit_chain_head`) created with constraints.
- [ ] **Check Constraints Verified:** `chk_single_head_row`, `chk_active_ledger_verified`, `chk_rejection_reason_required`, `uq_activity_single_active_ledger`.

---

## 3. Render Web Service Deployment Gate

- [ ] **Blueprint Provisioned:** Web service created from `render.yaml`.
- [ ] **Persistent Disk Attached:** 10 GB disk mounted at `/var/data` with directory `/var/data/uploads`.
- [ ] **Pre-Deploy Migration Run:** Render executes `alembic upgrade head` before process start.
- [ ] **Health Endpoint Returns 200:** `GET /health` returns `{"status": "healthy", "database": "connected"}`.
- [ ] **Administrator Bootstrapped:** `python -m app.bootstrap_admin` executed successfully in Render shell.
- [ ] **Bootstrap Password Cleaned:** `BOOTSTRAP_ADMIN_PASSWORD` variable cleared from environment.
- [ ] **CORS Origins Enforced:** Backend only accepts requests from Vercel frontend domain.

---

## 4. Vercel Frontend Deployment Gate

- [ ] **Project Connected:** GitHub repository imported into Vercel.
- [ ] **Environment Variables Configured:** `VITE_BACKEND_URL` and `VITE_API_BASE_URL` pointing to Render service.
- [ ] **Build Succeeded:** Vercel production build completes in under 20 seconds.
- [ ] **SPA Rewrites Active:** Client-side routing functional on `/audit`, `/monitoring`, `/projects`, `/dashboard`.
- [ ] **HTTPS Enforced:** Automatic SSL certificate provisioned.

---

## 5. Live Acceptance Smoke Test Workflow

1. **Root Administrator Login:**
   - Log in at `/login` with `admin@vana.earth`.
   - Verify JWT issuance and redirect to `/dashboard`.
   - Verify green live backend health badge in top navigation header.
2. **Project Portfolio & Environmental Targets:**
   - Create new restoration project (e.g., *Western Ghats Agroforestry Corridor*).
   - Add native tree planting target (e.g., 25,000 trees, unit: `TREES`).
   - Assign a Project Manager to the project.
3. **Field Activity Lifecycle:**
   - Log in as Field Officer.
   - Submit activity: 1,000 native saplings planted with geotagged site photo evidence.
   - Confirm activity is recorded with status `PENDING`.
4. **Rejection & Amendment Cycle:**
   - Log in as Project Manager.
   - Reject activity with code `INSUFFICIENT_EVIDENCE` and note: "Please attach perimeter polygon".
   - Confirm status changes to `REJECTED` and does NOT contribute to official achievements.
   - Log in as Field Officer and submit an amendment revision.
5. **Anti-Self-Verification Gate:**
   - Verify Field Officer is blocked (`HTTP 403 Forbidden`) if attempting to verify their own submission.
6. **Verification & Environmental Ledger Accounting:**
   - Log in as Project Manager and verify the amended revision.
   - Check Organization Dashboard: Official verified count increases by exactly 1,000.
7. **Field Monitoring & Survival Tracking:**
   - Schedule and complete a field inspection with photographic evidence.
   - Record a 94.2% seedling survival observation across sample plots.
   - Verify longitudinal survival curve updates on monitoring workspace without double-counting.
8. **Audit Ledger & Cryptographic Integrity Verification:**
   - Navigate to `/audit` $\to$ **Integrity Console**.
   - Execute chain verification across all recorded events.
   - Confirm banner displays **Cryptographically Valid (Green)** with zero sequence gaps or hash divergences.
