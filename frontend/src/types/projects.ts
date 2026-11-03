export type ProjectStatus = "DRAFT" | "ACTIVE" | "COMPLETED" | "ARCHIVED";

export interface GeoJsonPolygon {
  type: "Polygon";
  coordinates: number[][][]; // [ [ [lng, lat], ... ] ]
}

export interface Project {
  id: string;
  name: string;
  code: string;
  description: string | null;
  status: ProjectStatus;
  latitude: number;
  longitude: number;
  boundary_geojson: GeoJsonPolygon | null;
  created_at: string;
  updated_at: string;
  targets_count: number;
  team_count: number;
}

export interface ProjectDetail extends Project {
  targets: ProjectTarget[];
  assignments: ProjectAssignment[];
}

export interface ProjectCreateInput {
  name: string;
  code?: string;
  description?: string;
  status?: ProjectStatus;
  latitude: number;
  longitude: number;
  boundary_geojson?: GeoJsonPolygon | null;
}

export interface ProjectUpdateInput {
  name?: string;
  description?: string;
  status?: ProjectStatus;
  latitude?: number;
  longitude?: number;
  boundary_geojson?: GeoJsonPolygon | null;
}

export interface ProjectTarget {
  id: string;
  project_id: string;
  metric_code: string;
  display_name: string;
  category: string;
  dimension: string;
  canonical_unit: string;
  target_quantity: number;
  target_unit: string;
  target_date: string;
  milestone_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectTargetCreateInput {
  metric_code: string;
  target_quantity: number;
  target_unit: string;
  target_date: string;
}

export interface ProjectTargetUpdateInput {
  target_quantity?: number;
  target_unit?: string;
  target_date?: string;
}

export interface ProjectAssignment {
  id: string;
  project_id: string;
  user_id: string;
  assigned_role: "PROJECT_MANAGER" | "FIELD_OFFICER";
  assigned_at: string;
  user_email?: string;
  user_full_name?: string;
  user_system_role?: string;
  user_is_active?: boolean;
}

export interface ProjectAssignmentCreateInput {
  user_id: string;
  assigned_role: "PROJECT_MANAGER" | "FIELD_OFFICER";
}

export interface MetricDefinition {
  metric_code: string;
  display_name: string;
  category: string;
  dimension: string;
  canonical_unit: string;
  supported_units: string[];
  conversion_factors_to_base: Record<string, number>;
  aggregation_eligible: boolean;
  methodology_summary: string;
}
