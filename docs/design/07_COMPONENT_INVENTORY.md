# VANA — Reusable Component Inventory

This catalog specifies the core reusable UI components built on shadcn/ui and Tailwind CSS for the VANA platform.

---

## 1. Component Categories

### 1.1 Form Controls & Inputs

| Component Name | Base Library | Props & Configuration | Usage & Semantic Constraints |
|---|---|---|---|
| `MetricCodeSelect` | Radix Select / shadcn | `value: MetricCode`, `onChange`, `disabled?: boolean` | Dropdown rendering approved metric codes with humanized category tags. |
| `UnitRadioGroup` | Radix Radio / shadcn | `metricCode: MetricCode`, `selectedUnit: string` | Constrained unit picker allowing only valid units for the selected metric code. |
| `QuantityInput` | HTML5 input / shadcn | `min: 0.01`, `step: "any"`, `unitLabel: string` | Numeric input with inline trailing unit adornment and tabular font formatting. |
| `GPSCaptureButton` | Custom / Lucide React | `onCapture: (lat, lng, acc) => void` | Triggers Geolocation API; displays live accuracy radius badge (green $\le 15\text{m}$, red $> 25\text{m}$). |
| `EvidenceDropzone` | Custom / React Hook Form | `maxFiles: 3`, `maxSizeBytes: 10MB`, `accept: images` | Drag-and-drop file attachment area with thumbnail generation and remove actions. |

---

### 1.2 Data Presentation & Metrics

| Component Name | Base Library | Props & Configuration | Usage & Semantic Constraints |
|---|---|---|---|
| `MetricCard` | shadcn Card | `title`, `value`, `unit`, `trend?: string`, `statusPill` | Primary executive stat card featuring Manrope bold numbers and hairline borders. |
| `BalanceProgressBar` | Radix Progress / shadcn | `verified: number`, `target: number`, `pending?: number` | Dual-tone stacked progress bar showing verified progress (Forest Green) and pending claims (Earth Gold). |
| `StatusBadge` | shadcn Badge | `status: "APPROVED" | "PENDING" | "REJECTED"` | Semantic status pill with strict VANA color mapping (Approved: Green, Pending: Gold, Rejected: Crimson). |
| `DataTable` | TanStack Table | `columns`, `data`, `sorting`, `pagination` | High-density data table with tabular number formatting and sticky column headers. |
| `JSONDiffViewer` | Custom component | `previousState: object`, `newState: object` | Side-by-side or unified colored JSON state delta viewer used in the Audit History modal. |

---

### 1.3 Split-Screen Triage & Queue

| Component Name | Structure | Key Capabilities |
|---|---|---|
| `TriageQueueList` | Left Pane Container (40%) | Virtualized list of pending activity cards with age indicators, submitter thumbnails, and active item highlight. |
| `InspectionDetailPane` | Right Pane Container (60%) | Dual-section layout: Top evidence photo lightbox (zoom/pan) and bottom coordinate sanity check mini-map. |
| `AntiSelfVerificationGate` | Logic Wrapper Component | Disables approval/rejection triggers if `current_user.id == activity.created_by_id`, displaying an explanatory warning. |
| `RejectionReasonModal` | Radix Dialog / shadcn | Mandatory modal demanding `rejection_reason_code` selection and review commentary before rejecting. |

---

### 1.4 Geospatial & Map Components

| Component Name | Base Library | Props & Configuration |
|---|---|---|
| `LivingEarthCanvas` | React Leaflet | `center: [lat, lng]`, `zoom: number`, `children: ReactNode` | Main map canvas with custom CartoDB Positron or OpenStreetMap tiles. |
| `ProjectPolygonLayer`| React Leaflet `GeoJSON` | `data: GeoJsonObject`, `color: "#183D32"`, `fillOpacity: 0.15` | Renders the optional project boundary polygon with Forest Green hairline borders. |
| `ActivityMarkerPin` | Leaflet `DivIcon` | `status: ActivityStatus`, `quantity: number`, `onClick` | Custom circular marker pin color-coded by verification status with hover preview tooltip. |
| `MapInspectionDrawer`| Radix Sheet / shadcn | `isOpen: boolean`, `activity: ActivityDetail`, `onClose` | Slide-over inspection drawer on desktop; swipeable bottom sheet on mobile. |
