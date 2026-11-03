# VANA — Environmental Impact & Calculation Logic Specification

> **Notice:** The metric definitions and methodologies herein include illustrative metrics for system architecture and demonstration. In production, every active metric must be validated by Akshaya Vana scientific leadership. Metrics lacking an approved measurement methodology remain disabled.

---

## 1. Environmental Metric Classification & Definition Engine

VANA establishes a dual-tier taxonomy:
1. **Classification Categories (5 Groups):** High-level organizational groupings (`VEGETATION_PLANTING`, `LAND_RESTORATION`, `WATER_CONSERVATION`, `SOIL_CONSERVATION`, `WASTE_REMOVAL`).
2. **Individual Metric Definitions (`metric_code`):** Unique, dimensionally bound units of measurement with strictly validated field measurement procedures.

### Rule of Non-Contamination:
$$\textbf{NEVER aggregate two distinct metric codes merely because they share a dimension.}$$
For example, `TREES_PLANTED` and `SAPLINGS_PLANTED` both belong to dimension `COUNT`, but they represent distinct ecological interventions and **must never be summed together**.

---

## 2. Metric Definition Catalog

| Metric Code | Classification Category | Dimension | Canonical Base Unit | Supported Units | Conversion Factor to Base | Aggregation Eligibility | Measurement Methodology Summary |
|---|---|:---:|:---:|---|:---:|:---:|---|
| `TREES_PLANTED` | `VEGETATION_PLANTING` | `COUNT` | `trees` | `trees` | $1.0$ | Strict (Own Code) | Direct physical count of established native trees planted on site; tagged and geotagged. |
| `SAPLINGS_PLANTED` | `VEGETATION_PLANTING` | `COUNT` | `saplings` | `saplings` | $1.0$ | Strict (Own Code) | Physical tally of nursery saplings transplanted into soil plots; tagged with nursery lot number. |
| `AREA_RESTORED` | `LAND_RESTORATION` | `AREA` | `hectares` | `hectares`, $\text{m}^2$, `acres` | $\text{ha}: 1.0$<br>$\text{m}^2: 0.0001$<br>$\text{ac}: 0.404686$ | Strict (Own Code) | GPS boundary walking or polygon mapping of degraded land brought under active soil/vegetation restoration. |
| `AREA_REVEGETATED` | `LAND_RESTORATION` | `AREA` | `hectares` | `hectares`, $\text{m}^2$, `acres` | $\text{ha}: 1.0$<br>$\text{m}^2: 0.0001$<br>$\text{ac}: 0.404686$ | Strict (Own Code) | Direct measurement of canopy coverage or ground re-seeding within designated conservation boundaries. |
| `RAINWATER_HARVESTED` | `WATER_CONSERVATION` | `VOLUME` | `liters` | `liters`, $\text{m}^3$ | $\text{l}: 1.0$<br>$\text{m}^3: 1000.0$ | Strict (Own Code) | Water meter reading or calculated volume from certified percolation pits and check dams during rain events. |
| `RESERVOIR_CAPACITY_CREATED` | `WATER_CONSERVATION` | `VOLUME` | `cubic_meters` | `cubic_meters`, `liters` | $\text{m}^3: 1.0$<br>$\text{l}: 0.001$ | Strict (Own Code) | Civil engineering survey of excavated trench, bund, or farm pond storage volume capacity. |
| `WASTE_REMOVED` | `WASTE_REMOVAL` | `MASS` | `kilograms` | `kilograms`, `metric_tons` | $\text{kg}: 1.0$<br>$\text{t}: 1000.0$ | Strict (Own Code) | Certified weighbridge or hand-scale slip for physical non-biodegradable waste collected from site. |

*Metrics in the `SOIL_CONSERVATION` category (e.g. `TOPSOIL_PRESERVED`) remain disabled in the MVP pending calibrated scientific sampling procedures.*

---

## 3. Revision Lineage & The 5 Accounting Ledgers

Every reported activity belongs to a logical parent `field_activity` containing versioned `activity_revisions`. To prevent historical revisions from inflating active project quantities, VANA maintains five distinct accounting ledgers:

```
┌────────────────────────────────────────────────────────────────────────┐
│  VANA LEDGER ARCHITECTURE                                              │
│                                                                        │
│  1. Current Verified Quantity (A_verified):                            │
│     Sum of quantities of active approved revisions.                    │
│     (r in Revisions where r.is_active_ledger_entry = True)             │
│                                                                        │
│  2. Current Pending Quantity (Q_pending):                              │
│     Sum of pending quantities actively under consideration.            │
│     For an unverified activity: pending_revision.quantity.             │
│     For an amendment to a verified activity: max(0, new_qty - old_qty).│
│                                                                        │
│  3. Current Rejected Quantity (Q_rejected):                            │
│     Sum of quantities of current submissions currently in REJECTED     │
│     state (where no subsequent pending/approved revision exists).      │
│                                                                        │
│  4. Historical Rejected Submission Count:                              │
│     Total historical count of all revision records ever rejected.      │
│                                                                        │
│  5. Reported Quantity:                                                 │
│     Sum of claimed quantities across all active non-archived           │
│     logical activities: Current Verified + Net Pending Claims.         │
└────────────────────────────────────────────────────────────────────────┘
```

