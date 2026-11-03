# VANA — System Architecture Specification

This document details the engineering architecture, internal domain boundaries, data pipelines, and service contracts for VANA.

---

## 1. Architectural Style: Domain-Driven Modular Monolith

VANA is architected as a **Domain-Driven Modular Monolith**. This pattern combines the operational simplicity and transactional guarantees of a monolith with the clean boundaries and modular independence required for future microservice extraction.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND CLIENT (SPA)                           │
│              React 19 • TypeScript • Vite • Tailwind CSS               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS / REST API / Bearer JWT
┌───────────────────────────────────▼────────────────────────────────────┐
│                    VANA BACKEND (FastAPI Monolith)                     │
│  app/                                                                  │
│  ├── core/                 # Config, DB Session, Security, Storage     │
│  │   ├── security.py       # JWT creation/decoding, Argon2 pwd hash    │
│  │   ├── database.py       # SQLAlchemy 2.x async session factory      │
│  │   └── storage.py        # IStorageService abstraction interface     │
│  │                                                                     │
│  ├── domains/              # Bounded Business Domains                  │
│  │   ├── auth/             # User auth, credentials, session tokens    │
│  │   ├── projects/         # Project portfolio, metadata, targets      │
│  │   ├── teams/            # User roster, project allocations          │
│  │   ├── operations/       # Field activity reporting & revisions      │
│  │   ├── verification/     # Triage queue, review decisions, anti-gate │
│  │   ├── analytics/        # Verified environmental ledger calculation │
│  │   └── audit/            # Append-only system mutation ledger        │
│  │                                                                     │
│  └── api/v1/router.py      # Aggregated API route definitions          │
├────────────────────────────────────────────────────────────────────────┤
│  Persistence & Drivers                                                 │
│  ├── SQLAlchemy 2.x Async ORM                                          │
│  ├── PostgreSQL 16 (Neon / Local Docker)                               │
│  └── Local File Storage Mount (/uploads)                               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Codebase Organization & Directory Layout

```
c:\Developers\Sneha\Projects\VANA/
├── frontend/                        # React 19 Client SPA
│   ├── src/
│   │   ├── assets/                  # Brand SVG icons, logos
│   │   ├── components/              # shadcn/ui & domain components
│   │   │   ├── ui/                  # Atomic primitives (button, input, badge)
│   │   │   ├── layout/              # Shell, Sidebar, Header, MobileNav
│   │   │   ├── map/                 # React Leaflet canvas, pins, drawer
│   │   │   └── verification/        # Queue list, evidence lightbox
│   │   ├── context/                 # AuthContext, NotificationContext
│   │   ├── hooks/                   # useAuth, useProject, useVerification
│   │   ├── lib/                     # Axios instance, formatting utils
│   │   ├── pages/                   # 10 core screen page components
│   │   ├── types/                   # TypeScript interfaces, Zod schemas
│   │   ├── App.tsx                  # Root component & Route definitions
│   │   └── main.tsx                 # Vite entry point
│   ├── package.json
│   ├── tailwind.config.js           # VANA color tokens and typography
│   └── vite.config.ts
│
├── backend/                         # FastAPI Python Application Layer
│   ├── app/
│   │   ├── core/                    # Core infrastructure & configuration
│   │   │   ├── config.py            # Pydantic BaseSettings (env vars)
│   │   │   ├── database.py          # SQLAlchemy 2.x async engine & session
│   │   │   ├── security.py          # JWT, Argon2 hashing utilities
│   │   │   └── storage.py           # IStorageService & LocalStorageService
│   │   ├── domains/                 # Bounded Domain Packages
│   │   │   ├── auth/                # models, schemas, service, router
│   │   │   ├── projects/            # models, schemas, service, router
│   │   │   ├── teams/               # models, schemas, service, router
│   │   │   ├── operations/          # models, schemas, service, router
│   │   │   ├── verification/        # models, schemas, service, router
│   │   │   ├── analytics/           # models, schemas, service, router
│   │   │   └── audit/               # models, schemas, service, router
│   │   ├── main.py                  # FastAPI application factory
│   │   └── api/v1/router.py         # Versioned API router mount
│   ├── alembic/                     # Database migration environment
│   │   ├── versions/                # Versioned migration scripts
│   │   └── env.py                   # Migration runner
│   ├── tests/                       # Automated test suite
│   │   ├── conftest.py              # Pytest fixtures, test DB, auth tokens
│   │   ├── unit/                    # Math, unit conversion, domain logic
│   │   └── integration/             # API routes, verification state machine
│   ├── requirements.txt             # Locked Python dependencies
│   ├── Dockerfile
│   └── alembic.ini
│
├── docs/                            # Comprehensive System Documentation
└── AGENTS.md                        # Permanent Engineering Rules
```

