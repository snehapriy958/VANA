# VANA — Local Demo Environment Startup Guide

**Purpose:** Exact PowerShell commands to launch the full VANA demo environment locally.
**OS:** Windows
**Repository:** `C:\Developers\Sneha\Projects\VANA`

---

## Prerequisites

| Component | Required version | Check command |
|-----------|-----------------|---------------|
| PostgreSQL | 17.x | `& 'C:\Program Files\PostgreSQL\17\bin\psql.exe' --version` |
| Python | 3.12+ | `python --version` |
| Node.js | 18+ | `node --version` |
| pnpm / npm | any | `npm --version` |

---

## 1. Start PostgreSQL 17 (local development database)

> Run this in **Terminal 1**. The database persists between sessions — if already running, skip this step.

```powershell
# Check if PostgreSQL is already listening on 15432
netstat -ano | findstr ":15432"
# If a PID is listed → already running, skip to Section 2.

# Start PostgreSQL (daemon — runs in background)
& 'C:\Program Files\PostgreSQL\17\bin\postgres.exe' `
    -D "$env:TEMP\vana_pgdata" `
    -p 15432 `
    -h 127.0.0.1
```

> **Note:** `$env:TEMP\vana_pgdata` is the data directory initialized during project setup. If the directory does not exist, re-run the database initialization steps from the project setup guide.

**Health check:**
```powershell
& 'C:\Program Files\PostgreSQL\17\bin\psql.exe' `
    -h 127.0.0.1 -p 15432 -U postgres -d vana_dev `
    -c "SELECT current_database(), version();" -q
```

---

## 2. Start the Backend (local `vana_dev` database)

> Run this in **Terminal 2**. Backend listens on `http://127.0.0.1:8000`.

```powershell
cd C:\Developers\Sneha\Projects\VANA\backend
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Health check:**
```powershell
# In a new terminal:
curl http://127.0.0.1:8000/health
# Expected: {"status":"healthy","database":"connected",...}
```

**Swagger UI:** `http://127.0.0.1:8000/docs`

---

## 3. (Optional) Start the Checkpoint Backend (Neon `pre-vana-data-recovery`)

> Use this **only** when demonstrating with the recovered Neon database.
> Run this in **Terminal 3**. Checkpoint backend listens on `http://127.0.0.1:8001`.

```powershell
cd C:\Developers\Sneha\Projects\VANA\backend
.\.venv\Scripts\python.exe run_checkpoint_backend.py
```

When prompted:
```
Enter Neon checkpoint connection URI:
```
Paste the Neon URI for branch `pre-vana-data-recovery`. Input is hidden — it will not appear on screen or be saved anywhere.

**URI format expected:**
```
postgresql://[user]:[password]@[host].neon.tech/neondb?sslmode=require
```

**Health check:**
```powershell
curl http://127.0.0.1:8001/health
```

---

## 4. Start the Frontend

> Run this in **Terminal 4**. Frontend listens on `http://localhost:5173`.

```powershell
cd C:\Developers\Sneha\Projects\VANA
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

The terminal will print:
```
  VITE v5.x.x  ready in xxx ms
  ➜  Local:   http://127.0.0.1:5173/
```

**Open in browser:** `http://localhost:5173/login`

---

## 5. Pointing the Frontend to the Checkpoint Backend (Port 8001)

> **Never modify `frontend/.env` directly.**
> Instead, create a local override file that Vite picks up automatically and that is already gitignored.

```powershell
# Create the override (run from project root)
Set-Content -Path frontend\.env.local -Value "VITE_BACKEND_URL=http://localhost:8001"
```

Then **restart the Vite dev server** (Ctrl+C → re-run Section 4).

**To revert to the local backend:**
```powershell
Remove-Item frontend\.env.local
# Restart Vite dev server
```

> `frontend/.env.local` is listed in `.gitignore` — it will never be committed.

---

## 6. Run the Full Test Suite (optional, pre-demo verification)

```powershell
# Backend tests (from project root)
cd C:\Developers\Sneha\Projects\VANA\backend
.\.venv\Scripts\pytest.exe -q
# Expected: 172 passed

# Frontend tests (from project root)
cd C:\Developers\Sneha\Projects\VANA
npm --prefix frontend test -- --run
# Expected: 99 passed

# Frontend typecheck
npm --prefix frontend run typecheck
# Expected: no errors
```

---

## 7. Quick Reference — All Services

| Service | URL | Terminal | Notes |
|---------|-----|----------|-------|
| PostgreSQL | `127.0.0.1:15432` | 1 | daemon, persists |
| Backend (local DB) | `http://127.0.0.1:8000` | 2 | `uvicorn --reload` |
| Checkpoint Backend (Neon) | `http://127.0.0.1:8001` | 3 | optional |
| Frontend | `http://localhost:5173` | 4 | Vite HMR |
| Swagger UI | `http://127.0.0.1:8000/docs` | — | local backend |

---

## 8. Demo Credentials

| Email | Role | Password |
|-------|------|----------|
| `admin@vana.earth` | ADMIN | `SecurePass123!` |
| `pm.rajesh@vana.earth` | PROJECT_MANAGER | `SecurePass123!` |
| `fo.aarav@vana.earth` | FIELD_OFFICER | `SecurePass123!` |

---

## 9. Stopping Everything

```powershell
# Frontend — Ctrl+C in Terminal 4
# Checkpoint backend — Ctrl+C in Terminal 3
# Backend — Ctrl+C in Terminal 2
# PostgreSQL — Ctrl+C in Terminal 1 (or leave running for next session)
```

> PostgreSQL can be left running between sessions — it uses minimal resources at idle.

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Connection refused` on port 8000 | Uvicorn not running | Restart Section 2 |
| `Connection refused` on port 5173 | Vite not running | Restart Section 4 |
| Login returns 401 | Wrong backend URL in `.env` / `.env.local` | Check `VITE_BACKEND_URL` |
| Dashboard shows no data | Frontend pointing to wrong backend | Check `.env.local` |
| `psql: error: connection to server failed` | PostgreSQL not running | Restart Section 1 |
| Checkpoint URI rejected | Wrong scheme, host, or database path | URI must be `postgresql://...neon.tech/neondb` |
| Evidence thumbnails blank | Blobs not recovered — expected | Acknowledge in demo (Scene 4) |
| Alembic errors on startup | Migration not applied | Run `alembic upgrade head` from `backend/` |
