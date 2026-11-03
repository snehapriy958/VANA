# VANA — Information Architecture & Navigation Schema

This document details the navigation architecture, URL routing schema, role-based access distribution, and page hierarchy for VANA.

---

## 1. Global Sitemap & Route Hierarchy

```
VANA Root (/)
├── /login                                   [Public / Unauthenticated]
├── /dashboard                               [ADMIN, PROJECT_MANAGER]
├── /projects                                [ADMIN, PROJECT_MANAGER, FIELD_OFFICER (assigned)]
│   ├── /projects/new                        [ADMIN only]
│   └── /projects/:projectId                 [ADMIN, PM (assigned), FO (assigned)]
│       ├── /projects/:projectId/overview
│       ├── /projects/:projectId/targets
│       ├── /projects/:projectId/activities
│       └── /projects/:projectId/team
├── /map                                     [All Roles]
│   └── ?project_id=:id&status=:status
├── /operations                              [FIELD_OFFICER, PM, ADMIN]
│   ├── /operations/submit                   [Mobile-First Activity Submission]
│   └── /operations/history                  [Submission Log & Revisions]
├── /verification                            [ADMIN, PROJECT_MANAGER (assigned)]
│   └── /verification/:activityId            [Dual-Pane Review & Triage]
├── /analytics                               [ADMIN, PROJECT_MANAGER (assigned)]
│   └── ?project_id=:id&metric_code=:code
├── /team                                    [ADMIN, PROJECT_MANAGER (assigned)]
│   └── ?project_id=:id
└── /audit                                   [ADMIN only]
    └── ?entity_type=:type&actor_id=:id
```

---

## 2. Role-Based Screen Access Matrix

| Route Path | Screen Name | ADMIN | PROJECT_MANAGER | FIELD_OFFICER |
|---|---|:---:|:---:|:---:|
| `/login` | Authentication Portal | Public | Public | Public |
| `/dashboard` | Executive Organization Dashboard | Full View (Org-Wide) | Scoped View (Assigned Projects) | Redirected $\to$ `/operations` |
| `/projects` | Project Portfolio Explorer | All Projects | Assigned Projects | Assigned Projects |
| `/projects/new` | Create Project Wizard | Full Access | No Access (403) | No Access (403) |
| `/projects/:id` | Project Workspace Hub | Full Access | Full Access (Assigned) | Read-Only (Assigned) |
| `/map` | Living Earth Interactive Map | All Projects & Pins | Assigned Projects & Pins | Assigned Projects & Pins |
| `/operations` | Field Operations Roster | Full Access | Full Access | Assigned Operations Hub |
| `/operations/submit`| Field Activity Submission | Full Access | Allowed (Assigned) | Primary Daily Screen |
| `/verification` | Verification Centre Triage | All Projects Queue | Assigned Projects Queue | No Access (403) |
| `/analytics` | Impact Analytics Engine | Org-Wide Aggregates | Assigned Aggregates | No Access (403) |
| `/team` | User & Team Allocations | Full CRUD | View & Assign (Assigned) | No Access (403) |
| `/audit` | System-Wide Audit History | Full Access | No Access (403) | No Access (403) |

---

## 3. Global Navigation Patterns

### 3.1 Desktop Navigation (Sidebar)
* **Width:** Fixed 260px desktop sidebar, pinned to the left edge.
* **Header:** VANA logotype (Forest Green on Ivory) + Active Organization name ("Akshaya Vana").
* **Primary Navigation Links:**
  * Dashboard (with live pending verification counter badge)
  * Projects
  * Living Earth Map
  * Field Operations
  * Verification Centre (badge pill displaying unreviewed queue count)
  * Impact Analytics
  * Team Management
  * Audit History (Admin only)
* **Footer:** Active user profile pill (Name, Role badge, Project count), and Logout button.

### 3.2 Mobile Navigation (Top Bar + Bottom Tab Bar)
* **Top App Bar (56px):**
  * Left: VANA brand mark + current page title.
  * Right: User avatar thumbnail + notification bell.
* **Bottom Tab Bar (64px):**
  * Dynamic based on role:
    * **Field Officer:** `[Operations (Submit)]`, `[My Projects]`, `[Map]`, `[Profile]`
    * **Project Manager:** `[Dashboard]`, `[Verification (Queue)]`, `[Projects]`, `[Map]`
    * **Admin:** `[Dashboard]`, `[Verification]`, `[Projects]`, `[More (Team, Audit, Analytics)]`

### 3.3 Breadcrumb Traversal
Deeply nested views (e.g. `/projects/:projectId/activities`) provide strict hierarchical breadcrumb links:
`Projects` $>$ `Sundarbans Mangrove Restoration` $>$ `Activities` $>$ `Submission #4092`
All breadcrumb segments are interactive and reflect accurate routing state.

---

## 4. Query Parameter State Specifications

To ensure views are shareable, bookmarkable, and refresh-safe, state is persisted in URL query parameters:

| Parameter Key | Permitted Values | Affected Views | Purpose |
|---|---|---|---|
| `project_id` | UUID | `/map`, `/verification`, `/analytics`, `/team` | Filters view to a specific project context. |
| `metric_code` | Enum string (e.g., `TREES_PLANTED`) | `/analytics`, `/projects/:id` | Isolates charts to a specific dimensional metric. |
| `status` | `PENDING`, `APPROVED`, `REJECTED`, `ALL` | `/verification`, `/operations`, `/projects/:id` | Filters queue and activity tables. |
| `time_range` | `7d`, `30d`, `90d`, `1y`, `all` | `/dashboard`, `/analytics` | Constrains time-series aggregate windows. |
| `page` / `page_size` | Integers (`page=1`, `page_size=25`) | All data tables and queues | Controls pagination offset. |