---

## 3. Bounded Domain Responsibilities & Service Contracts

Each domain in `backend/app/domains/` encapsulates its own models, Pydantic schemas, and service layer. Domains communicate with each other exclusively through documented service interfaces rather than directly mutating another domain's database models.

| Domain Package | Key Responsibilities | Consumed By Other Domains |
|---|---|---|
| **`auth`** | User credentials, password hashing, JWT issue/refresh, role validation. | Provides `get_current_user` and `require_role` FastAPI dependencies. |
| **`projects`** | Project metadata, status transitions, center coordinates, boundary polygons, dimensional targets. | Used by `operations` (validating assigned projects) and `analytics` (target baselines). |
| **`teams`** | Project-to-user assignments, role allocation within projects. | Used by `auth` and `verification` to verify project assignment access. |
| **`operations`** | Field activity submission, revision creation, photo upload, coordinate validation. | Consumed by `verification` for triage queue and scrutiny. |
| **`verification`** | Triage queue filtering, approval/rejection state machine, anti-self-verification gate. | Invokes `analytics.recalculate_project_ledger()` on state transition; appends to `audit`. |
| **`analytics`** | Transactional ledger computation, unit conversion, verified rollups, dimensional caching. | Consumed by `projects` (workspace balance sheet) and Organization Dashboard. |
| **`audit`** | Append-only system change log capturing actor, timestamp, entity, and JSON state diff. | Invoked by all mutating domain services. |

---

## 4. Ingestion, Verification & Ledger Recalculation Flow

The sequence diagram below illustrates the exact transactional execution path from a field officer submitting a report to the official environmental ledger being recalculated upon verification:

```
FieldOfficer           Backend (API)          VerificationService    LedgerService          PostgreSQL
     │                       │                        │                    │                    │
     │── 1. POST /activity ─►│                        │                    │                    │
     │   (qty, metric, coords│── 2. Validate input ──►│                    │                    │
     │    & photo upload)    │── 3. Store photo ─────►│                    │                    │
     │                       │── 4. Insert Activity & Rev 1 (PENDING) ─────────────────────────►│
     │◄── HTTP 201 Created ──│                        │                    │                    │
     │                       │                        │                    │                    │
     │                 ProjectManager                 │                    │                    │
     │                       │                        │                    │                    │
     │                       │── 5. POST /verify ────►│                    │                    │
     │                       │   (decision=APPROVED)  │                    │                    │
     │                       │                        │── 6. Check gate ──►│                    │
     │                       │                        │   (verifier !=     │                    │
     │                       │                        │    creator)        │                    │
     │                       │                        │── 7. Set APPROVED ─────────────────────►│
     │                       │                        │── 8. Recalculate ─►│                    │
     │                       │                        │                    │── 9. Run SQL sum ─►│
     │                       │                        │                    │   for active revs  │
     │                       │                        │                    │◄── 600 Trees ──────│
     │                       │                        │                    │── 10. Update ─────►│
     │                       │                        │                    │   verified_qty     │
     │                       │                        │── 11. Write Audit Log ─────────────────►│
     │                       │◄── HTTP 200 OK ────────│                    │                    │
```
