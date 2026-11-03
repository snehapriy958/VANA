# VANA — Performance Strategy & Optimization

This document outlines the performance benchmarks, database indexing strategies, frontend bundle optimizations, and caching mechanisms engineered into VANA.

---

## 1. Performance Targets & SLA Benchmarks

| Metric / Scenario | Performance SLA | Measurement Method |
|---|:---:|---|
| **API Response Time (CRUD)** | $\le 100\text{ms}$ (p95) | FastAPI middleware timer |
| **Verification & Recalculation Loop** | $\le 250\text{ms}$ (p95) | Transaction duration from POST to committed aggregate |
| **Dashboard Portfolio Load** | $\le 500\text{ms}$ (p95) | End-to-end response on 10,000 recorded activities |
| **Living Earth Map Initial Pin Render** | $\le 300\text{ms}$ | Client-side Leaflet marker initialization |
| **Mobile Form TTI (Time-to-Interactive)**| $\le 1.2\text{s}$ | Google Lighthouse mobile audit on 4G cellular simulation |

---

## 2. Database Indexing & Query Optimization

### 2.1 Strategic Composite Indexes
To ensure sub-10ms ledger aggregations, PostgreSQL utilizes specialized composite indexes:
1. **Active Ledger Index:**
   ```sql
   CREATE INDEX idx_revisions_active_ledger_math 
   ON activity_revisions(activity_id, is_active_ledger_entry) 
   WHERE is_active_ledger_entry = TRUE;
   ```
   *Enables instant filtering of active records without scanning archived or rejected revisions.*
2. **Project Target Lookup Index:**
   ```sql
   CREATE INDEX idx_targets_project_metric 
   ON project_targets(project_id, metric_code);
   ```
3. **Pending Verification Triage Index:**
   ```sql
   CREATE INDEX idx_revisions_triage_queue 
   ON activity_revisions(status, created_at ASC) 
   WHERE status = 'PENDING';
   ```

### 2.2 Eliminating N+1 Query Antipatterns
SQLAlchemy queries must use explicit eager loading (`selectinload` or `joinedload`) to prevent sequential query waterfalls:
```python
# Optimal Query Pattern
stmt = (
    select(FieldActivity)
    .where(FieldActivity.project_id == project_id)
    .options(
        selectinload(FieldActivity.revisions),
        selectinload(FieldActivity.evidence_files)
    )
)
```

---

## 3. Frontend Bundle & Asset Optimization

1. **Route-Level Code Splitting:**
   * All 10 major screen components are loaded lazily via `React.lazy()` and `Suspense`:
     ```typescript
     const LivingEarthMap = React.lazy(() => import('@/pages/LivingEarthMap'));
     const VerificationCentre = React.lazy(() => import('@/pages/VerificationCentre'));
     ```
   * Initial bundle payload is restricted to $< 180\text{ KB}$ (gzipped).
2. **Map Canvas & Marker Clustering:**
   * Rather than rendering thousands of distinct DOM nodes on the Leaflet canvas, activity pins utilize `leaflet.markercluster` to aggregate proximate pins dynamically at low zoom levels.
3. **TanStack Query Caching Policies:**
   * **Project Metadata:** `staleTime: 5 * 60 * 1000` (5 minutes).
   * **Verification Queue:** `staleTime: 15 * 1000` (15 seconds, with automatic refetch on window focus).
   * **Organization Rollups:** `staleTime: 60 * 1000` (1 minute).

---

## 4. Connection Pooling with Neon PgBouncer

Because serverless and containerized backend workers can rapidly exhaust database connections:
* Backend utilizes connection pooling configured for Neon's built-in **PgBouncer** pooler.
* Connection pool parameters:
  * `pool_size = 20`
  * `max_overflow = 10`
  * `pool_recycle = 1800` (Recycles connections every 30 minutes to prevent stale socket leaks).
