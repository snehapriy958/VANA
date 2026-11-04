# VANA — Production Environment Variables Reference

> **Document Status:** Authoritative Pre-Deployment Specification\
> **Platform:** VANA Environmental Operations Platform\
> **Security Notice:** NEVER commit actual credentials, database passwords, or JWT secrets to version control. This document defines the exact variables required by Neon, Render, and Vercel environments.

---

## 1. Backend Environment Variables (Render Web Service)

These variables must be configured in Render Dashboard under **Environment Variables**:

| Variable Name | Required | Default / Example Value | Description & Constraints |
|---|:---:|---|---|
| `ENVIRONMENT` | **YES** | `production` | Set to `production` for live deployments. Activates strict security guards (disallows localhost DBs, requires CORS). |
| `PROJECT_NAME` | No | `VANA Environmental Operations Platform` | Human-readable service name for OpenAPI docs and health check. |
| `API_V1_STR` | No | `/api/v1` | URL prefix for REST routes. |
| `DATABASE_URL` | **YES** | `postgresql+asyncpg://user:pass@ep-pooler.neon.tech/neondb?ssl=require` | Pooled connection string to Neon PostgreSQL database for application transactions. |
| `ALEMBIC_DATABASE_URL` | **YES** | `postgresql+asyncpg://user:pass@ep-direct.neon.tech/neondb?ssl=require` | Direct (unpooled) Neon PostgreSQL connection string used by Alembic migrations to support transactional DDL. |
| `JWT_SECRET_KEY` | **YES** | *(64-character random hex string)* | HS256 encryption secret key used to sign access and refresh tokens. Must be $\ge 32$ characters. |
| `JWT_ALGORITHM` | No | `HS256` | Cryptographic algorithm for JWT signatures. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Lifespan of short-lived JWT access tokens in minutes. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Lifespan of refresh tokens in days. |
| `STORAGE_BACKEND` | No | `local` | Storage driver implementation (`local`). |
| `STORAGE_LOCAL_ROOT` | **YES** | `/var/data/uploads` | Local filesystem path on Render Persistent Disk for evidence photos. |
| `CORS_ORIGINS` | **YES** | `["https://vana-app.vercel.app"]` | JSON-encoded array of allowed frontend origin URLs. Wildcards and `*` are forbidden when credentials are enabled. |

---

## 2. Administrator Bootstrap Environment Variables (One-Time Execution)

These variables are supplied temporarily to the Render Web Shell or One-Off Job to provision the root administrator:

| Variable Name | Required | Example Value | Description & Constraints |
|---|:---:|---|---|
| `BOOTSTRAP_ADMIN_EMAIL` | **YES** | `admin@vana.earth` | Email address of the initial administrator account. |
| `BOOTSTRAP_ADMIN_NAME` | No | `System Administrator` | Full name of the administrator. Defaults to `System Administrator`. |
| `BOOTSTRAP_ADMIN_PASSWORD` | **YES** | `Your#Secure#Bootstrap#Password#2026!` | Password satisfying complexity: $\ge 12$ chars, uppercase, lowercase, digit, special character. |

> [!IMPORTANT]
> Unset or delete `BOOTSTRAP_ADMIN_PASSWORD` immediately after running `python -m app.bootstrap_admin` to prevent credential exposure.

---

## 3. Frontend Environment Variables (Vercel Project Settings)

These variables must be configured in Vercel Dashboard under **Project Settings $\to$ Environment Variables**:

| Variable Name | Required | Example Production Value | Description |
|---|:---:|---|---|
| `VITE_BACKEND_URL` | **YES** | `https://vana-backend.onrender.com` | Base origin of the Render web service without trailing slash. Used for root `/health` checks. |
| `VITE_API_BASE_URL` | **YES** | `https://vana-backend.onrender.com/api/v1` | Full API v1 base path. Used by Axios client to execute REST requests. |

---

## 4. Local Development Variables (Reference)

For local development in `backend/.env` and `frontend/.env`:

### `backend/.env`:
```bash
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:15432/vana_dev
TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:15432/vana_test
JWT_SECRET_KEY=dev-secret-key-must-be-changed-in-production-at-least-32-chars
STORAGE_LOCAL_ROOT=uploads
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://127.0.0.1:3000","http://127.0.0.1:5173"]
```

### `frontend/.env`:
```bash
VITE_BACKEND_URL=http://localhost:8000
VITE_API_BASE_URL=http://localhost:8000/api/v1
```
