# VANA — Responsive Design & Ergonomics Specification

This document details the responsive adaptation strategy, breakpoint behaviors, and touch-screen ergonomics across Desktop, Tablet, and Mobile devices.

---

## 1. Breakpoint Grid & Fluid Containers

| Breakpoint Name | Tailwind Token | Viewport Range | Primary Target Devices | Grid Columns / Margins |
|---|---|---|---|:---:|
| **Mobile** | Default (`< md`) | $320\text{px}$ to $767\text{px}$ | Smartphones (iOS, Android) | 4 columns / 16px padding |
| **Tablet** | `md:` / `lg:` | $768\text{px}$ to $1279\text{px}$ | iPad, Android Tablets, Foldables | 8 columns / 24px padding |
| **Desktop** | `xl:` / `2xl:` | $\ge 1280\text{px}$ | Laptops, High-Resolution Displays | 12 columns / 32px padding |

---

## 2. Cross-Device Responsive Adaptations

### 2.1 Navigation & Shell Structure
* **Desktop ($\ge 1280\text{px}$):** Persistent left sidebar (260px width) with text labels, live unreviewed count badges, and user profile pill at bottom.
* **Tablet ($768\text{px} - 1279\text{px}$):** Collapses to an icon-only rail (72px width) with hover tooltips; expands to a slide-over drawer upon tapping the hamburger icon.
* **Mobile ($< 768\text{px}$):** Top header (56px) with organization indicator; fixed bottom navigation bar (64px) with high-priority role-specific destinations.

### 2.2 Split-Screen Verification Centre
* **Desktop:** Side-by-side dual pane (Queue 40%, Detail Inspection 60%).
* **Tablet:** Queue occupies full width; clicking an item opens a 70% slide-over inspection modal.
* **Mobile:** Queue rendered as scrollable cards; selecting an item navigates to a dedicated full-screen verification view (`/verification/:id`) with sticky bottom Approve/Reject action bar.

### 2.3 Data Tables vs. Card Stacks
* **Desktop & Tablet:** High-density data tables with fixed headers, sortable columns, and tabular figure alignment.
* **Mobile:** Data tables automatically transform into vertical card stacks (`MobileCardList`), surfacing essential data (Project, Date, Metric, Status Badge) with click-to-expand details.

---

## 3. Mobile Touch Ergonomics (Field Operations)

Field Officers frequently operate smartphones outdoors under variable sunlight, sometimes while wearing field gloves. The following touch standards are mandatory:

1. **Touch Target Sizing:**
   * All primary interactive elements (buttons, inputs, select triggers, checkboxes) have a minimum touch target of **$48\text{px} \times 48\text{px}$** (exceeding the standard 44px threshold).
2. **One-Thumb Reach Zone:**
   * Primary action buttons (e.g., "Capture GPS", "Take Photo", "Submit Field Activity") are anchored in the lower 40% of the mobile screen.
3. **Native Device Hardware Integration:**
   * File upload buttons invoke the native mobile camera interface directly via `capture="environment"` attribute, enabling instant photo capture without navigating through gallery folders.
4. **Visual Contrast Outdoors:**
   * Form input borders and text labels utilize high-contrast Charcoal (`#29332F`) against Pure White card surfaces to ensure legibility under direct sunlight.
