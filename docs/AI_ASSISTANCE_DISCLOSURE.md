# VANA — AI Assistance & Engineering Collaboration Disclosure

> **Platform:** VANA Environmental Operations & Impact Intelligence\
> **Submission To:** Akshaya Vana Climate Ventures Private Limited\
> **Author:** Sneha Priya\
> **Date:** November 4, 2026\
> **Compliance:** Full Transparency & Academic/Professional Honesty

---

## 1. Executive Statement

In accordance with the evaluation criteria established for the Akshaya Vana full-stack technical assignment, this document provides full, transparent disclosure regarding the utilization of Artificial Intelligence tools during the design, development, testing, and documentation of the VANA platform.

As the software engineer responsible for this submission:
- **Architecture & Domain Invariants:** I conceptualized, established, and directed the domain-driven modular monolith architecture, the environmental accounting rules, the anti-self-verification constraints, and the cryptographic ledger requirements.
- **Independent Verification:** Every line of code, database migration, automated test, mathematical calculation, and architectural decision was reviewed, executed, verified, and audited by me across authentic PostgreSQL 17, Python 3.12, and React 19 environments.
- **Accountability:** I take complete technical responsibility for the architecture, implementation quality, security boundaries, and bug fixes across the VANA codebase.

---

## 2. Tools & Workflows Utilized

| Tool / Model | Role in Development Workflow | Primary Areas of Assistance |
|---|---|---|
| **Google Antigravity / Gemini 2.5 Flash & Pro** | Agentic Pair Programming & Automation | - Scaffolding repetitive boilerplate code (FastAPI routers, Pydantic schemas, Tailwind UI components).\
- Rapid test generation (pytest edge cases, mock fixtures, node:test suites).\
- Automating regression runs, headless browser screenshots, and typechecking cycles.\
- Formatting architectural decision records (ADRs) and markdown documentation. |
| **Claude 3.7 Sonnet** | Architectural Sounding Board & Code Review | - Reviewing cryptographic hash-chaining conventions (RFC-compliant canonical JSON serialization).\
- Stress-testing PostgreSQL transaction concurrency (row locking via `SELECT ... FOR UPDATE`).\
- Auditing anti-self-verification invariants and multi-tenant RBAC boundaries. |

---

## 3. Detailed Scope of AI Assistance

### 3.1 Architectural Design & Business Logic (Human-Directed)
- **Human Contribution:** Defined the 13 core permanent engineering rules in `AGENTS.md`, including PostgreSQL as single source of truth, verified-only official environmental accounting, anti-self-verification, and strict unit dimensionality.
- **AI Contribution:** Assisted in translating these design invariants into cohesive Python type annotations, Pydantic DTO models, and SQLAlchemy ORM relationships.

### 3.2 Backend Implementation & Database Schema
- **Human Contribution:** Designed the relational data model across 12 domain tables, partial unique indexes (`uq_activity_single_active_ledger`, `uq_active_survival_observation`), and check constraints (`chk_active_ledger_verified`, `chk_rejection_reason_required`).
- **AI Contribution:** Generated initial Alembic migration scripts (`0001_initial_schema`, `0002_field_monitoring`, `0003_audit_immutability_ledger`) and assisted in implementing deterministic SHA-256 hash chaining functions with canonical JSON sorting.

### 3.3 Frontend Development & Design System
- **Human Contribution:** Defined the VANA design tokens (Forest Green `#183D32`, Warm Ivory `#F5F3EA`, Sage `#A8B99B`, Earth Gold `#D6A76A`, Charcoal `#29332F`), typography choices (`Manrope` headings, `Inter` body text), and component layout structures.
- **AI Contribution:** Assisted in authoring accessible React 19 components, TanStack Query hooks, Axios service wrappers, and dynamic before-and-after state diffing algorithms.

### 3.4 Quality Assurance & Test Suites
- **Human Contribution:** Formulated test scenarios for edge cases: concurrent sequence increments, transaction rollbacks preserving sequence continuity, negative tamper detection, and cross-project multi-tenant isolation.
- **AI Contribution:** Generated test cases resulting in 164 backend pytest tests and 99 frontend unit tests with 100% pass rates.

---

## 4. Engineering Ownership & Verification Standard

No AI-generated code was accepted blindly or committed without verification:
1. Every Alembic migration was tested with two-way execution cycles (`downgrade -1` $\to$ `upgrade head`).
2. Every cryptographic verification check was independently verified using negative mutation tests (intentionally mutating database payloads to prove that SHA-256 tampering detection fires accurately).
3. The full application stack was run live and automated in headless Chrome to capture genuine production screenshots.

I am fully prepared to defend, explain, live-code, and refactor any component of this platform during technical interviews.
