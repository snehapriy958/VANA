# VANA Phase 6 — Architecture Review & Design Corrections

> **Document Status:** Final Gate Review Record\
> **Date:** November 3, 2026\
> **Target Release:** VANA Phase 6 (Field Monitoring & Follow-up Management)\
> **Review Scope:** Audit of initial design and pre-implementation gate resolutions, recording all architectural corrections, methodological groundings, security hardening, evidence retention analysis, database parity verification, and open decisions.

---

## 1. Executive Summary & Review Objectives

Following initial design reviews and stakeholder pre-implementation gating, the architecture for Phase 6 was refined across five critical operational areas:
1. **Cross-Project Referential Integrity:** Physical database-level enforcement using composite foreign keys `(entity_id, project_id)` plus transactional service-level validation.
2. **Survival Plot and Cohort Identity:** Establishing the monitored population unit as the 3-tuple `(project_id, plot_identifier, cohort_identifier)`, accommodating multiple cohorts per plot and multi-plot cohorts, and implementing an append-only historical correction model.
3. **Threshold Grounding:** Removal of the arbitrary 70% universal survival threshold from active alert evaluation, restricting alerts to deterministic operational deadlines (`OVERDUE_INSPECTION`, `UPCOMING_INSPECTION`, `OVERDUE_TASK`).
4. **Evidence Retention & Audit Invariants:** Transitioning the relationship between `evidence_files` and `field_inspections` from `CASCADE` to `RESTRICT` to prevent accidental loss of photo evidence.
5. **Database Revision Synchronization:** Concrete verification of live database heads (`vana_dev` and `vana_test`) confirming 100% synchronization at `0001_initial_schema`.

---

## 2. Itemized Pre-Implementation Gate Resolutions

### Gate Issue 1: Cross-Project Referential Integrity
* **Finding:** While service-level checks were proposed, database foreign keys could still theoretically allow cross-project entity references if service validation were bypassed.
* **Resolution:**
  * Added `UNIQUE (id, project_id)` to `field_activities` and `field_inspections`.
  * Implemented composite foreign keys:
    * `(linked_activity_id, project_id) REFERENCES field_activities(id, project_id)` on `field_inspections`.
    * `(inspection_id, project_id) REFERENCES field_inspections(id, project_id)` and `(activity_id, project_id) REFERENCES field_activities(id, project_id)` on `maintenance_tasks`.
    * `(inspection_id, project_id) REFERENCES field_inspections(id, project_id)` and `(activity_id, project_id) REFERENCES field_activities(id, project_id)` on `survival_observations`.
  * Service layer validates all references prior to execution, returning `400 Bad Request`.
  * Integration tests verify rejection of cross-project references.

### Gate Issue 2: Survival Plot and Cohort Identity Rules
* **Finding:** Ambiguity regarding multi-cohort plots, multi-plot cohorts, and how historical corrections are represented without data loss.
* **Resolution:**
  * Defined population unit identity as `(project_id, plot_identifier, cohort_identifier)`.
  * Supported multi-cohort plots (e.g. 2025 planting + 2026 enrichment) and multi-plot cohorts.
  * Longitudinal queries filter strictly by the exact 3-tuple and methodology.
  * Implemented append-only correction pattern: original record marked `is_active = FALSE`, linked to new record via `superseded_by_id`, preserving audit history.

### Gate Issue 3: Removal of Unsupported Survival Thresholds
* **Finding:** The universal 70% threshold alert lacked an approved empirical or biome-specific policy basis.
* **Resolution:**
  * Removed `LOW_SURVIVAL_RATE` from the active MVP alert engine.
  * Survival monitoring displays raw observation date, methodology (`SAMPLE_PLOT`, `TRANSECT`, `FULL_CENSUS`), sample size ($N_{\text{sample}}$), assessed count ($A + D$), and observed sample rate:
    $$\text{observed\_sample\_survival\_rate} = \frac{A}{A + D} \times 100 \quad (\text{when } A + D > 0)$$
  * No speculative classifications ("healthy", "critical") are applied. Configurable biome thresholds deferred to future milestones.

### Gate Issue 4: Evidence Retention and Referential Integrity
* **Finding:** `ON DELETE CASCADE` on `evidence_files.inspection_id` violated Rule 6 (Audit Trail Integrity).
* **Resolution:**
  * Configured `ON DELETE RESTRICT` on `evidence_files.inspection_id`. Inspections with evidence cannot be deleted from the database.
  * Verified that target check constraint `chk_evidence_target` is 100% backward-compatible with existing activity and revision evidence records.

### Gate Issue 5: Live Database Revision Verification
* **Finding:** Previous review assumed migration alignment without verifying live database state.
* **Resolution:**
  * Queried live PostgreSQL instances on port 15432:
    * `vana_dev`: `0001_initial_schema`
    * `vana_test`: `0001_initial_schema`
  * Parity with `backend/alembic/versions/0001_initial_schema.py` confirmed. Down revision for `0002_field_monitoring.py` is definitively `0001_initial_schema`.

---

## 3. Comparison Matrix: Initial Design vs Final Gate Design

| Dimension | Initial Proposal | Corrected Review | Final Gate Design |
| :--- | :--- | :--- | :--- |
| **Cross-Project Integrity** | Implicit / UI trust | Service-level checks | Composite DB Foreign Keys + Service checks |
| **Population Identity** | Project + Date | Plot + Cohort strings | Tuple `(project, plot, cohort)` + Append-only corrections |
| **Survival Thresholds** | Hardcoded 70% | Configurable param | Removed from MVP alerts; raw rates only |
| **Evidence Retention** | Redundant table / Cascade | Shared table / Cascade | Shared table with `ON DELETE RESTRICT` |
| **Database Parity** | Assumed from file | File inspected | Empirically verified on live PostgreSQL |
| **Table Additions** | 4 new tables | 3 tables + 1 alter | 3 tables + 1 alter + 1 composite unique |

---

## 4. Final Sign-off Verdict

All five pre-implementation issues are conclusively resolved. The design is frozen and ready for code implementation upon explicit stakeholder instruction.
