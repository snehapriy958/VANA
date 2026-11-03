# VANA — Role-Based User Journeys

This document outlines the step-by-step end-to-end user journeys for VANA's three primary user personas: Field Officer, Project Manager, and Administrator.

---

## 1. Persona 1: Field Officer (Field Operations & Reporting)

**Goal:** Accurately record on-site ecological interventions on a mobile device and track verification status.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Arrive at    │ ──► │ Select       │ ──► │ Select       │ ──► │ Enter        │
│ Field Site   │     │ Project      │     │ Metric Code  │     │ Quantity     │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                                                                      ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Track Status │ ◄── │ Submit Form  │ ◄── │ Attach Photo │ ◄── │ Capture GPS  │
│ (Pending/Rev)│     │ & Get ID     │     │ Evidence     │     │ Coordinates  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

### Detailed Operational Steps:
1. **Authentication & Project Selection:**
   * Field Officer logs into VANA on mobile browser (`/login`).
   * Platform redirects to `/operations/submit`.
   * User selects the active project from a dropdown filtered strictly to their assigned projects.
2. **Metric & Quantity Entry:**
   * User selects an approved `metric_code` (e.g., `TREES_PLANTED`).
   * The UI dynamically locks the permitted unit selection (e.g., `trees` or `saplings`) and displays the required measurement methodology helper text.
   * User enters recorded quantity (e.g., `250`).
3. **Geospatial & Evidence Capture:**
   * User taps "Capture Current Location". Browser invokes Geolocation API.
   * UI displays captured latitude, longitude, and accuracy radius (e.g., `12.9716° N, 77.5946° E (±4m)`).
   * User attaches 1 to 3 clear ground photos from the camera or gallery.
4. **Submission & Pending Status:**
   * User taps "Submit Field Activity".
   * Backend validates inputs, stores files via `IStorageService`, and creates a new parent activity with revision 1 in `PENDING` status.
   * User receives a confirmation screen with Submission ID `#ACT-8102` and status pill `PENDING REVIEW`.
5. **Rejection & Revision Flow (Exception Path):**
   * If the Project Manager rejects the submission (e.g., reason: `INSUFFICIENT_EVIDENCE`), the Field Officer receives a status notification.
   * User navigates to `/operations/history`, opens `#ACT-8102`, and reads the reviewer's feedback.
   * User taps "Submit Corrected Revision", attaches clear supplementary photos, and resubmits.
   * A new revision (Revision 2) enters `PENDING` review while Revision 1 remains preserved as `REJECTED`.

---

## 2. Persona 2: Project Manager (Operational Triage & Verification)

**Goal:** Review pending field submissions, scrutinize evidence, enforce verification standards, and monitor project target achievement.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Review Queue │ ──► │ Select Item  │ ──► │ Scrutinize   │ ──► │ Check Anti-  │
│ on Dashboard │     │ in Triage    │     │ Evidence     │     │ Self-Gate    │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                                   ┌──────────────────────────────────┴───────────────┐
                                   ▼                                                  ▼
                       ┌──────────────────────┐                           ┌───────────────────────┐
                       │ APPROVE              │                           │ REJECT                │
                       │ • State $\to$ APPROVED│                           │ • Select Reason Code  │
                       │ • Auto-Recalculate   │                           │ • Enter Review Notes  │
                       │ • Ledger Updated     │                           │ • State $\to$ REJECTED │
                       └──────────────────────┘                           └───────────────────────┘
```

### Detailed Operational Steps:
1. **Queue Inspection:**
   * Project Manager navigates to `/verification`.
   * The queue displays pending submissions from assigned projects, sorted by submission age.
2. **Deep Scrutiny in Dual-Pane View:**
   * PM clicks a submission. Left pane shows activity summary; right pane displays high-res photo gallery and an interactive map pin showing reported coordinates.
3. **Verification Enforcement:**
   * **Anti-Self-Verification Check:** If the PM was the author of the submission, the "Approve" and "Reject" buttons are disabled with a tooltip: *"You cannot verify your own submission."*
4. **Approval Action:**
   * PM clicks "Approve Submission".
   * Confirmation dialog summarizes the quantity and metric code being approved.
   * Backend updates revision status to `APPROVED`, marks it as the active ledger entry, updates the project's `current_verified_quantity`, and logs the event in the audit trail.
5. **Rejection Action:**
   * PM clicks "Reject Submission".
   * A required modal opens demanding a `rejection_reason_code` (e.g., `COORDINATES_MISMATCH`) and review notes explaining the defect.
   * Backend records rejection, preserving the submission under `current_rejected_quantity` without affecting verified totals.

---

## 3. Persona 3: Administrator (Governance, Setup & Portfolio Audit)

**Goal:** Configure new projects, establish dimensional targets, assign personnel, and audit organizational impact.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Create New   │ ──► │ Define Geo   │ ──► │ Set Metric   │ ──► │ Assign PMs   │
│ Project      │     │ Coordinates  │     │ Targets      │     │ & Field Team │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                                                                      ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Audit Full   │ ◄── │ Export Impact│ ◄── │ Review Org   │ ◄── │ Monitor Live │
│ History Logs │     │ Ledger Data  │     │ Analytics    │     │ Earth Map    │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

### Detailed Operational Steps:
1. **Project Creation & Bounding:**
   * Admin navigates to `/projects` and clicks "New Project".
   * Enters project name, biome type, organization sector, and center coordinates (`lat`, `lng`).
   * Optionally uploads or pastes a GeoJSON polygon boundary defining the project perimeter.
2. **Target Definition:**
   * Admin adds targets to the project:
     * Target 1: `TREES_PLANTED`, Target Quantity: `50,000`, Unit: `trees`, Deadline: `2027-12-31`.
     * Target 2: `AREA_RESTORED`, Target Quantity: `200`, Unit: `hectares`, Deadline: `2027-12-31`.
   * Backend validates metric codes and dimensional validity.
3. **Team Roster Allocation:**
   * Admin navigates to `/team`, selects the project, and assigns 1 lead Project Manager and 4 Field Officers.
4. **Audit Trail Inspection:**
   * Admin navigates to `/audit`.
   * Filters the audit log by Entity: `FIELD_ACTIVITY`, Date Range: `Past 30 Days`.
   * Reviews an approval event, inspecting the side-by-side JSON state diff (`previous_state` vs. `new_state`) showing exact changes to verified balances.
