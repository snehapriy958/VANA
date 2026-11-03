/**
 * VANA — Environmental Impact Analytics & Dashboard Types
 */

export interface MetricProgressSummary {
  metric_code: string;
  display_name: string;
  category: string;
  canonical_unit: string;
  total_verified_quantity: string | number;
  total_pending_adjustment: string | number;
  total_target_quantity: string | number | null;
  overall_achievement_percentage: number | null;
  active_projects_count: number;
  activities_count: number;
}

export interface AttentionProjectItem {
  project_id: string;
  project_name: string;
  project_code: string;
  status: string;
  reason: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  pending_verifications_count: number;
  days_until_deadline: number | null;
  lowest_target_achievement_percentage: number | null;
}

export interface TargetProgressItem {
  target_id: string;
  metric_code: string;
  metric_name: string;
  target_quantity: string | number;
  target_unit: string;
  verified_quantity: string | number;
  net_pending_adjustment: string | number;
  remaining_quantity: string | number;
  achievement_percentage: number;
  target_date: string;
  milestone_id: string | null;
}

export interface DashboardOverviewResponse {
  total_projects: number;
  active_projects: number;
  completed_projects: number;
  draft_projects: number;
  total_pending_verifications: number;
  metric_achievements: MetricProgressSummary[];
  attention_projects: AttentionProjectItem[];
  user_role: string;
  is_portfolio_wide: boolean;
}

export interface ProjectProgressItem {
  id: string;
  name: string;
  code: string;
  status: string;
  description: string | null;
  latitude: number | null;
  longitude: number | null;
  targets: TargetProgressItem[];
  overall_achievement_percentage: number | null;
  pending_verifications_count: number;
  last_activity_date: string | null;
  has_coordinates: boolean;
}

export interface DashboardProjectsResponse {
  total: number;
  projects: ProjectProgressItem[];
}

export interface RecentActivityItem {
  id: string;
  event_type: "SUBMISSION" | "VERIFICATION" | "REJECTION" | "AMENDMENT" | "PROJECT_UPDATE";
  title: string;
  description: string;
  timestamp: string;
  actor_id: string | null;
  actor_name: string | null;
  project_id: string;
  project_name: string;
  project_code: string;
  metric_code: string | null;
  quantity: string | number | null;
  unit: string | null;
  status: string | null;
}

export interface ProjectImpactDetailResponse {
  project_id: string;
  project_name: string;
  project_code: string;
  project_status: string;
  description: string | null;
  latitude: number | null;
  longitude: number | null;
  boundary_geojson: Record<string, unknown> | null;
  targets: TargetProgressItem[];
  overall_achievement_percentage: number | null;
  activities_summary: {
    total_activities_count: number;
    verified_active_revisions_count: number;
    pending_revisions_count: number;
    current_rejected_revisions_count: number;
    archived_activities_count: number;
  };
  historical_rejected_count: number;
  last_activity_date: string | null;
}

export interface ProjectTrendPoint {
  date: string; // YYYY-MM-DD
  metric_code: string;
  metric_name: string;
  unit: string;
  period_quantity: string | number;
  cumulative_quantity: string | number;
  activities_count: number;
}

export interface ProjectTrendsResponse {
  project_id: string;
  project_name: string;
  trends: ProjectTrendPoint[];
  available_metrics: string[];
}

export interface MetricCatalogSummaryItem {
  metric_code: string;
  display_name: string;
  category: string;
  canonical_unit: string;
  supported_units: string[];
  total_verified_quantity: string | number;
  total_pending_adjustment: string | number;
  total_target_quantity: string | number | null;
  overall_achievement_percentage: number | null;
  projects_count: number;
}
