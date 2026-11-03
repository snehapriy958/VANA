# VANA — Design System Specification

This document defines the core tokens, layout systems, component specifications, and accessibility criteria comprising the VANA Design System.

---

## 1. Design Token Architecture

### 1.1 Color Tokens (Tailwind CSS Mapping)

```css
:root {
  /* Brand Primitive Colors */
  --color-forest: #183D32;
  --color-ivory: #F5F3EA;
  --color-sage: #A8B99B;
  --color-gold: #D6A76A;
  --color-charcoal: #29332F;
  --color-white: #FFFFFF;
  --color-crimson: #9E3A2B;

  /* Semantic UI Tokens */
  --bg-canvas: var(--color-ivory);
  --bg-surface: var(--color-white);
  --bg-surface-subtle: #EBE8DC;
  
  --text-primary: var(--color-charcoal);
  --text-secondary: #5C6E66;
  --text-muted: #8A9E95;
  --text-on-dark: var(--color-white);

  --border-subtle: rgba(41, 51, 47, 0.08);
  --border-default: rgba(41, 51, 47, 0.15);
  --border-strong: rgba(41, 51, 47, 0.30);

  /* Status Colors */
  --status-verified-bg: rgba(24, 61, 50, 0.10);
  --status-verified-text: var(--color-forest);
  --status-verified-border: rgba(24, 61, 50, 0.25);

  --status-pending-bg: rgba(214, 167, 106, 0.15);
  --status-pending-text: #8C6228;
  --status-pending-border: rgba(214, 167, 106, 0.40);

  --status-rejected-bg: rgba(158, 58, 43, 0.10);
  --status-rejected-text: var(--color-crimson);
  --status-rejected-border: rgba(158, 58, 43, 0.25);
}
```

---

### 1.2 Spacing & Layout Scale
VANA implements a strict 4px/8px modular rhythm:

| Spacing Token | Pixels | Application |
|---|---|---|
| `space-1` | `4px` | Micro-spacing, pill padding, icon-text gap |
| `space-2` | `8px` | Button inline padding, input field compact gaps |
| `space-3` | `12px` | Card internal gap, badge margins |
| `space-4` | `16px` | Standard button padding, table cell padding |
| `space-6` | `24px` | Standard card interior padding, grid gap |
| `space-8` | `32px` | Section margins, drawer padding |
| `space-12`| `48px` | Major section breaks, page header separation |
| `space-16`| `64px` | Viewport edge padding on large screens |

---

### 1.3 Typographic Hierarchy

| Style Role | Font | Size / Line Height | Weight | Tracking | Case / Feature |
|---|---|---|---|---|---|
| **Display 1** | Manrope | 40px / 48px | 800 (ExtraBold) | `-0.025em` | Title Case |
| **Heading 1** | Manrope | 32px / 40px | 700 (Bold) | `-0.02em` | Title Case |
| **Heading 2** | Manrope | 24px / 32px | 700 (Bold) | `-0.015em` | Title Case |
| **Heading 3** | Manrope | 20px / 28px | 600 (SemiBold) | `-0.01em` | Title Case |
| **Subheading**| Manrope | 16px / 24px | 600 (SemiBold) | `0em` | Sentence Case |
| **Body Large**| Inter | 16px / 24px | 400 (Regular) | `0em` | Sentence Case |
| **Body Base** | Inter | 14px / 20px | 400 (Regular) | `0em` | Sentence Case |
| **Body Small**| Inter | 12px / 16px | 400 (Regular) | `+0.01em` | Sentence Case |
| **Metric Value**| Manrope | 28px / 32px | 700 (Bold) | `-0.02em` | Tabular Nums |
| **Table Data**| Inter | 13px / 18px | 400 / 500 | `0em` | Tabular Nums |
| **Overline**  | Inter | 11px / 14px | 600 (SemiBold) | `+0.08em` | All Caps |

---

### 1.4 Elevation, Borders & Corner Radii
* **Borders over Shadows:** Rather than heavy drop shadows, VANA uses clean hairline borders (`border-charcoal/10` or `1px solid rgba(41,51,47,0.12)`) to define elevation planes.
* **Corner Radii:**
  * `rounded-none` (0px): Map canvases, split-screen container dividers.
  * `rounded-sm` (4px): Badges, table selection checkboxes, dropdown menus.
  * `rounded-md` (6px): Form inputs, action buttons, table rows.
  * `rounded-lg` (8px): Cards, metric panels, modals, popovers.
  * `rounded-full` (9999px): Status indicator dots, user avatar thumbnails.
* **Elevation Shadows:**
  * `shadow-none`: Default flat surface.
  * `shadow-subtle`: `0 1px 3px rgba(24, 61, 50, 0.05)` (Standard card).
  * `shadow-floating`: `0 4px 12px rgba(24, 61, 50, 0.08)` (Dropdowns, modals).

---

## 2. Layout Grid Systems

* **Desktop (Viewport $\ge 1280\text{px}$):**
  * Fixed left navigation sidebar: 260px.
  * Dynamic content canvas: 12-column grid, max content width 1440px, 24px column gutters.
* **Tablet (Viewport $768\text{px}$ to $1279\text{px}$):**
  * Collapsible left navigation drawer (icon dock: 72px or full slide-over).
  * 8-column grid, 16px column gutters.
* **Mobile (Viewport $< 768\text{px}$):**
  * Top navigation bar (56px) + bottom navigation tab bar (64px).
  * 4-column grid, 16px side margins.

---

## 3. Accessibility Standards (WCAG 2.1 AA)

1. **Color Contrast:**
   * All primary and secondary body typography achieves a minimum 7:1 contrast ratio against the ivory canvas and white cards.
   * Status text badges (Verified, Pending, Rejected) maintain a minimum 4.5:1 ratio against their tinted background pills.
2. **Focus Visibility:**
   * Interactive components feature a prominent, accessible 2px focus ring: `ring-2 ring-forest ring-offset-2 ring-offset-ivory`.
3. **Screen Readers & ARIA:**
   * All icon-only buttons include descriptive `aria-label` tags.
   * Asynchronous verification updates use `aria-live="polite"` regions.
   * Metric progress bars include `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, and `aria-valuemax`.
