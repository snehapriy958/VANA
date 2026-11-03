# VANA — Approved Technology Stack Specification

> **Mandatory Policy:** The technologies, frameworks, and libraries specified herein constitute the fixed, permanent technology stack for VANA. No addition, replacement, or modification may occur without explicit architectural sign-off.

---

## 1. Frontend Technology Stack

| Layer / Capability | Approved Package / Tool | Version | Technical Rationale & Role |
|---|---|:---:|---|
| **Core Framework** | React | `19.x` | Modern reactive UI runtime, enhanced server component support, concurrent rendering. |
| **Language** | TypeScript | `5.x` | Strict compile-time type safety, preventing interface bugs across domain entities. |
| **Build Tool & Bundler** | Vite | `5.x+` | Fast HMR, optimized ESM production builds, lightweight configuration. |
| **Styling Engine** | Tailwind CSS | `3.4+` | Utility-first styling engine enforcing the VANA design tokens (`forest`, `ivory`, `gold`, `sage`). |
| **Component Primitives** | shadcn/ui (Radix UI) | Latest | Accessible, unstyled headless primitives styled directly with Tailwind CSS. |
| **Client-Side Routing** | React Router | `7.x` | Declarative client-side routing, nested layouts, loader data integration. |
| **Server State & Caching** | TanStack Query | `5.x` | Asynchronous query caching, optimistic UI updates, background query invalidation. |
| **Form Management** | React Hook Form | `7.x` | High-performance uncontrolled form handling, minimal re-renders. |
| **Schema Validation** | Zod | `3.x` | TypeScript-first runtime schema validation matching backend Pydantic models. |
| **Data Visualization** | Recharts | `2.x` | Declarative SVG charting library for time-series and dimensional progress charts. |
| **Geospatial Mapping** | React Leaflet / Leaflet | `4.x / 1.9+`| Client-side interactive mapping with GeoJSON polygon and marker clustering. |
| **HTTP Client** | Axios | `1.7+` | Request/response interceptors for Bearer JWT injection and 401 token refresh. |

---

## 2. Backend Technology Stack

| Layer / Capability | Approved Package / Tool | Version | Technical Rationale & Role |
|---|---|:---:|---|
| **Runtime Environment** | Python | `3.12+` | High performance, modern typing syntax (`type` statements, PEP 695), native async. |
| **Web Framework** | FastAPI | `0.115+` | High-throughput asynchronous REST API framework with native OpenAPI doc generation. |
| **Data Validation** | Pydantic | `2.9+` | Rust-backed high-speed request validation, strict type coercion, serialization. |
| **ORM & Data Access** | SQLAlchemy | `2.0+` | Modern typed async ORM with native PostgreSQL dialect support. |
| **Schema Migrations** | Alembic | `1.13+` | Version-controlled, reversible database schema evolution scripts. |
| **Relational Database** | PostgreSQL | `16.x` | Robust relational persistence, JSONB support for GeoJSON, transactional integrity. |
| **Password Hashing** | Argon2 (`argon2-cffi`)| Latest | Memory-hard, state-of-the-art password hashing conforming to OWASP guidelines. |
| **Authentication Tokens** | PyJWT | `2.9+` | Cryptographically signed JSON Web Tokens for stateless session authentication. |
| **Asynchronous Drivers** | `asyncpg` | Latest | High-speed native asynchronous driver for PostgreSQL. |

---

## 3. Infrastructure & Deployment Environment

* **Containerization:** Multi-stage `Dockerfile` with minimal production runtime images (`python:3.12-slim` and `node:20-alpine`).
* **Source Control & CI/CD:** GitHub repository with GitHub Actions workflows for linting, type checks, and automated pytest runs.
* **Frontend Hosting:** Vercel (Edge network deployment with automatic CDN caching).
* **Backend Hosting:** Render (Web Service running Uvicorn with Docker environment).
* **Database Hosting:** Neon PostgreSQL (Managed PostgreSQL 16 with automated backups).

---

## 4. Strict Dependency Prohibitions

To prevent architectural bloat and dependency vulnerabilities, the following are strictly prohibited in the MVP:
1. **No External Message Brokers:** RabbitMQ, Kafka, ActiveMQ.
2. **No Unapproved Database Extensions:** PostGIS (standard PostgreSQL `DOUBLE PRECISION` and JSONB are used instead).
3. **No Heavy Distributed Caches:** Redis, Memcached (PostgreSQL indexed queries and TanStack client caching are sufficient for MVP).
4. **No Heavy Headless Browsers:** Puppeteer, Playwright, or Selenium on the backend.
5. **No AI/ML Frameworks on the Backend:** PyTorch, TensorFlow, LangChain (VANA is a deterministic operations ledger).
