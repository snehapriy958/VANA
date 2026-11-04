/**
 * VANA — Field Monitoring & Follow-up Management TypeScript Definitions
 * Strictly maps to backend FastAPI OpenAPI schemas and PostgreSQL domain models.
 */

// ============================================================================
// Enums and Literal Types
// ============================================================================

export type InspectionStatus = "SCHEDULED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";

export type InspectionType =
  | "ROUTINE"
  | "SURVIVAL_CHECK"
  | "MAINTENANCE_AUDIT"
  | "EMERGENCY";

export type CanopyCondition = "EXCELLENT" | "HEALTHY" | "STRESSED" | "CRITICAL";

export type SoilMoistureCondition =
  | "SATURATED"
  | "ADEQUATE"
  | "DRY"
  | "SEVERELY_PARCHED";

export type MaintenanceTaskStatus =
  | "TODO"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED";

export type MaintenanceTaskCategory =
  | "IRRIGATION"
  | "WEEDING"
  | "MULCHING"
  | "FENCING_REPAIR"
  | "REPLANTING_PREP"
  | "PEST_CONTROL"
  | "SOIL_ENRICHMENT"
  | "OTHER";

export type MaintenanceTaskPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";

export type SurvivalMethodology = "SAMPLE_PLOT" | "TRANSECT" | "FULL_CENSUS";

export type AlertType =
  | "OVERDUE_INSPECTION"
  | "UPCOMING_INSPECTION"
  | "OVERDUE_TASK";

export type AlertSeverity = "HIGH" | "MEDIUM" | "LOW";

// ============================================================================
// Field Inspection Entities & Requests
// ============================================================================

export interface InspectionAddendum {
  type: string;
  author_id: string;
  author_name: string;
  created_at: string;
  content: string;
}

export interface InspectionEvidence {
  id: string;
  inspection_id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  download_url: string;
  latitude?: number | null;
  longitude?: number | null;
  caption?: string | null;
  uploaded_at: string;
}

export interface FieldInspection {
  id: string;
  project_id: string;
  linked_activity_id?: string | null;
  scheduled_date: string;
  status: InspectionStatus;
  inspection_type: InspectionType;
  assigned_to_id?: string | null;
  completed_at?: string | null;
  findings?: string | null;
  vegetation_health_score?: number | null;
  canopy_condition?: CanopyCondition | null;
  soil_moisture_condition?: SoilMoistureCondition | null;
  threats_detected?: string[] | null;
  addenda: InspectionAddendum[];
  created_at: string;
  updated_at: string;
}

export interface InspectionCreateRequest {
  project_id: string;
  scheduled_date: string;
  inspection_type?: InspectionType;
  assigned_to_id?: string | null;
  linked_activity_id?: string | null;
}

export interface InspectionStartRequest {
  notes?: string | null;
}

export interface InspectionCompleteRequest {
  findings: string;
  vegetation_health_score?: number | null;
  canopy_condition?: CanopyCondition | null;
  soil_moisture_condition?: SoilMoistureCondition | null;
  threats_detected?: string[] | null;
}

export interface InspectionCancelRequest {
  cancellation_reason: string;
}

export interface InspectionAddendumCreate {
  content: string;
}

// ============================================================================
// Maintenance Task Entities & Requests
// ============================================================================

