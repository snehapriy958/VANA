# VANA — Production Deployment Guide & Acceptance Blueprint
## Cloud Deployment Architecture for Neon, Render, Vercel & GitHub

> **Platform:** VANA Environmental Operations & Impact Intelligence\
> **Assignment:** Akshaya Vana Climate Ventures Private Limited Full-Stack Technical Submission\
> **Date:** November 4, 2026\
> **Status:** Production Ready & Verified (Pre-Deployment Complete)\
> **Repository:** `https://github.com/snehapriy958/VANA`\
> **Architecture:** Domain-Driven Modular Monolith (FastAPI + React 19 + PostgreSQL 17)

---

## 1. High-Level Architecture Blueprint

```
                     ┌───────────────────────────────────┐
                     │          Vercel Edge              │
                     │    React 19 SPA + Vite + CSS      │
                     │   https://vana-app.vercel.app     │
                     └─────────────────┬─────────────────┘
                                       │ HTTPS (JSON API)
                                       ▼
                     ┌───────────────────────────────────┐
                     │          Render Web               │
                     │  FastAPI + SQLAlchemy 2.0 Async   │
                     │   https://vana-api.onrender.com   │
                     └─────────┬─────────────────┬───────┘
                               │                 │
                  TCP (SSL)    │                 │ Persistent Disk
                  (asyncpg)    ▼                 ▼ (/var/data)
                 ┌───────────────────┐     ┌───────────────────┐
                 │  Neon PostgreSQL  │     │    Render Disk    │
                 │   Serverless PG   │     │     10 GB Ext4    │
                 │  Official Ledger  │     │ Evidence Uploads  │
                 └───────────────────┘     └───────────────────┘
```

---

## 2. Infrastructure Prerequisite Summary

| Service | Component | Purpose | Pricing Tier | Connection Type |
|---|---|---|---|---|
| **Neon** | PostgreSQL 17 | Primary system of record & cryptographic audit ledger | Serverless / Free or Launch | Pooled (App) + Direct (Alembic) |
| **Render** | Web Service | FastAPI Python 3.12 backend modular monolith | Starter / Standard | HTTP/HTTPS + Persistent Disk |
| **Vercel** | Edge Network | React 19 single-page application | Hobby / Pro | Global Edge CDN with SPA rewrites |
| **GitHub** | Code Repository | Version control, release tags, and CI/CD pipelines | Free / Team | Git over HTTPS / SSH |

---

## 3. Phase 1 — Neon PostgreSQL Provisioning

