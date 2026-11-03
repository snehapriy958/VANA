# VANA — Structural Wireframes (Desktop & Mobile)

This document provides architectural wireframes for all 10 core screens of the VANA platform across Desktop (1440px) and Mobile (375px) viewports.

---

## 1. Login Screen Wireframe (`/login`)

### Desktop Viewport (1440px)
```
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [ Left Hero Banner: 45% Width - Forest Green ]  │ [ Right Form: 55% Width - Warm Ivory Canvas ]    │
│                                                 │                                                 │
│   V A N A                                       │                 Sign In                         │
│   Environmental Operations & Impact             │                 Access your VANA workspace      │
│   Intelligence Platform                         │                                                 │
│                                                 │                 Email Address                   │
│   "Ground Truth First."                         │                 [ user@akshayavana.com        ] │
│                                                 │                                                 │
│   • Verifiable field data                       │                 Password                        │
│   • Zero synthetic multipliers                  │                 [ ••••••••••••••••••      (o) ] │
│   • Auditable ecological ledgers                │                                                 │
│                                                 │                 [ Sign In to Platform         ] │
│                                                 │                                                 │
│   Akshaya Vana Climate Ventures © 2026          │                 Need access? Contact your Admin │
└─────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
```

### Mobile Viewport (375px)
```
┌───────────────────────────────────────┐
│ V A N A                               │
│ Akshaya Vana Operations               │
├───────────────────────────────────────┤
│                                       │
│ Sign In                               │
│ Access your operational workspace     │
│                                       │
│ Email Address                         │
│ [ officer@akshayavana.com           ] │
│                                       │
│ Password                              │
│ [ ••••••••••••••••••••••••••    (o) ] │
│                                       │
│ [ Sign In to Platform               ] │
│                                       │
│ Need access? Contact your admin       │
│                                       │
└───────────────────────────────────────┘
```

---

## 2. Organization Dashboard Wireframe (`/dashboard`)

### Desktop Viewport (1440px)
```
┌───────────┬───────────────────────────────────────────────────────────────────────────────────────┐
│ VANA      │ Dashboard Overview                                    [ Active Org: Akshaya Vana v ]  │
├───────────┼───────────────────────────────────────────────────────────────────────────────────────┤
│ Dashboard*│ ┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐     │
│ Projects  │ │ Active Projects  │ Verified Trees   │ Restored Area    │ Pending Review   │     │
│ Map       │ │ 12 Projects      │ 142,500 Trees    │ 840 Hectares     │ 18 Submissions   │     │
│ Operations│ │ +2 this quarter  │ 74% of target    │ 62% of target    │ Action Required  │     │
│ Verify (18│ └──────────────────┴──────────────────┴──────────────────┴──────────────────┘     │
│ Analytics │                                                                                       │
│ Team      │ ┌──────────────────────────────────────────────┐ ┌──────────────────────────────────┐ │
│ Audit     │ │ Portfolio Progress Balance Sheet             │ │ Living Earth Geospatial Overview │ │
│           │ │                                              │ │ ┌──────────────────────────────┐ │ │
│           │ │ Mangrove Delta Project                       │ │ │ Map Canvas                   │ │ │
│           │ │ [██████████████████░░░░░░] 74% (74k/100k)   │ │ │  o Project Pin               │ │ │
│           │ │                                              │ │ │     o Activity Hotspot       │ │ │
│           │ │ Western Ghats Afforestation                  │ │ │                              │ │ │
│           │ │ [████████████░░░░░░░░░░░░] 48% (48k/100k)   │ │ └──────────────────────────────┘ │ │
│           │ │                                              │ │ [ View Full Living Earth Map ]   │ │
│           │ └──────────────────────────────────────────────┘ └──────────────────────────────────┘ │
│           │                                                                                       │
│           │ Recent Verification Velocity & Activity Stream                                        │
│           │ ┌────────────┬─────────────────────────────┬─────────────────┬──────────┬───────────┐ │
│           │ │ Time (UTC) │ Project                     │ Activity Code   │ Quantity │ Status    │ │
│           │ ├────────────┼─────────────────────────────┼─────────────────┼──────────┼───────────┤ │
│ [Profile] │ │ 10:42 AM   │ Sundarbans Mangrove Delta   │ TREES_PLANTED   │ 250 Tr   │ APPROVED  │ │
│ [Logout]  │ │ 09:15 AM   │ Nilgiri Highlands Shola     │ AREA_RESTORED   │ 4.5 Ha   │ PENDING   │ │
└───────────┴─┴────────────┴─────────────────────────────┴─────────────────┴──────────┴───────────┴─┘
```

