# VANA — Scalability Roadmap & Transition Triggers

This document defines the quantitative scaling triggers, architectural evolution phases, and criteria for migrating from VANA's MVP modular monolith to distributed cloud infrastructure.

---

## 1. Scalability Philosophy: Justified Evolution

VANA adheres to an empirical scalability philosophy:
* **Start Simple:** A cleanly architected modular monolith running on modern hardware can effortlessly handle millions of database records and hundreds of concurrent operations.
* **No Premature Complexity:** Distributed message brokers, microservices, and distributed caches are operational liabilities until real traffic, data volumes, or organizational scale demand them.
* **Preserve Core Invariants:** Across all infrastructure evolution phases, the core programming languages (Python, TypeScript), frontend framework (React 19), backend framework (FastAPI), and relational database (PostgreSQL) remain identical.

---

## 2. Infrastructure Evolution Phases

```
┌────────────────────────────────────────────────────────────────────────┐
│  PHASE 1: MODULAR MONOLITH (MVP)                                       │
│  • Single FastAPI application process                                  │
│  • Local disk evidence storage (/uploads)                              │
│  • Managed Neon PostgreSQL 16 (Connection Pooling)                     │
│  • Vercel Edge Frontend + Render Web Service                           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Trigger: File volume > 50GB, uploads/day > 500
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  PHASE 2: CLOUD STORAGE & WORKER DECOUPLING                            │
│  • Amazon S3 / Cloudflare R2 for photo evidence via IStorageService    │
│  • Redis 7.x + Celery for async background exports and ledger sync     │
│  • Read-Replica for Analytics queries on PostgreSQL                    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Trigger: Concurrent users > 2,000, multi-region
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  PHASE 3: ENTERPRISE CONTAINER ORCHESTRATION & OBSERVABILITY          │
│  • AWS ECS (Fargate) with auto-scaling task definitions                │
│  • AWS RDS Multi-AZ PostgreSQL with read-replicas                      │
│  • OpenTelemetry (OTel) instrumentation + Prometheus + Grafana         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Quantitative Transition Triggers

| Infrastructure Addition | Quantitative Trigger / Operational Threshold | Architectural Motivation |
|---|---|---|
| **Amazon S3 / R2 Object Storage** | Evidence storage $> 50\text{ GB}$ OR $> 500$ uploads/day OR deployment to ephemeral containers. | Local filesystem storage is non-persistent on ephemeral container hosts (e.g., Render restarts). S3 provides durability ($99.999999999\%$). |
| **Redis & Celery** | Bulk CSV/PDF export generation takes $> 3\text{ seconds}$ OR background notification fan-out needed. | Decouples long-running report generation and email alerts from the synchronous HTTP request/response loop. |
| **PostgreSQL Read Replicas** | Database CPU utilization consistently $> 70\%$ due to complex analytical aggregation queries. | Directs heavy read-only analytical queries away from the primary transactional ledger database. |
| **AWS ECS & Application Autoscaling** | Concurrent active field sessions $> 2{,}000$ with CPU/Memory saturation on single instance. | Enables horizontal scaling of stateless FastAPI worker containers behind an Application Load Balancer (ALB). |
| **Prometheus & Grafana** | Multi-region operational footprint requiring SLA tracking and API latency anomaly detection. | Centralized metric scraping, automated alert thresholds, and dashboard monitoring. |

---

## 4. Migration Continuity Guarantee

Every migration is designed to occur with **zero schema breakage and minimal application refactoring**:
* Evidence storage migration simply involves activating the `S3StorageService` implementation of `IStorageService` via environment variables. Relative storage keys in PostgreSQL remain 100% valid.
* Background workers execute existing service domain methods (`analytics.calculate_rollup()`) wrapped in lightweight Celery tasks.