### 3.1 Database Creation
1. Sign in to the [Neon Console](https://console.neon.tech).
2. Create a new project: `vana-production`.
3. Select PostgreSQL version: `17`.
4. Region: Choose the AWS region closest to your Render service (e.g., `us-east-2` Ohio or `us-west-2` Oregon).
5. Obtain the two required connection strings from the Neon Dashboard:
   - **Pooled Connection String** (Used by FastAPI application for high concurrency):
     ```
     postgresql://vana_user:SECRET_PASS@ep-pooler-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```
   - **Direct Unpooled Connection String** (Used strictly by Alembic migrations to support transactional DDL):
     ```
     postgresql://vana_user:SECRET_PASS@ep-direct-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```

### 3.2 URL Normalization & Production Validation
VANA's backend automatically normalizes Neon URLs in `backend/app/core/config.py` and `backend/alembic/env.py`:
- Protocol `postgres://` or `postgresql://` is automatically converted to `postgresql+asyncpg://`.
- Parameter `sslmode=require` is automatically normalized to `ssl=require`.
- In production (`ENVIRONMENT=production`), the application strictly rejects `localhost`, `127.0.0.1`, or sqlite URLs to prevent accidental development data leakage.

---

## 4. Phase 2 — Render Backend Deployment

### 4.1 Deployment Configuration via `render.yaml`
The repository includes a root [render.yaml](file:///C:/Developers/Sneha/Projects/VANA/render.yaml) Blueprint specification. To deploy:
1. In the Render Dashboard, click **New +** $\to$ **Blueprint**.
2. Select your repository: `https://github.com/snehapriy958/VANA`.
3. Render reads `render.yaml` and provisions:
   - **Service Name:** `vana-backend`
   - **Runtime:** Python (`runtime.txt` or Python 3.12.8)
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Pre-Deploy Command:** `alembic upgrade head` (automatically applies database migrations before launching new code)
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
   - **Persistent Disk:** Mounted at `/var/data` (10 GB) for content-addressed photo evidence storage.

### 4.2 Render Environment Variables Matrix

| Variable | Type | Recommended Value | Purpose |
|---|:---:|---|---|
| `ENVIRONMENT` | String | `production` | Enables strict production fail-safes and CORS enforcement |
| `PROJECT_NAME` | String | `VANA Environmental Operations Platform` | OpenAPI / API metadata title |
| `API_V1_STR` | String | `/api/v1` | Versioned REST API route prefix |
| `DATABASE_URL` | Secret | `postgresql+asyncpg://...@...neon.tech/neondb?ssl=require` | Pooled Neon PostgreSQL connection |
| `ALEMBIC_DATABASE_URL` | Secret | `postgresql+asyncpg://...@...neon.tech/neondb?ssl=require` | Direct (unpooled) Neon URL for migrations |
| `JWT_SECRET_KEY` | Secret | *(64-character random hex string)* | HS256 JWT signing secret (auto-generated by Render) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Integer | `60` | Lifespan of short-lived access JWT |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Integer | `7` | Lifespan of rotating refresh token |
| `STORAGE_BACKEND` | String | `local` | Content-addressed storage driver |
| `STORAGE_LOCAL_ROOT` | String | `/var/data/uploads` | Path to persistent disk for evidence storage |
| `CORS_ORIGINS` | JSON Array | `["https://vana-app.vercel.app"]` | Allowed frontend origins (exact URLs, no wildcards) |

### 4.3 Secure Initial Administrator Bootstrap
After the Render web service successfully deploys and Alembic migration `0003_audit_immutability_ledger` executes, provision the initial organization administrator using Render's **One-Off Job** or **Web Shell**:

```bash
# Set temporary bootstrap credentials in Render Environment or execute in shell:
export BOOTSTRAP_ADMIN_EMAIL="admin@vana.earth"
export BOOTSTRAP_ADMIN_NAME="System Administrator"
export BOOTSTRAP_ADMIN_PASSWORD="Secure#Admin#Password#2026!"

# Execute bootstrap CLI
python -m app.bootstrap_admin
```

The CLI tool:
1. Validates password complexity ($\ge 12$ chars, mixed case, numbers, special characters).
2. Hashes credentials using Argon2id.
3. Inserts the `ADMIN` record and emits an immutable `USER_PROVISIONED` audit record into the cryptographic ledger.
4. Refuses to overwrite any existing administrator.
5. Immediately unset `BOOTSTRAP_ADMIN_PASSWORD` in the environment after successful execution.

---

## 5. Phase 3 — Vercel Frontend Deployment

### 5.1 Project Setup
1. In the Vercel Dashboard, click **Add New...** $\to$ **Project**.
2. Select GitHub repository: `snehapriy958/VANA`.
3. Configure Project Settings:
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build` (`tsc -b && vite build`)
   - **Output Directory:** `dist`
   - **Install Command:** `npm install`

### 5.2 Vercel Environment Variables Matrix

| Variable | Value | Purpose |
|---|---|---|
| `VITE_BACKEND_URL` | `https://vana-backend.onrender.com` | Root backend URL for server health checks |
| `VITE_API_BASE_URL` | `https://vana-backend.onrender.com/api/v1` | Full API v1 base URL for domain services |

### 5.3 Client-Side Routing Guarantee
Single Page Application (SPA) routing is handled by `frontend/vercel.json`:
```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```
This guarantees deep links like `/audit`, `/monitoring`, `/projects`, and `/verification` load properly without HTTP 404 errors.

---

## 6. Phase 4 — Post-Deployment Smoke Verification Checklist

After deploying Neon, Render, and Vercel:

1. **System Health Check:**
   - Execute: `curl -I https://vana-backend.onrender.com/health`
   - Assert: `HTTP/1.1 200 OK` with JSON `{"status": "healthy", "database": "connected"}`.
2. **CORS Validation:**
   - Execute an OPTIONS request from the Vercel domain to ensure `Access-Control-Allow-Origin` matches exactly.
3. **Admin Login:**
   - Navigate to `https://vana-app.vercel.app/login`.
   - Log in with bootstrapped `admin@vana.earth` credentials.
   - Confirm immediate redirect to Organization Dashboard with green connection health badge.
4. **Project & Target Creation:**
   - Create a sample agroforestry restoration project.
   - Add a tree planting target (e.g. 10,000 trees).
5. **Field Activity Submission & Photo Evidence:**
   - Provision a Field Officer account.
   - Log in as Field Officer and submit a planting activity with a photo attachment.
   - Verify upload streams successfully and is saved to `/var/data/uploads`.
6. **Anti-Self-Verification Gate:**
   - Verify that the Field Officer cannot approve their own activity (`HTTP 403 Forbidden`).
7. **Manager Verification & Ledger Achievement:**
   - Log in as Project Manager.
   - Approve activity. Confirm official environmental achievement increments on the dashboard.
8. **Cryptographic Chain Verification:**
   - Navigate to `/audit` $\to$ **Integrity Console**.
   - Click **Verify Chain**.
   - Confirm status badge displays **Cryptographically Valid** with green checkmark across all sequences.
