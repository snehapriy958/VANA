# VANA — Testing Strategy & Quality Assurance

This document details the test automation strategy, test matrices, testing tools, and validation gates enforced across the VANA platform.

---

## 1. Testing Pyramid & Tooling

```
      /\
     /  \     End-to-End Tests (Cypress / Playwright - Phase 2)
    /----\
   /      \   API & State Machine Integration Tests (pytest + httpx)
  /--------\
 /          \ Unit Tests: Math, Ledger, Units, Zod (pytest, vitest)
/------------\
```

| Testing Layer | Test Framework | Scope of Coverage | Target Pass Rate |
|---|---|---|:---:|
| **Unit Tests (Backend)** | `pytest`, `pytest-asyncio` | Mathematical unit conversion, dimensional validation, Pydantic schemas, recalculation logic. | 100% |
| **Integration Tests (Backend)**| `pytest`, `httpx`, `asyncpg` | FastAPI endpoints, JWT auth, RBAC permissions, anti-self-verification gate, Alembic migrations. | 100% |
| **Unit Tests (Frontend)** | `vitest`, React Testing Library | Form validation (Zod + React Hook Form), formatting utilities, metric card rendering. | 100% |

---

## 2. Core Business Logic Test Matrices

### 2.1 Environmental Ledger & Dimensionality Test Cases

| Test ID | Test Scenario | Input Data | Expected Outcome |
|---|---|---|---|
| `TEST-MATH-01` | Sum verified items of same metric code & unit | 3 activities: 200 trees, 250 trees, 150 trees (`APPROVED`) | Sum = 600 trees; Official Progress = 60.0% of 1,000 target. |
| `TEST-MATH-02` | Unit conversion within same metric code | 2 activities: 2 hectares, 5,000 $\text{m}^2$ (`AREA_RESTORED`) | Converted sum = 2.5 hectares. |
| `TEST-MATH-03` | Cross-metric aggregation prevention | Attempting to sum `TREES_PLANTED` and `SAPLINGS_PLANTED` | Throws `DimensionalityMismatchError`; transaction aborted. |
| `TEST-MATH-04` | Cross-dimension aggregation prevention | Attempting to sum `10 hectares` with `500 trees` | Throws `DimensionalityMismatchError`; rejected by Pydantic. |
| `TEST-MATH-05` | Pending quantity isolation | Target: 1,000 trees; Verified: 600 trees; Pending: 200 trees | Verified Achievement remains 600 trees (60%); Reported = 800. |
| `TEST-MATH-06` | Rejection quantity isolation | 50 trees rejected with reason `INSUFFICIENT_EVIDENCE` | Verified Achievement unaffected; Rejected quantity = 50. |

---

### 2.2 Verification State Machine & Security Test Cases

| Test ID | Test Scenario | Actor & Action | Expected Outcome |
|---|---|---|---|
| `TEST-AUTH-01` | Anti-self-verification violation | Submitter attempts `POST /verification/revisions/{id}/decision` on own submission | **HTTP 403 Forbidden** with `SELF_VERIFICATION_PROHIBITED`. |
| `TEST-AUTH-02` | Unassigned PM verification attempt | PM attempts to verify activity on unassigned project | **HTTP 403 Forbidden** with `PROJECT_NOT_ASSIGNED`. |
| `TEST-AUTH-03` | Missing rejection reason | PM rejects activity without `rejection_reason_code` | **HTTP 422 Unprocessable Entity**. |
| `TEST-AUTH-04` | Amendment revision lifecycle | Field Officer resubmits revision 2 for rejected activity | Revision 2 created with status `PENDING`; prior rejected record preserved. |
| `TEST-AUTH-05` | Re-verification delta recalculation | Verified activity of 200 trees amended to 250 trees and approved | Ledger recalculates delta (+50 trees); total verified updates to reflect 250 trees. |

---

## 3. Database Migration & Rollback Testing

Every Alembic migration must undergo automated two-way validation in the CI pipeline:
1. `alembic upgrade head` executes against an isolated PostgreSQL instance.
2. Integration tests verify tables, indexes, and constraints.
3. `alembic downgrade base` executes, ensuring all drops and reversions are clean.
4. `alembic upgrade head` re-runs to ensure zero drift.

---

## 4. Continuous Integration & Merge Gates

Pull requests must pass the following automated checks before merging:
* **Python Backend:** `flake8`, `black --check`, `mypy --strict`, `pytest -v --cov=app`.
* **TypeScript Frontend:** `tsc --noEmit`, `eslint`, `vitest run`.
* Zero warning policy on database migrations and model schemas.
