/**
 * VANA — Audit History & Immutability Ledger Domain Types
 * Defines canonical data contracts for cryptographic audit logs, verification histories,
 * and SHA-256 chain verification reports.
 */

export interface AuditLog {
  id: string;
  sequence_number: number;
  actor_id: string | null;
  project_id: string | null;
  action_type: string;
  entity_type: string;
  entity_id: string;
  previous_state: Record<string, any> | null;
  new_state: Record<string, any> | null;
  canonical_payload: Record<string, any>;
  previous_hash: string;
  current_hash: string;
  hash_version: number;
  correlation_id: string | null;
  is_backfilled: boolean;
  ip_address: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AuditVerificationItem {
  sequence_number: number;
  event_id: string;
  action_type: string;
  entity_type: string;
  activity_id: string | null;
  revision_id: string | null;
  revision_number: number | null;
  project_id: string | null;
  actor_id: string | null;
  verifier_id: string | null;
  status: string | null;
  verified_quantity: number | null;
  rejection_reason_code: string | null;
  review_notes: string | null;
  current_hash: string;
  previous_hash: string;
  created_at: string;
}

export interface AuditVerificationHistoryResponse {
  items: AuditVerificationItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AuditVerificationError {
  sequence_number: number | null;
  event_id: string | null;
  error_type: string;
  message: string;
  expected: string | null;
  actual: string | null;
}

export interface AuditChainVerificationResponse {
  is_valid: boolean;
  status: "VALID" | "COMPROMISED" | "EMPTY" | string;
  total_events_checked: number;
  chain_head_sequence: number;
  chain_head_hash: string;
  last_verified_sequence: number | null;
  first_failure_sequence: number | null;
  failure_category: string | null;
  errors: AuditVerificationError[];
  verified_at: string;
  disclaimer: string;
}

export interface AuditEventFilterParams {
  page?: number;
  page_size?: number;
  action_type?: string;
  actor_id?: string;
  project_id?: string;
  entity_type?: string;
  entity_id?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
}

export interface AuditVerificationFilterParams {
  page?: number;
  page_size?: number;
  activity_id?: string;
  project_id?: string;
  from_date?: string;
  to_date?: string;
}

export interface AuditVerifyChainRequest {
  from_sequence?: number;
  to_sequence?: number;
}

export type AuditEntityCategory =
  | "project"
  | "environmental_target"
  | "project_assignment"
  | "field_activity"
  | "activity_revision"
  | "evidence_file"
  | "field_inspection"
  | "maintenance_task"
  | "survival_observation";
