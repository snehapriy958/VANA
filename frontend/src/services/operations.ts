import { apiClient } from "./apiClient";
import {
  FieldActivity,
  VerificationDecisionPayload,
  VerificationDecisionResponse,
  VerificationQueueItem,
} from "../types/operations";

export const operationsService = {
  /**
   * Lists field activities with optional filtering by project, status, and metric.
   */
  async getActivities(params?: {
    projectId?: string;
    status?: string;
    metricCode?: string;
    isArchived?: boolean;
  }): Promise<FieldActivity[]> {
    const query = new URLSearchParams();
    if (params?.projectId) query.append("project_id", params.projectId);
    if (params?.status) query.append("status", params.status);
    if (params?.metricCode) query.append("metric_code", params.metricCode);
    if (params?.isArchived !== undefined) {
      query.append("is_archived", String(params.isArchived));
    }

    const response = await apiClient.get<FieldActivity[]>(
      `/operations/activities${query.toString() ? `?${query.toString()}` : ""}`
    );
    return response.data;
  },

  /**
   * Retrieves an activity's details, full revision lineage, and attached evidence.
   */
  async getActivity(activityId: string): Promise<FieldActivity> {
    const response = await apiClient.get<FieldActivity>(`/operations/activities/${activityId}`);
    return response.data;
  },

  /**
   * Submits a new field activity report with optional photo evidence (multipart/form-data).
   */
  async createActivity(formData: FormData): Promise<FieldActivity> {
    const response = await apiClient.post<FieldActivity>("/operations/activities", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  /**
   * Submits an amendment or correction revision for an activity.
   */
  async amendActivity(activityId: string, formData: FormData): Promise<FieldActivity> {
    const response = await apiClient.post<FieldActivity>(
      `/operations/activities/${activityId}/revisions`,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return response.data;
  },

  /**
   * Soft-deletes/archives an activity and deactivates active ledger entries.
   */
  async archiveActivity(activityId: string): Promise<{ activity_id: string; status: string }> {
    const response = await apiClient.delete<{ activity_id: string; status: string }>(
      `/operations/activities/${activityId}`
    );
    return response.data;
  },

  /**
   * Fetches pending activity revisions awaiting review in the Verification Centre.
   */
  async getVerificationQueue(): Promise<VerificationQueueItem[]> {
    const response = await apiClient.get<VerificationQueueItem[]>("/verification/queue");
    return response.data;
  },

  /**
   * Records a verification decision (APPROVE / REJECT) on a pending revision.
   */
  async submitVerificationDecision(
    revisionId: string,
    payload: VerificationDecisionPayload
  ): Promise<VerificationDecisionResponse> {
    const response = await apiClient.post<VerificationDecisionResponse>(
      `/verification/revisions/${revisionId}/decision`,
      payload
    );
    return response.data;
  },

  /**
   * Constructs the relative download / streaming URL for an evidence file.
   */
  getEvidenceFileUrl(evidenceId: string): string {
    return `/api/v1/operations/evidence/${evidenceId}`;
  },
};
