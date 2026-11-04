/**
 * VANA Core Frontend Type Definitions
 */

export interface HealthStatus {
  status: "healthy" | "degraded" | "down";
  database: string;
  environment: string;
  platform: string;
  version?: string;
}

export type UserRole = "ADMIN" | "PROJECT_MANAGER" | "FIELD_OFFICER";

export type ActivityStatus = "PENDING" | "VERIFIED" | "REJECTED";

export interface ApiErrorResponse {
  detail?: {
    error_code?: string;
    message: string;
    field_errors?: Array<{ field: string; message: string }>;
  };
}

export * from "./monitoring";
export * from "./audit";