### Mobile Viewport (375px)
```
┌───────────────────────────────────────┐
│ VANA  [Akshaya Vana]             (18) │
├───────────────────────────────────────┤
│ Organization Summary                  │
│                                       │
│ ┌───────────────────────────────────┐ │
│ │ 142,500 Verified Trees            │ │
│ │ 74% of Portfolio Target           │ │
│ └───────────────────────────────────┘ │
│ ┌───────────────────────────────────┐ │
│ │ 840 Hectares Restored             │ │
│ │ 62% of Portfolio Target           │ │
│ └───────────────────────────────────┘ │
│ ┌───────────────────────────────────┐ │
│ │ 18 Pending Submissions            │ │
│ │ [ Go to Verification Queue ]      │ │
│ └───────────────────────────────────┘ │
│                                       │
│ Active Projects                       │
│ • Sundarbans Delta (74% verified)     │
│ • Western Ghats (48% verified)        │
│                                       │
├───────────────────────────────────────┤
│ [Home*]  [Projects]  [Map]  [Verify]  │
└───────────────────────────────────────┘
```

---

## 3. Project Workspace Wireframe (`/projects/:id`)

### Desktop Viewport (1440px)
```
┌───────────┬───────────────────────────────────────────────────────────────────────────────────────┐
│ VANA      │ Projects > Sundarbans Mangrove Conservation                                           │
├───────────┼───────────────────────────────────────────────────────────────────────────────────────┤
│ Dashboard │ Sundarbans Mangrove Conservation  [ ACTIVE ]               [ Edit Project ] [ Submit ]│
│ Projects* │ Coordinates: 21.9497° N, 89.1833° E | Biome: Coastal Mangrove | Lead PM: S. Sen       │
│ Map       ├───────────────────────────────────────────────────────────────────────────────────────┤
│ Operations│ [ Overview* ]   [ Targets & Balance Sheet ]   [ Field Activities ]   [ Team Roster ]  │
│ Verify    ├───────────────────────────────────────────────────────────────────────────────────────┤
│ Analytics │ Target vs. Verified Achievement Balance Sheet                                         │
│ Team      │ ┌──────────────────────────────────────────┬────────────────────────────────────────┐ │
│ Audit     │ │ Target: 100,000 Trees Planted            │ Target: 250 Hectares Restored          │ │
│           │ │ • Verified Achievement: 64,500 trees     │ • Verified Achievement: 180 hectares   │ │
│           │ │ • Current Pending:       4,200 trees     │ • Current Pending:       15 hectares   │ │
│           │ │ • Current Rejected:        800 trees     │ • Current Rejected:        5 hectares   │ │
│           │ │ Progress: [█████████████░░░░░] 64.5%     │ Progress: [██████████████░░░░] 72.0%   │ │
│           │ └──────────────────────────────────────────┴────────────────────────────────────────┘ │
│           │                                                                                       │
│           │ Localized Boundary Map & Recent Field Records                                         │
│           │ ┌───────────────────────────┬───────────────────────────────────────────────────────┐ │
│           │ │ Boundary Canvas           │ Date       Officer     Metric Code   Qty     Status   │ │
│           │ │ ┌───────────────────────┐ │ 2026-11-01 R. Ghosh    TREES_PLANTED 400 Tr  APPROVED │ │
│           │ │ │ /---------------\     │ │ 2026-11-01 M. Roy      TREES_PLANTED 250 Tr  PENDING  │ │
│           │ │ │ |  Polygon Zone |  *  │ │ 2026-10-31 P. Sen      AREA_RESTORED 2.0 Ha  APPROVED │ │
│           │ │ │ \---------------/     │ │                                                       │ │
│           │ │ └───────────────────────┘ │ [ View All 142 Activities ]                           │ │
└───────────┴─┴───────────────────────────┴───────────────────────────────────────────────────────┴─┘
```

---

## 4. Field Operations Reporting Wireframe (`/operations/submit`)

