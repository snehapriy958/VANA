# VANA — UI Interaction States Specification

This document details the visual and behavioral patterns for asynchronous interaction states, loading skeletons, empty states, error handling, and optimistic updates across the VANA application.

---

## 1. Loading & Shimmer Skeletons

To avoid visual layout shifts (CLS) and provide immediate tactile feedback:
* **Metric Cards:** Metric numbers and progress bars render with an animated pulse skeleton matching exact typography dimensions:
  ```html
  <div class="h-8 w-24 bg-charcoal/10 rounded animate-pulse" />
  ```
* **Data Tables & Queue:** Display 5 rows of hairline skeleton bars matching table column widths.
* **Map Canvas:** Renders a subtle Warm Ivory placeholder with a centered spinning leaf indicator and label: *"Loading project boundaries & spatial pins..."*.

---

## 2. Empty State Patterns

Empty states in VANA must be **informative, dignified, and actionable** rather than generic dead-ends.

```
┌────────────────────────────────────────────────────────┐
│                        ( Icon )                        │
│                 No Active Projects Yet                 │
│   Create your first conservation project to begin      │
│   recording field interventions and tracking impact.   │
│                                                        │
│               [ + Create First Project ]               │
└────────────────────────────────────────────────────────┘
```

| Context | Heading | Description | Primary CTA |
|---|---|---|---|
| **Empty Portfolio** | "No Active Projects" | "Create an environmental project to establish targets and assign teams." | `[ + Create First Project ]` (Admin only) |
| **Empty Verification Queue** | "Verification Queue Clear" | "All submitted field activities have been verified. Great job!" | `[ View Verified Ledgers ]` |
| **Filtered Search Zero-Results** | "No Matching Submissions" | "No activities match your current filter parameters." | `[ Clear All Filters ]` |
| **No Assigned Projects (FO)** | "No Projects Assigned" | "You are not currently assigned to any active field projects. Contact your Project Manager." | — |

---

## 3. Error States & Recovery Mechanisms

1. **Inline Field Errors (Forms):**
   * Red hairline border on input: `border-crimson`.
   * High-contrast error message below input with icon: `text-crimson text-xs flex items-center gap-1`.
2. **Global API / Network Banners:**
   * If a query fails to fetch, a banner displays at the top of the container: *"Unable to load verified ledger data. [Retry Connection]"*.
3. **Session Timeout (401 Unauthorized):**
   * Modal dialog notifies the user: *"Your operational session has expired. Please sign in again."* Automatically preserves current form drafts in `sessionStorage` before redirecting to `/login`.

---

## 4. Optimistic UI Updates & Rollbacks

When a Project Manager approves or rejects a submission in the Verification Centre:
1. **Optimistic Transition:**
   * The item is immediately removed from the pending queue list in the UI, and the unreviewed queue counter decrements by 1 instantly.
   * The balance sheet progress bar animates to reflect the newly approved quantity immediately.
2. **Server Confirmation:**
   * A background mutation executes via TanStack Query: `POST /api/v1/verification/:id/decision`.
   * If the API responds with success (`HTTP 200`), a subtle toast appears: *"Activity #ACT-9041 verified. Official ledger updated."*
3. **Rollback on Error:**
   * If the API fails (e.g., anti-self-verification violation or network error), the optimistic update is rolled back immediately: the item returns to the queue, the counter restores, and an error alert is presented with the specific backend message.

---

## 5. Disabled States & Compliance Gates

* **Anti-Self-Verification Gate:**
  * When `current_user.id == activity.created_by_id`, the "Approve" and "Reject" buttons render in a muted, disabled visual state (`opacity-50 cursor-not-allowed`).
  * Hovering or tapping the button triggers a tooltip: *"Policy Violation: You cannot verify an activity submission you authored."*
* **Submission Without Evidence:**
  * The "Submit Activity" button remains disabled until at least one valid photo file has been uploaded and required coordinates are established.