export interface MaintenanceTask {
  id: string;
  project_id: string;
  inspection_id?: string | null;
  activity_id?: string | null;
  title: string;
  description?: string | null;
  category: MaintenanceTaskCategory;
  priority: MaintenanceTaskPriority;
  status: MaintenanceTaskStatus;
  due_date: string;
  assigned_to_id?: string | null;
  completed_at?: string | null;
  completion_notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MaintenanceTaskCreateRequest {
  project_id: string;
  title: string;
  description?: string | null;
  category: MaintenanceTaskCategory;
  priority?: MaintenanceTaskPriority;
  due_date: string;
  assigned_to_id?: string | null;
  inspection_id?: string | null;
  activity_id?: string | null;
}

export interface TaskStartRequest {
  notes?: string | null;
}

export interface TaskCompleteRequest {
  completion_notes: string;
}

export interface TaskCancelRequest {
  cancellation_reason: string;
}

export interface TaskReopenRequest {
  justification: string;
}

// ============================================================================
// Survival Observation Entities & Requests
// ============================================================================

export interface SurvivalObservation {
  id: string;
  project_id: string;
  activity_id?: string | null;
  inspection_id?: string | null;
  plot_identifier: string;
  cohort_identifier: string;
  methodology: SurvivalMethodology | string;
  coverage_area_sqm?: number | null;
  observation_date: string;
  sample_size: number;
  alive_count: number;
  dead_count: number;
  unassessed_count: number;
  survival_rate: number | null;
  mortality_causes?: string[] | null;
  is_definitive: boolean;
  is_active: boolean;
  superseded_by_id?: string | null;
  correction_notes?: string | null;
  notes?: string | null;
  created_at: string;
}

export interface SurvivalObservationCreateRequest {
  project_id: string;
  plot_identifier: string;
  cohort_identifier: string;
  methodology?: SurvivalMethodology;
  coverage_area_sqm?: number | null;
  observation_date: string;
  sample_size: number;
  alive_count: number;
  dead_count: number;
  mortality_causes?: string[] | null;
  is_definitive?: boolean;
  activity_id?: string | null;
  inspection_id?: string | null;
  notes?: string | null;
}

export interface SurvivalObservationCorrectionRequest {
  sample_size: number;
  alive_count: number;
  dead_count: number;
  methodology?: SurvivalMethodology | null;
  coverage_area_sqm?: number | null;
  mortality_causes?: string[] | null;
  is_definitive?: boolean | null;
  notes?: string | null;
  correction_notes: string;
}

export interface SurvivalAnalytics {
  id: string;
  observation_date: string;
  methodology: string;
  sample_size: number;
  alive_count: number;
  dead_count: number;
  assessed_count: number;
  unassessed_count: number;
  survival_rate: number | null;
  is_definitive: boolean;
}

// ============================================================================
// Operational Alerts & Dashboard Summaries
// ============================================================================

export interface MonitoringAlert {
  alert_type: AlertType;
  severity: AlertSeverity;
  entity_id: string;
  project_id: string;
  title: string;
  due_date: string;
  details?: string | null;
}

export interface MonitoringAlertSummary {
  total_alerts: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  alerts: MonitoringAlert[];
}

export interface MonitoringDashboard {
  project_id?: string | null;
  total_inspections: number;
  scheduled_inspections: number;
  in_progress_inspections: number;
  completed_inspections: number;
  total_tasks: number;
  open_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  total_alerts: number;
  high_severity_alerts: number;
  latest_observations: SurvivalObservation[];
}

// ============================================================================
// Filter and Pagination Parameters
// ============================================================================

export interface InspectionFilterParams {
  project_id?: string;
  status?: InspectionStatus | string;
  assigned_to_id?: string;
  from_date?: string;
  to_date?: string;
  skip?: number;
  limit?: number;
}

export interface TaskFilterParams {
  project_id?: string;
  status?: MaintenanceTaskStatus | string;
  assigned_to_id?: string;
  priority?: MaintenanceTaskPriority | string;
  category?: MaintenanceTaskCategory | string;
  skip?: number;
  limit?: number;
}

export interface SurvivalFilterParams {
  project_id: string;
  plot_identifier?: string;
  cohort_identifier?: string;
  active_only?: boolean;
  skip?: number;
  limit?: number;
}

export type MonitoringFilterParams =
  | InspectionFilterParams
  | TaskFilterParams
  | SurvivalFilterParams;

export interface PaginatedMonitoringResponse<T> {
  items: T[];
  total?: number;
  skip: number;
  limit: number;
}