### Mobile Viewport (375px) — Primary Persona Interface
```
┌───────────────────────────────────────┐
│ VANA                  Step 1 of 3     │
│ Record Field Activity                 │
├───────────────────────────────────────┤
│ Select Assigned Project               │
│ [ Sundarbans Mangrove Conservation  v]│
│                                       │
│ Environmental Metric Code             │
│ [ TREES_PLANTED                     v]│
│                                       │
│ Measurement Unit                      │
│ (•) trees      ( ) saplings           │
│                                       │
│ Quantity Recorded                     │
│ [ 250                               ] │
│                                       │
│ Activity Date                         │
│ [ 2026-11-02                        ] │
│                                       │
│ GPS Location                          │
│ [ 21.9512° N, 89.1840° E            ] │
│ Accuracy: ±4 meters [ Refresh GPS ]   │
│                                       │
│ Photographic Evidence (Max 3)         │
│ ┌─────────┐ ┌─────────┐ ┌───────────┐ │
│ │ [Photo] │ │ [Photo] │ │ [ + Add ] │ │
│ └─────────┘ └─────────┘ └───────────┘ │
│                                       │
│ Field Notes                           │
│ [ Planted Avicennia marina along   ]  │
│ [ tidal mudflat section 4B.        ]  │
│                                       │
│ [ Submit for Verification           ] │
├───────────────────────────────────────┤
│ [Submit*]  [My Projects]  [Map] [User]│
└───────────────────────────────────────┘
```

---

## 5. Verification Centre Wireframe (`/verification`)

### Desktop Viewport (1440px) — Dual-Pane Triage
```
┌───────────┬───────────────────────────────────────────────────────────────────────────────────────┐
│ VANA      │ Activity Verification Centre [ 18 Pending Submissions ]                               │
├───────────┼───────────────────────────────────────────────────┬───────────────────────────────────┤
│ Dashboard │ Pending Submissions Queue (Left Pane: 40%)        │ Evidence Inspection (Right: 60%)  │
│ Projects  ├───────────────────────────────────────────────────┼───────────────────────────────────┤
│ Map       │ Filter: [ All Assigned Projects v ]               │ Activity Submission #ACT-9041     │
│ Operations│                                                   │ Project: Sundarbans Conservation  │
│ Verify*   │ ► #ACT-9041 • 250 Trees Planted                   │ Submitter: Rajesh Ghosh (Officer) │
│ Analytics │   Sundarbans Delta | R. Ghosh | Today 09:30       │ Date: 2026-11-02 09:30 UTC        │
│ Team      │                                                   ├───────────────────────────────────┤
│ Audit     │   #ACT-9040 • 4.5 Hectares Restored               │ Photographic Evidence:            │
│           │   Nilgiri Highlands | K. Varma | Today 08:15      │ ┌───────────────────────────────┐ │
│           │                                                   │ │ [ High Resolution Field Photo │ │
│           │   #ACT-9038 • 150 Trees Planted (Rev 2)           │ │   Showing Sapling Rows with   │ │
│           │   Sundarbans Delta | M. Roy | Yesterday           │ │   Physical Tag Markers ]      │ │
│           │                                                   │ └───────────────────────────────┘ │
│           │   #ACT-9035 • 10,000 Liters Water Harvested       │ Verified GPS: 21.9512° N, 89.184° │
│           │   Western Ghats | D. Sharma | 2 days ago          │ Accuracy: ±4m (Inside Zone Poly)  │
│           │                                                   ├───────────────────────────────────┤
│           │                                                   │ Actions (Anti-Self Gate Checked): │
│           │                                                   │ [ Reject Submission ]  [ Approve ]│
└───────────┴───────────────────────────────────────────────────┴───────────────────────────────────┘
```

---

## 6. Living Earth Interactive Map Wireframe (`/map`)

### Desktop Viewport (1440px)
```
┌───────────┬───────────────────────────────────────────────────────────────────────────────────────┐
│ VANA      │ [ Search Projects, Sites, or Coordinates...     ]  Layers: [x] Projects [x] Activities│
├───────────┼───────────────────────────────────────────────────────────────────────────────────────┤
│ Dashboard │ ┌──────────────────────────────────────────────────────────────┐ ┌──────────────────┐ │
│ Projects  │ │ React Leaflet Map Canvas                                     │ │ Slide-Over Drawer│ │
│ Map*      │ │                                                              │ │                  │ │
│ Operations│ │           (O) Project Marker                                 │ │ Sundarbans Delta │ │
│ Verify    │ │               /-------------------\                          │ │ 21.949°N, 89.183°│ │
│ Analytics │ │               | Project Boundary  |                          │ │                  │ │
│ Team      │ │               |   * Approved Pin  |                          │ │ Verified Total:  │ │
│ Audit     │ │               |   * Pending Pin   |                          │ │ 64,500 Trees     │ │
│           │ │               \-------------------/                          │ │                  │ │
│           │ │                                                              │ │ Recent Activity: │ │
│           │ │     (O) Project Marker                                       │ │ #ACT-9041        │ │
│           │ │                                                              │ │ 250 Trees        │ │
│           │ │                                                              │ │ [ Open Project ] │ │
│           │ └──────────────────────────────────────────────────────────────┘ └──────────────────┘ │
└───────────┴───────────────────────────────────────────────────────────────────────────────────────┘
```
