export type ActivityStatus = "PENDING" | "VERIFIED" | "REJECTED";

export type RejectionReasonCode =
  | "INSUFFICIENT_EVIDENCE"
  | "COORDINATES_MISMATCH"
  | "INCORRECT_UNIT_OR_QUANTITY"
  | "DUPLICATE_SUBMISSION"
  | "DATA_ENTRY_ERROR";

export interface EvidenceFile {
  id: string;
  activity_id: string;
  revision_id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  download_url: string;
  uploaded_at: string;
}

export interface ActivityRevision {
  id: string;
  activity_id: string;
  revision_number: number;
  quantity: string | number;
  activity_date: string;
  latitude: number | null;
  longitude: number | null;
  gps_accuracy_meters: number | null;
  field_notes: string | null;
  status: ActivityStatus;
  is_active_ledger_entry: boolean;
  verifier_id: string | null;
  verifier_name: string | null;
  verified_at: string | null;
  rejection_reason_code: string | null;
  review_notes: string | null;
  created_at: string;
  evidence_files: EvidenceFile[];
}

export interface FieldActivity {
  id: string;
  project_id: string;
  project_name: string | null;
  project_code: string | null;
  created_by_id: string;
  created_by_name: string | null;
  metric_code: string;
  unit: string;
  is_archived: boolean;
  current_revision_id: string | null;
  created_at: string;
  updated_at: string;
  current_revision: ActivityRevision | null;
  active_ledger_revision: ActivityRevision | null;
  active_verified_quantity: string | number;
  net_pending_adjustment: string | number | null;
  revisions_count: number;
  revisions?: ActivityRevision[];
}

export interface VerificationQueueItem {
  revision_id: string;
  activity_id: string;
  project_id: string;
  project_name: string;
  project_code: string;
  creator_id: string;
  creator_name: string;
  metric_code: string;
  unit: string;
  quantity: string | number;
  activity_date: string;
  latitude: number | null;
  longitude: number | null;
  gps_accuracy_meters: number | null;
  field_notes: string | null;
  revision_number: number;
  is_amendment: boolean;
  previously_verified_quantity: string | number | null;
  net_adjustment: string | number | null;
  evidence_files: EvidenceFile[];
  created_at: string;
  can_verify: boolean;
}

export interface VerificationDecisionPayload {
  decision: "VERIFIED" | "REJECTED" | "APPROVED";
  rejection_reason_code?: string;
  review_notes?: string;
}

export interface VerificationDecisionResponse {
  revision_id: string;
  activity_id: string;
  status: string;
  is_active_ledger_entry: boolean;
  verifier_id: string;
  verifier_name: string | null;
  verified_at: string;
  review_notes: string | null;
  rejection_reason_code: string | null;
  project_verified_total_recalculated: string | number;
}
