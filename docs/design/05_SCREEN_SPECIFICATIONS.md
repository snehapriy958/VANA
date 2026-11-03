# VANA — Comprehensive Screen Specifications

This document defines the functional and technical specifications for all 10 core screens in the VANA platform.

---

## Screen Index
1. [Screen 01: Login & Authentication](#screen-01-login--authentication)
2. [Screen 02: Organization Dashboard](#screen-02-organization-dashboard)
3. [Screen 03: Project Explorer](#screen-03-project-explorer)
4. [Screen 04: Project Workspace](#screen-04-project-workspace)
5. [Screen 05: Living Earth — Interactive Project Map](#screen-05-living-earth--interactive-project-map)
6. [Screen 06: Field Operations & Activity Reporting](#screen-06-field-operations--activity-reporting)
7. [Screen 07: Activity Verification Centre](#screen-07-activity-verification-centre)
8. [Screen 08: Environmental Impact Analytics](#screen-08-environmental-impact-analytics)
9. [Screen 09: Team & User Management](#screen-09-team--user-management)
10. [Screen 10: Audit History](#screen-10-audit-history)

---

## Screen 01: Login & Authentication
* **Route:** `/login`
* **Purpose:** Authenticate users securely into VANA via email and password, establishing role-based sessions.
* **Target Roles:** `ADMIN`, `PROJECT_MANAGER`, `FIELD_OFFICER` (Public unauthenticated entry).
* **Layout & Navigation:** Dual-column editorial layout on desktop. Left column (45%): Brand hero panel with Forest Green background, nature imagery snippet, and VANA manifesto. Right column (55%): Minimalist white authentication card on Warm Ivory canvas. Single-column card on mobile. Redirects upon success based on role (`ADMIN`/`PM` $\to$ `/dashboard`, `FIELD_OFFICER` $\to$ `/operations/submit`).
* **Components & Displayed Data:** Brand logo, Email input field, Password input with visibility toggle, "Sign In" button, Error alert banner, Session timeout notification.
* **User Actions:** Enter credentials, submit form, toggle password mask, dismiss error notices.
* **Interaction States:**
  * *Loading State:* "Sign In" button displays a centered spinning indicator; inputs are disabled.
  * *Empty State:* Form inputs render clean with placeholder labels (`user@akshayavana.com`).
  * *Success State:* Green confirmation checkmark renders; smooth 200ms fade transition redirects to target workspace.
  * *Error State:* Red hairline input borders (`border-crimson`) and banner notification ("Invalid email or password").
* **Responsive Behavior:** Hero panel hides on screens $< 1024\text{px}$; form centers horizontally with 24px side padding and full-width inputs.
* **Acceptance Criteria:**
  1. Authenticates against `/api/v1/auth/login` using Argon2 verification.
  2. Stores JWT access token securely; initializes auth context.
  3. Rejects invalid credentials with standard non-enumerating error message.
  4. Enforces role-based redirection immediately upon success.

---

## Screen 02: Organization Dashboard
* **Route:** `/dashboard`
* **Purpose:** Executive command center providing high-level portfolio oversight, verified environmental totals, and verification velocity.
* **Target Roles:** `ADMIN`, `PROJECT_MANAGER` (scoped to assigned projects).
* **Layout & Navigation:** Top executive summary row (4 metric cards), Middle section: Dual-panel split (Left: Portfolio progress balance sheets; Right: Mini Living Earth map preview), Bottom section: Recent verification activity stream and pending queue alerts. Sidebar navigation highlight.
* **Components & Displayed Data:** KPI summary cards, Dimensional progress balance bars, Interactive Leaflet mini-map, Activity timeline stream, Pending review alert pill. Active projects count, Total Verified Trees (`COUNT`), Total Verified Hectares Restored (`AREA`), Total Verified Water Conserved (`VOLUME`), Pending Verification Count, Recent activity feed.
* **User Actions:** Click KPI card to drill down into Analytics, click "Review Pending" to navigate to Verification Centre, click mini-map to launch full Living Earth view.
* **Interaction States:**
  * *Loading State:* Pulse shimmer skeletons for all 4 metric cards, balance bars, and activity list.
  * *Empty State:* Clean empty-slate panel with "Create First Project" CTA for new organizations.
  * *Success State:* Live data rendered with crisp hairline borders and green verified badges.
  * *Error State:* Error banner with "Unable to load portfolio rollups. [Retry]" button.
* **Responsive Behavior:** 4-column metric row stacks into 2 columns on tablet and 1 column on mobile. Mini-map collapses beneath balance sheet on screens $< 1024\text{px}$.
* **Acceptance Criteria:**
  1. Displays strictly verified achievement totals; pending quantities displayed in a secondary distinct callout.
  2. PM view filters aggregates exclusively to their assigned projects.
  3. Loads within 800ms with cached rollups.

---

## Screen 03: Project Explorer
* **Route:** `/projects`
* **Purpose:** Searchable, filterable directory of all environmental projects with progress and location metadata.
* **Target Roles:** `ADMIN`, `PROJECT_MANAGER`, `FIELD_OFFICER` (view assigned).
* **Layout & Navigation:** Top header with action bar (Search, Filter by Status, Filter by Biome, "New Project" button for Admins), Main view: Toggleable between Card Grid View and Dense Data Table View. Clicking project card navigates to `/projects/:projectId`.
* **Components & Displayed Data:** Search bar, Filter dropdowns, Project Summary Card, Status Badge (`ACTIVE`, `COMPLETED`, `DRAFT`), Data Table with sorting, Pagination footer. Project name, Biome, Location (lat/lng coordinates), Primary Target vs. Verified Progress %, Assigned Lead PM, Last Activity Date.
* **User Actions:** Search by name/region, filter by status, toggle card/table view, click project to open workspace, click "New Project" (Admin only) to launch creation wizard.
* **Interaction States:**
  * *Loading State:* 6-card shimmer skeleton grid with animated pulsing blocks.
  * *Empty State:* "No projects match your filter criteria." with a "Clear All Filters" button.
  * *Success State:* Grid or table view populated with projects and progress badges.
  * *Error State:* Alert banner notifying of network failure with retry action.
* **Responsive Behavior:** Table switches to vertical card list on mobile viewports ($< 768\text{px}$). Filter dropdowns collapse into a slide-over filter drawer.
* **Acceptance Criteria:**
  1. "New Project" button hidden for non-Admin users.
  2. Field Officers see only projects they are explicitly assigned to.
  3. Filter state persists in URL query parameters (`?status=ACTIVE&search=`).

---

## Screen 04: Project Workspace
* **Route:** `/projects/:projectId`
* **Purpose:** Single-project command center detailing targets, team allocations, localized map, and activity records.
* **Target Roles:** `ADMIN`, `PROJECT_MANAGER` (assigned), `FIELD_OFFICER` (assigned).
* **Layout & Navigation:** Hero banner with project name, status badge, center coordinates, and assigned PM. Below: Tabbed navigation (`[Overview]`, `[Targets & Achievements]`, `[Field Activities]`, `[Team Roster]`).
* **Components & Displayed Data:** Project header, Metric Target Balance Cards, Team Allocation Table, Localized Leaflet Map with boundary polygon, Paginated Activity History Table. Project metadata, Target vs. Verified Achievement vs. Pending Quantity per metric code, Percent progress bars per target, Roster of assigned PMs and Field Officers.
* **User Actions:** Switch tabs, PM/Admin can edit targets or add team members, Field Officer can click "Submit Activity for this Project".
* **Interaction States:**
  * *Loading State:* Tab contents render with placeholder shimmer blocks.
  * *Empty State:* Target tab shows "No targets defined yet" with "Add Target" CTA (for PM/Admin).
  * *Success State:* Verified achievements display alongside active targets with dual-color progress bars.
  * *Error State:* Error banner if project ID is invalid or access is forbidden (403).
* **Responsive Behavior:** Tabs render as horizontal scrollable pill bar on mobile. Map displays above tables on small screens.
* **Acceptance Criteria:**
  1. Verified progress bar calculated strictly from active approved revisions.
  2. Rejection counts and pending quantities clearly labeled and distinct from verified numbers.
  3. Localized map displays the project's GeoJSON boundary polygon if present.

---

## Screen 05: Living Earth — Interactive Project Map
* **Route:** `/map`
* **Purpose:** Geospatial visualization of all environmental project locations, boundary zones, and field activities.
* **Target Roles:** `ADMIN`, `PROJECT_MANAGER`, `FIELD_OFFICER` (scoped to permissions).
* **Layout & Navigation:** Full-viewport interactive Leaflet map canvas. Floating top-left search & filter dock; floating bottom-right layer control dock; slide-out inspection drawer on click.
* **Components & Displayed Data:** React Leaflet map canvas, Custom SVG Forest Green project markers, GeoJSON polygon boundary layer, Activity pin clusters color-coded by status, Slide-over inspection drawer. Project boundary polygons, Center coordinates, Activity pins (Green: Approved, Gold: Pending, Crimson: Rejected).
* **User Actions:** Pan/zoom map, toggle layer visibility (Projects, Boundaries, Activities), click pin to open slide-over detail drawer, click "Open Workspace" from drawer.
* **Interaction States:**
  * *Loading State:* Translucent ivory overlay with centered spinning leaf icon and loading text.
  * *Empty State:* Map defaults to central geographic view with toast: "No mapped activities in this area."
  * *Success State:* Interactive pins and polygons rendered cleanly with smooth hover tooltips.
  * *Error State:* Tile load failure warning banner with fallback to standard map styling.
* **Responsive Behavior:** Slide-over detail drawer converts to an accessible swipeable bottom sheet on mobile devices ($< 768\text{px}$).
* **Acceptance Criteria:**
  1. Renders projects and activities matching user's role scope.
  2. Projects without polygons render clean circular buffer markers centered on `(latitude, longitude)`.
  3. Mobile view displays inspection drawer as an accessible swipeable bottom sheet.

---

## Screen 06: Field Operations & Activity Reporting
* **Route:** `/operations/submit`
* **Purpose:** Mobile-first data capture tool enabling Field Officers to record on-site activities with photos and GPS coordinates.
* **Target Roles:** `FIELD_OFFICER`, `PROJECT_MANAGER`, `ADMIN`.
* **Layout & Navigation:** Single-column mobile-optimized card (max width 600px). Sticky header with submission step indicator; sticky bottom action bar with submit button. Accessible via mobile bottom navigation.
* **Components & Displayed Data:** Project selector dropdown, Metric Code picker, Unit selection pill group, Quantity numeric input, "Get GPS Location" button with accuracy indicator, Multi-file photo uploader with preview thumbnails, Notes textarea, Submission button.
* **User Actions:** Select project and metric, input quantity, trigger browser GPS, capture/upload evidence photos, add notes, submit report.
* **Interaction States:**
  * *Loading State:* "Submitting Field Report..." spinner on submit button; form inputs locked.
  * *Empty State:* Blank form with pre-selected default assigned project and helpful metric guidelines.
  * *Success State:* Confirmation modal displays Submission ID (`#ACT-9042`), status badge `PENDING REVIEW`, and "Submit Another" button.
  * *Error State:* High-contrast red field validation errors below invalid inputs; banner if GPS accuracy $> 25\text{m}$.
* **Responsive Behavior:** Touch targets expanded to $\ge 48\text{px}$; photo uploader triggers native mobile camera directly via `capture="environment"`.
* **Acceptance Criteria:**
  1. Prevents form submission if quantity $\le 0$, photo missing, or project unselected.
  2. Unit selection constrained strictly to supported units for the chosen `metric_code`.
  3. Displays warning if GPS accuracy radius $> 25\text{m}$.
  4. Stores draft values in `sessionStorage` to guard against transient network loss.

---

## Screen 07: Activity Verification Centre
* **Route:** `/verification`
* **Purpose:** Operational audit and review queue for Project Managers and Admins to scrutinize evidence and approve/reject field activities.
* **Target Roles:** `ADMIN`, `PROJECT_MANAGER` (assigned projects).
* **Layout & Navigation:** Dual-pane split-screen. Left pane (40% width): Scrollable queue of pending activities sorted by date. Right pane (60% width): Deep inspection view for selected activity.
* **Components & Displayed Data:** Triage queue table, Filter bar (by Project, Submitter, Date), Evidence photo lightbox viewer, Map location verification widget, Review Action Bar (`[Approve]`, `[Reject]`). Submitter name, metric code, quantity, unit, GPS coordinates, photo evidence, revision history.
* **User Actions:** Select activity from queue, zoom photo, inspect location, Approve submission, Reject submission (launches rejection reason modal).
* **Interaction States:**
  * *Loading State:* Left queue renders skeleton cards; right pane displays loading placeholder.
  * *Empty State:* "Queue Clear — All submissions have been verified!" with link to Project Workspace.
  * *Success State:* Toast notification confirms: "Activity verified; project ledger recalculated." Item smoothly animates out of queue.
  * *Error State:* Error banner if approval fails; buttons disabled with tooltip if self-verification attempted.
* **Responsive Behavior:** On screens $< 1024\text{px}$, queue is full-width; selecting an activity opens inspection view in a dedicated modal or full-screen page.
* **Acceptance Criteria:**
  1. **Anti-Self-Verification Enforced:** Approve and Reject buttons disabled if `current_user.id == activity.created_by_id`.
  2. Rejection requires selecting a valid `rejection_reason_code` and entering non-empty review notes.
  3. Approving an item removes it from the pending queue and triggers immediate recalculation of project achievement totals.

---

## Screen 08: Environmental Impact Analytics
* **Route:** `/analytics`
* **Purpose:** Deep-dive environmental intelligence, verified metric trends, dimensional comparisons, and audit disclosures.
* **Target Roles:** `ADMIN`, `PROJECT_MANAGER` (assigned projects).
* **Layout & Navigation:** Top filter bar (Project selector, Metric Code selector, Date range selector). Middle row: Key verified totals and historical velocity. Bottom row: 2 dimensional time-series charts (Recharts) and project comparison data table.
* **Components & Displayed Data:** Metric dimension selector, Time-series line chart (Cumulative Verified Quantity over time), Monthly breakdown bar chart, Project benchmark table, CSV Data Export button. Cumulative verified quantities by metric code, monthly velocity, data methodology citations box.
* **User Actions:** Change time window (`30d`, `90d`, `1y`), switch metric codes, export raw verified data table to CSV.
* **Interaction States:**
  * *Loading State:* Recharts surfaces display animated shimmer outlines; KPI cards show skeleton blocks.
  * *Empty State:* "No verified data available for this metric and time period." with prompt to review pending queue.
  * *Success State:* Interactive charts render with hover tooltips displaying exact verified numbers and dates.
  * *Error State:* Alert banner if historical aggregation query times out.
* **Responsive Behavior:** Charts maintain fluid aspect ratios; benchmark table scrolls horizontally on mobile with fixed first column.
* **Acceptance Criteria:**
  1. Displays **zero** synthetic multipliers (no fake carbon estimates or hypothetical biodiversity scores).
  2. Different metric codes are plotted in separate charts; never summed together.
  3. Data export contains verifiable audit hashes and revision references.

---

## Screen 09: Team & User Management
* **Route:** `/team`
* **Purpose:** Manage organization personnel, assign roles, and map staff to specific project rosters.
* **Target Roles:** `ADMIN` (full control), `PROJECT_MANAGER` (view and assign within assigned projects).
* **Layout & Navigation:** Top action header (Search staff, "Invite User" button for Admin). Main body: Team directory table with expandable project assignment rows.
* **Components & Displayed Data:** User roster data table, Role Badge pill (`ADMIN`, `PROJECT_MANAGER`, `FIELD_OFFICER`), Status toggle (`ACTIVE`, `INACTIVE`), "Assign Projects" modal dialog, User creation dialog. User full name, Email address, Assigned Role, Number of Active Projects, Total Submissions / Verifications, Account Status.
* **User Actions:** Admin can create user, change role, deactivate account, and assign users to projects. PM can assign field officers to their assigned projects.
* **Interaction States:**
  * *Loading State:* Table rows render with 5 animated skeleton bars.
  * *Empty State:* "No team members found." with clear search button.
  * *Success State:* Toast confirms user created or role updated; table reflects change instantly.
  * *Error State:* Form validation errors inside modal dialog (e.g., "Email already registered").
* **Responsive Behavior:** User rows collapse into profile cards with expandable assignment chips on mobile.
* **Acceptance Criteria:**
  1. Role modification and user creation restricted to `ADMIN`.
  2. PMs can only add/remove field officers for projects where they are designated as Project Manager.
  3. All role updates and project assignment changes trigger an audit log record.

---

## Screen 10: Audit History
* **Route:** `/audit`
* **Purpose:** Comprehensive, immutable system-wide change ledger for regulatory compliance, traceability, and dispute resolution.
* **Target Roles:** `ADMIN` only.
* **Layout & Navigation:** Full-width high-density data ledger with advanced filtering dock at the top (Entity Type, Action Type, Actor, Date Range).
* **Components & Displayed Data:** Audit event table, Actor avatar pill, Action Badge (`VERIFY_APPROVED`, `VERIFY_REJECTED`, `TARGET_UPDATED`, `ROLE_CHANGED`), JSON state diff inspection modal. Timestamp (UTC), Actor name and role, Action type, Affected entity type & ID, IP address, Summary description, Expandable JSON diff (`before` vs. `after`).
* **User Actions:** Filter by entity/actor/date, click event row to open side-by-side JSON state diff dialog, export audit report.
* **Interaction States:**
  * *Loading State:* High-density table displays 10 shimmer skeleton rows.
  * *Empty State:* "No audit log entries match your filter criteria."
  * *Success State:* Paginated table populated with chronological immutable records.
  * *Error State:* Error banner if query fails due to invalid date range parameters.
* **Responsive Behavior:** Table scrolls horizontally on mobile with sticky timestamp and action badge columns.
* **Acceptance Criteria:**
  1. Read-only ledger; no UI or API exists to modify or delete audit entries.
  2. All verification decisions, rejections, revisions, and target edits appear with accurate before/after states.
  3. Paginated efficiently with 50 entries per page.