### Mathematical Definitions:

Let $\mathcal{A}$ be the set of active (non-archived) logical activities for project $P$ and metric code $M$.
For each activity $a \in \mathcal{A}$:
* Let $R_{\text{active}}(a)$ be the revision with `is_active_ledger_entry = TRUE` (if any).
* Let $R_{\text{current}}(a)$ be the latest revision (`revision_number = max`).

$$\text{Current Verified Quantity } (A_v) = \sum_{a \in \mathcal{A}} \begin{cases} R_{\text{active}}(a).\text{quantity} & \text{if } R_{\text{active}}(a) \text{ exists} \\ 0 & \text{otherwise} \end{cases}$$

$$\text{Current Pending Quantity } (Q_p) = \sum_{a \in \mathcal{A}} \begin{cases} 
R_{\text{current}}(a).\text{quantity} & \text{if } R_{\text{current}}(a).\text{status} = \text{PENDING and } R_{\text{active}}(a) = \emptyset \\
\max(0, R_{\text{current}}(a).\text{quantity} - R_{\text{active}}(a).\text{quantity}) & \text{if } R_{\text{current}}(a).\text{status} = \text{PENDING and } R_{\text{active}}(a) \neq \emptyset \\
0 & \text{otherwise}
\end{cases}$$

$$\text{Current Rejected Quantity } (Q_r) = \sum_{a \in \mathcal{A}} \begin{cases}
R_{\text{current}}(a).\text{quantity} & \text{if } R_{\text{current}}(a).\text{status} = \text{REJECTED and } R_{\text{active}}(a) = \emptyset \\
0 & \text{otherwise}
\end{cases}$$

$$\text{Reported Quantity} = \sum_{a \in \mathcal{A}} \begin{cases}
R_{\text{current}}(a).\text{quantity} & \text{if } R_{\text{current}}(a).\text{status} \in \{\text{APPROVED}, \text{PENDING}\} \\
R_{\text{active}}(a).\text{quantity} & \text{if } R_{\text{current}}(a).\text{status} = \text{REJECTED and } R_{\text{active}}(a) \neq \emptyset \\
0 & \text{if } R_{\text{current}}(a).\text{status} = \text{REJECTED and } R_{\text{active}}(a) = \emptyset
\end{cases}$$

$$\text{Official Progress Percentage } = \left( \frac{A_v}{\text{Target Quantity}} \right) \times 100$$

---

## 4. Test Scenarios & Conceptual Verification

### Scenario A: Three Approved Activities
* **Setup:** Target = 1,000 trees (`TREES_PLANTED`).
  * Activity 1: 200 trees (`APPROVED`, `is_active = True`)
  * Activity 2: 250 trees (`APPROVED`, `is_active = True`)
  * Activity 3: 150 trees (`APPROVED`, `is_active = True`)
* **Expected Quantities:**
  * **Current Verified:** $200 + 250 + 150 = \mathbf{600\text{ trees}}$
  * **Official Progress:** $\left(\frac{600}{1000}\right) \times 100 = \mathbf{60.0\%}$
  * **Current Pending:** $\mathbf{0\text{ trees}}$
  * **Current Rejected:** $\mathbf{0\text{ trees}}$
  * **Historical Rejected Count:** $\mathbf{0}$
  * **Reported Quantity:** $\mathbf{600\text{ trees}}$

---

### Scenario B: Approved Activity Receives a Pending Amendment
* **Setup:** From Scenario A, Activity 1 (currently verified at 200 trees) receives an amended submission: Revision 2 with quantity **250 trees** (`status = PENDING`, `is_active = False`).
* **Expected Quantities:**
  * **Current Verified:** $\mathbf{600\text{ trees}}$ (Activity 1 Rev 1 remains verified and legally active until Rev 2 is approved).
  * **Official Progress:** $\mathbf{60.0\%}$
  * **Current Pending:** $\mathbf{50\text{ trees}}$ (the net additional trees under review: $250 - 200$).
  * **Current Rejected:** $\mathbf{0\text{ trees}}$
  * **Historical Rejected Count:** $\mathbf{0}$
  * **Reported Quantity:** $250 \text{ (Act 1 claim)} + 250 \text{ (Act 2)} + 150 \text{ (Act 3)} = \mathbf{650\text{ trees}}$.
  * *Audit Assurance:* No double counting; reported quantity reflects the true current claim (650), not an inflated $600 + 250 = 850$.

