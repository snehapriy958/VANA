# VANA — Infrastructure Evolution & Deployment Topology

This document details the concrete deployment architectures, containerization models, and transition topologies across VANA's lifecycle.

---

## 1. Phase 1 (MVP) Deployment Topology

```
┌────────────────────────────────────────────────────────────────────────┐
│                              CLIENT TIER                               │
│  Web Browsers (Desktop & Mobile)                                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS (TLS 1.3)
┌───────────────────────────────────▼────────────────────────────────────┐
│                             FRONTEND                                   │
│  Vercel Edge Network (Global CDN)                                      │
│  • React 19 SPA (Static Assets, Brotli Compression)                    │
│  • Client-side routing with fallback to index.html                     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ API Proxy / REST Calls (Bearer JWT)
┌───────────────────────────────────▼────────────────────────────────────┐
│                             BACKEND                                    │
│  Render Web Service (Docker Container)                                 │
│  • Python 3.12+ FastAPI running on Uvicorn                             │
│  • Persistent Disk Mount (/uploads) for Evidence Attachments           │
│  • Local Storage Service Implementation                                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Encrypted PostgreSQL Connection
┌───────────────────────────────────▼────────────────────────────────────┐
│                            DATABASE TIER                               │
│  Neon Serverless PostgreSQL 16                                         │
│  • Built-in PgBouncer connection pooling                               │
│  • Automated point-in-time recovery (PITR)                             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 2 (Decoupled Cloud Workers & Storage) Topology

When storage exceeds local volume capacity or background processing demands async workers:

```
                               ┌─────────────────────────────────────────┐
                               │  Vercel Frontend (React 19 SPA)         │
                               └────────────────────┬────────────────────┘
                                                    │ HTTPS
                               ┌────────────────────▼────────────────────┐
                               │  FastAPI API Gateway Container          │
                               │  (Stateless Web Service)                │
                               └───────┬────────────┬────────────┬───────┘
                                       │            │            │
             ┌─────────────────────────┘            │            └────────────────────────┐
             ▼                                      ▼                                     ▼
┌─────────────────────────┐            ┌─────────────────────────┐           ┌─────────────────────────┐
│  Cloudflare R2 / S3     │            │  Redis 7.x (Broker)     │           │  Neon PostgreSQL 16     │
│  • Content-Addressed    │            │  • Task Queues          │           │  • Transactional Master │
│    Photo Attachments    │            │  • Rate Limit Windows   │           │  • Read-Replica for     │
│  • CDN Edge Delivery    │            └────────────┬────────────┘           │    Heavy Analytics      │
└─────────────────────────┘                         │                        └─────────────────────────┘
                                                    ▼
                                       ┌─────────────────────────┐
                                       │  Celery Worker Process  │
                                       │  • CSV/PDF Exports      │
                                       │  • Notification Dispatch│
                                       └─────────────────────────┘
```

---

## 3. Deployment Configuration & Persistence Strategy

### 3.1 Render Web Service Persistence Rule
* **Local Volume Mount:** In Phase 1 on Render, the backend service must attach a **Persistent Disk** mounted at `/uploads`.
* **Container Lifecycle Safety:** Because ephemeral container restarts wipe standard disk writes, setting `PERSISTENT_VOLUME_PATH=/uploads` guarantees that field activity photos persist across container redeployments.
* **Environment Configuration:**
  ```ini
  ENVIRONMENT=production
  DATABASE_URL=postgresql+asyncpg://user:pass@ep-cool-db.neon.tech/vana
  STORAGE_BACKEND=local
  STORAGE_LOCAL_ROOT=/uploads
  JWT_SECRET_KEY=secure-random-256-bit-key
  CORS_ORIGINS=https://vana.akshayavana.com
  ```

---

## 4. Multi-Stage Dockerfile Blueprint

```dockerfile
# Stage 1: Build & Dependency Resolution
FROM python:3.12-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Minimal Production Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create non-root operational user
RUN useradd -m -u 1001 vanauser && mkdir -p /uploads && chown -R vanauser:vanauser /app /uploads
USER vanauser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
