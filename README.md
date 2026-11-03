# VANA — Environmental Operations & Impact Intelligence Platform

[![Platform](https://img.shields.io/badge/Platform-VANA-183D32.svg)](https://github.com/akshayavana/vana)
[![Architecture](https://img.shields.io/badge/Architecture-Modular%20Monolith-A8B99B.svg)](docs/engineering/01_SYSTEM_ARCHITECTURE.md)
[![Status](https://img.shields.io/badge/Status-Design%20%26%20Documentation-D6A76A.svg)](IMPLEMENTATION_STATUS.md)

**VANA** is an enterprise-grade Environmental Operations and Impact Intelligence Platform engineered for **Akshaya Vana Climate Ventures**. The platform provides centralized command, rigorous field activity verification, geospatial tracking, and verifiable environmental impact accounting across diverse geographical conservation and ecological restoration projects.

---

## 1. Product Vision & The Golden Thread

Environmental initiatives often suffer from verification gaps, inconsistent unit reporting, and lack of ground-truth traceability. VANA bridges the gap between field actions and official environmental claims through a continuous operational loop:

$$\textbf{PLAN} \longrightarrow \textbf{ASSIGN} \longrightarrow \textbf{EXECUTE} \longrightarrow \textbf{RECORD} \longrightarrow \textbf{VERIFY} \longrightarrow \textbf{MEASURE} \longrightarrow \textbf{MONITOR}$$

### Core Operating Tenet: The Verified Ledger
* **Only verified activities contribute to official environmental achievements.**
* Pending and rejected submissions remain distinct and traceable.
* Incompatible measurement units and disparate metric definitions are strictly isolated to prevent mathematical contamination.
* All data points are grounded in documented physical methodologies; no speculative carbon, biodiversity, or survival-rate multipliers are manufactured.

---

## 2. Platform Architecture

VANA is architected as a **Domain-Driven Modular Monolith**, ensuring rapid initial delivery, robust consistency, and clean domain boundaries for future scalability.

```
c:\Developers\Sneha\Projects\VANA/
├── docs/
│   ├── design/            # Brand identity, design system, wireframes, screen specs
│   ├── engineering/       # Architecture, database schema, APIs, security, testing
│   └── scalability/       # Long-term scalability, infrastructure evolution, performance
├── frontend/              # React 19 SPA (Vite, TypeScript, Tailwind, shadcn/ui)
├── backend/               # Python 3.12+ FastAPI Application Layer
│   ├── app/
│   │   ├── auth/          # Authentication & RBAC (Argon2, JWT)
│   │   ├── projects/      # Project management & targets
│   │   ├── teams/         # Team assignments & memberships
│   │   ├── operations/    # Field activity recording & revisions
│   │   ├── verification/  # Verification centre & audit queue
│   │   ├── analytics/     # Verified environmental calculation engine
│   │   └── audit/         # System-wide audit history
│   └── alembic/           # PostgreSQL schema migration scripts
├── AGENTS.md              # Permanent engineering instructions
├── DECISION_LOG.md        # Architectural Decision Records (ADRs)
├── IMPLEMENTATION_ROADMAP.md # Milestone tracking & execution plan
├── IMPLEMENTATION_STATUS.md  # Real-time milestone progress log
└── DESIGN_REVIEW_CHECKLIST.md# Verification audit checklist
```

---

## 3. Technology Stack

| Layer | Approved Technologies |
|---|---|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, React Router, TanStack Query, React Hook Form, Zod, Recharts, React Leaflet, Axios |
| **Backend** | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PostgreSQL 16 |
| **Security** | Argon2 password hashing, Bearer JWT authentication, Granular RBAC, Anti-self-verification gate |
| **Hosting & CI/CD** | Docker, GitHub Actions, Vercel (Frontend), Render (Backend), Neon PostgreSQL |
| **Future Scale** | Redis, Celery, Amazon S3, AWS RDS, AWS ECS, OpenTelemetry, Prometheus, Grafana |

---

## 4. User Roles & Governance

| Role | Scope of Access | Key Responsibilities |
|---|---|---|
| **ADMIN** | Organization-Wide | Full administrative control, user provisioning, project creation, target setting, verification, audit review. |
| **PROJECT_MANAGER** | Assigned Projects Only | Team allocation, project workspace management, activity verification, performance tracking. |
| **FIELD_OFFICER** | Assigned Projects Only | Field activity reporting, GPS capture, photo evidence upload, revision resubmission. |

*Crucial Rule:* **Anti-Self-Verification** — Under no circumstance can a user verify their own submitted activity.

---

## 5. Documentation Directory

Detailed technical and design specifications are maintained in the `docs/` tree:

* **Design Blueprints (`docs/design/`):**
  * `01_BRAND_IDENTITY.md` — Visual brand identity, color tokens, and typography
  * `02_DESIGN_SYSTEM.md` — Spacing, component styling, layout grid, and tokens
  * `03_INFORMATION_ARCHITECTURE.md` — Route hierarchy, navigation, and role mapping
  * `04_USER_JOURNEYS.md` — Role-based operational user journeys
  * `05_SCREEN_SPECIFICATIONS.md` — Specifications for all 10 core screens
  * `06_WIREFRAMES.md` — Structural desktop and mobile ASCII wireframes
  * `07_COMPONENT_INVENTORY.md` — Reusable component catalog and states
  * `08_RESPONSIVE_DESIGN.md` — Breakpoint strategies and touch ergonomics
  * `09_INTERACTION_STATES.md` — Loading, empty, error, and optimistic states
  * `10_MVP_DESIGN_SCOPE.md` — Detailed boundary between MVP and future phases

* **Engineering Specifications (`docs/engineering/`):**
  * `01_SYSTEM_ARCHITECTURE.md` — Modular monolith boundaries and service contracts
  * `02_TECH_STACK.md` — Library versions, constraints, and dependencies
  * `03_DATABASE_DESIGN.md` — PostgreSQL relational schema, indexes, constraints, ERD
  * `04_API_SPECIFICATION.md` — RESTful API endpoints and Pydantic schemas
  * `05_SECURITY_AND_RBAC.md` — Authentication, authorization, and audit mechanics
  * `06_ENVIRONMENTAL_IMPACT_LOGIC.md` — Dimensional math, unit conversion, ledger rules
  * `07_TESTING_STRATEGY.md` — Unit, integration, regression, and E2E test matrices

* **Scalability Roadmap (`docs/scalability/`):**
  * `01_SCALABILITY_ROADMAP.md` — Triggers and phased migration plan
  * `02_INFRASTRUCTURE_EVOLUTION.md` — Evolution towards Celery, S3, RDS, ECS
  * `03_PERFORMANCE_STRATEGY.md` — Indexing, connection pooling, and tile caching

---

## 6. Development & Operational Governance

All contributors must review and abide by the permanent engineering rules in [AGENTS.md](AGENTS.md). 

* All changes must proceed through documented milestones outlined in [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md).
* Completed milestones and test statuses are tracked in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).
* All design choices and architectural deviations are recorded in [DECISION_LOG.md](DECISION_LOG.md).