---

### Scenario C: The Amendment in Scenario B is Rejected
* **Setup:** Project Manager reviews Activity 1 Revision 2 (250 trees) and rejects it with reason `INCORRECT_UNIT_OR_QUANTITY`.
* **State Transition:** Revision 2 transitions to `status = REJECTED`, `is_active = False`. Activity 1 Revision 1 remains `status = APPROVED`, `is_active = True`.
* **Expected Quantities:**
  * **Current Verified:** $\mathbf{600\text{ trees}}$ (Rev 1 remains untouched).
  * **Official Progress:** $\mathbf{60.0\%}$
  * **Current Pending:** $\mathbf{0\text{ trees}}$
  * **Current Rejected:** $\mathbf{0\text{ trees}}$ (Activity 1 is not in a rejected state because it possesses an active approved revision).
  * **Historical Rejected Count:** $\mathbf{1}$ (Revision 2 rejection recorded in immutable audit log).
  * **Reported Quantity:** $\mathbf{600\text{ trees}}$

---

### Scenario D: Rejected Activity Resubmitted and Approved
* **Step 1:** New Activity 4 submitted: Revision 1 with quantity 100 trees (`PENDING`).
  * Verified: 600 | Pending: 100 | Rejected: 0 | Reported: 700 | Hist. Rejected: 1
* **Step 2:** Activity 4 Revision 1 is rejected (`INSUFFICIENT_EVIDENCE`).
  * Verified: 600 | Pending: 0 | **Current Rejected: 100** | Reported: 600 | **Hist. Rejected: 2**
* **Step 3:** Field Officer resubmits Activity 4 Revision 2 with quantity 90 trees (`PENDING`).
  * Verified: 600 | **Current Pending: 90** | **Current Rejected: 0** (Rev 1 is now historical) | Reported: 690 | **Hist. Rejected: 2** (audit preserved).
* **Step 4:** Activity 4 Revision 2 is approved.
  * **Current Verified:** $600 + 90 = \mathbf{690\text{ trees}}$
  * **Official Progress:** $\left(\frac{690}{1000}\right) \times 100 = \mathbf{69.0\%}$
  * **Current Pending:** $\mathbf{0\text{ trees}}$
  * **Current Rejected:** $\mathbf{0\text{ trees}}$
  * **Historical Rejected Count:** $\mathbf{2}$ (both historical rejections preserved)
  * **Reported Quantity:** $\mathbf{690\text{ trees}}$

---

### Scenario E: Two Different Metric Codes Using Same Dimension
* **Setup:** Project tracks two targets:
  * Target 1: `TREES_PLANTED` (`COUNT`), Target = 1,000 trees. Verified = 600 trees.
  * Target 2: `SAPLINGS_PLANTED` (`COUNT`), Target = 5,000 saplings. Verified = 2,000 saplings.
* **Calculation Rule:** Strict metric isolation.
  * Target 1 Official Progress = $\mathbf{60.0\%}$ (`TREES_PLANTED`).
  * Target 2 Official Progress = $\mathbf{40.0\%}$ (`SAPLINGS_PLANTED`).
  * **Combined Scalar:** $\mathbf{\text{PROHIBITED}}$. The calculation engine explicitly rejects summing these two metric codes together ($600 + 2000 \ne 2600$). They are presented on separate balance sheets.

---

### Scenario F: An Activity is Deleted or Archived
* **Setup:** From Scenario A (Verified = 600 trees: 200 + 250 + 150), Activity 3 (150 trees) is discovered to be a duplicate site submission. Admin archives Activity 3 via `DELETE /operations/activities/{id}`.
* **State Transition:**
  * `field_activities.is_archived` is set to `TRUE`.
  * Activity 3 Revision 1 has `is_active_ledger_entry` set to `FALSE`.
  * Recalculation engine runs transactionally.
  * Audit log entry created: `action_type = 'ACTIVITY_ARCHIVED'`, `entity_id = Activity 3 UUID`.
* **Expected Quantities:**
  * **Current Verified:** $200 + 250 = \mathbf{450\text{ trees}}$
  * **Official Progress:** $\left(\frac{450}{1000}\right) \times 100 = \mathbf{45.0\%}$ (immediately reduced by 150 trees).
  * **Current Pending:** $\mathbf{0\text{ trees}}$
  * **Current Rejected:** $\mathbf{0\text{ trees}}$
  * **Reported Quantity:** $\mathbf{450\text{ trees}}$
  * **Historical Rejected Count:** Unchanged.
