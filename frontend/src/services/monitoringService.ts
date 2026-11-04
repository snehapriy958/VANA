/**
 * VANA — Field Monitoring & Follow-up Management API Service
 * Interacts with FastAPI endpoints under /api/v1/monitoring using the shared Axios client.
 */

import { apiClient } from "./apiClient";
import type {
  FieldInspection,
  InspectionAddendumCreate,
  InspectionCancelRequest,
  InspectionCompleteRequest,
  InspectionCreateRequest,
  InspectionEvidence,
  InspectionFilterParams,
  InspectionStartRequest,
  MaintenanceTask,
  MaintenanceTaskCreateRequest,
  MonitoringAlertSummary,
  MonitoringDashboard,
  SurvivalAnalytics,
  SurvivalFilterParams,
  SurvivalObservation,
  SurvivalObservationCorrectionRequest,
  SurvivalObservationCreateRequest,
  TaskCancelRequest,
  TaskCompleteRequest,
  TaskFilterParams,
  TaskReopenRequest,
  TaskStartRequest,
} from "../types/monitoring";

export const monitoringService = {
  // ==========================================================================
  // Field Inspections (8 endpoints)
  // ==========================================================================

  /**
   * Schedules a new field inspection. Restricted to Admins and assigned PMs.
   */
  async scheduleInspection(data: InspectionCreateRequest): Promise<FieldInspection> {
    const response = await apiClient.post<FieldInspection>("/monitoring/inspections", data);
    return response.data;
  },

  /**
   * Lists field inspections with optional multi-criteria filtering and pagination.
   */
  async listInspections(params?: InspectionFilterParams): Promise<FieldInspection[]> {
    const response = await apiClient.get<FieldInspection[]>("/monitoring/inspections", {
      params,
    });
    return response.data;
  },

  /**
   * Retrieves full details of a specific inspection by ID.
   */
  async getInspection(id: string): Promise<FieldInspection> {
    const response = await apiClient.get<FieldInspection>(`/monitoring/inspections/${id}`);
    return response.data;
  },

  /**
   * Transitions an inspection from SCHEDULED to IN_PROGRESS.
   */
  async startInspection(id: string, data?: InspectionStartRequest): Promise<FieldInspection> {
    const response = await apiClient.post<FieldInspection>(
      `/monitoring/inspections/${id}/start`,
      data ?? {}
    );
    return response.data;
  },

  /**
   * Completes an inspection with mandatory field observations.
   */
  async completeInspection(
    id: string,
    data: InspectionCompleteRequest
  ): Promise<FieldInspection> {
    const response = await apiClient.post<FieldInspection>(
      `/monitoring/inspections/${id}/complete`,
      data
    );
    return response.data;
  },

  /**
   * Cancels a scheduled or in-progress inspection with required justification.
   */
  async cancelInspection(id: string, data: InspectionCancelRequest): Promise<FieldInspection> {
    const response = await apiClient.post<FieldInspection>(
      `/monitoring/inspections/${id}/cancel`,
      data
    );
    return response.data;
  },

  /**
   * Appends an immutable post-completion addendum to a completed inspection.
   */
  async addInspectionAddendum(
    id: string,
    data: InspectionAddendumCreate
  ): Promise<FieldInspection> {
    const response = await apiClient.post<FieldInspection>(
      `/monitoring/inspections/${id}/addendum`,
      data
    );
    return response.data;
  },

  /**
   * Uploads photo or document evidence to an inspection using multipart/form-data.
   * Supports either raw FormData or File + optional GPS/caption metadata.
   */
  async uploadInspectionEvidence(
    id: string,
    fileOrFormData: File | FormData,
    metadata?: { latitude?: number | null; longitude?: number | null; caption?: string | null }
  ): Promise<InspectionEvidence> {
    let formData: FormData;

    if (fileOrFormData instanceof FormData) {
      formData = fileOrFormData;
    } else {
      formData = new FormData();
      formData.append("file", fileOrFormData);
      if (metadata?.latitude !== undefined && metadata?.latitude !== null) {
        formData.append("latitude", String(metadata.latitude));
      }
      if (metadata?.longitude !== undefined && metadata?.longitude !== null) {
        formData.append("longitude", String(metadata.longitude));
      }
      if (metadata?.caption) {
        formData.append("caption", metadata.caption);
      }
    }

    const response = await apiClient.post<InspectionEvidence>(
      `/monitoring/inspections/${id}/evidence`,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return response.data;
  },

  // ==========================================================================
  // Maintenance Tasks (7 endpoints)
  // ==========================================================================

  /**
   * Creates a new maintenance task. Restricted to Admins and assigned PMs.
   */
  async createTask(data: MaintenanceTaskCreateRequest): Promise<MaintenanceTask> {
    const response = await apiClient.post<MaintenanceTask>("/monitoring/tasks", data);
    return response.data;
  },

  /**
   * Lists maintenance tasks with optional status, priority, category, and assignee filtering.
   */
  async listTasks(params?: TaskFilterParams): Promise<MaintenanceTask[]> {
    const response = await apiClient.get<MaintenanceTask[]>("/monitoring/tasks", {
      params,
    });
    return response.data;
  },

  /**
   * Retrieves full details of a maintenance task by ID.
   */
  async getTask(id: string): Promise<MaintenanceTask> {
    const response = await apiClient.get<MaintenanceTask>(`/monitoring/tasks/${id}`);
    return response.data;
  },

  /**
   * Transitions a task from TODO to IN_PROGRESS.
   */
  async startTask(id: string, data?: TaskStartRequest): Promise<MaintenanceTask> {
    const response = await apiClient.post<MaintenanceTask>(
      `/monitoring/tasks/${id}/start`,
      data ?? {}
    );
    return response.data;
  },

  /**
   * Marks a task as COMPLETED with mandatory completion notes.
   */
  async completeTask(id: string, data: TaskCompleteRequest): Promise<MaintenanceTask> {
    const response = await apiClient.post<MaintenanceTask>(
      `/monitoring/tasks/${id}/complete`,
      data
    );
    return response.data;
  },

  /**
   * Cancels an open maintenance task with justification.
   */
  async cancelTask(id: string, data: TaskCancelRequest): Promise<MaintenanceTask> {
    const response = await apiClient.post<MaintenanceTask>(
      `/monitoring/tasks/${id}/cancel`,
      data
    );
    return response.data;
  },

  /**
   * Reopens a completed task back to TODO with mandatory justification.
   */
  async reopenTask(id: string, data: TaskReopenRequest): Promise<MaintenanceTask> {
    const response = await apiClient.post<MaintenanceTask>(
      `/monitoring/tasks/${id}/reopen`,
      data
    );
    return response.data;
  },

  // ==========================================================================
  // Survival Observations (5 endpoints)
  // ==========================================================================

  /**
   * Records a new field survival observation.
   * Server derives survival_rate; client-supplied survival_rate is never accepted.
   */
  async createSurvivalObservation(
    data: SurvivalObservationCreateRequest
  ): Promise<SurvivalObservation> {
    const response = await apiClient.post<SurvivalObservation>(
      "/monitoring/survival-observations",
      data
    );
    return response.data;
  },

  /**
   * Retrieves survival observation history for a project, with optional plot/cohort filtering.
   */
  async listSurvivalObservations(
    params: SurvivalFilterParams
  ): Promise<SurvivalObservation[]> {
    const response = await apiClient.get<SurvivalObservation[]>(
      "/monitoring/survival-observations",
      { params }
    );
    return response.data;
  },

  /**
   * Retrieves full details of a specific survival observation.
   */
  async getSurvivalObservation(id: string): Promise<SurvivalObservation> {
    const response = await apiClient.get<SurvivalObservation>(
      `/monitoring/survival-observations/${id}`
    );
    return response.data;
  },

  /**
   * Atomically supersedes an active observation with corrected data.
   * Deactivates the original observation and establishes acyclic supersession link.
   */
  async correctSurvivalObservation(
    id: string,
    data: SurvivalObservationCorrectionRequest
  ): Promise<SurvivalObservation> {
    const response = await apiClient.post<SurvivalObservation>(
      `/monitoring/survival-observations/${id}/correct`,
      data
    );
    return response.data;
  },

  /**
   * Retrieves longitudinal survival trajectory curves for a specific plot and cohort tuple.
   */
  async getSurvivalAnalytics(params: {
    projectId: string;
    plotIdentifier: string;
    cohortIdentifier: string;
  }): Promise<SurvivalAnalytics[]> {
    const response = await apiClient.get<SurvivalAnalytics[]>("/monitoring/survival-analytics", {
      params: {
        project_id: params.projectId,
        plot_identifier: params.plotIdentifier,
        cohort_identifier: params.cohortIdentifier,
      },
    });
    return response.data;
  },

  // ==========================================================================
  // Monitoring Operations: Alerts & Dashboard (2 endpoints)
  // ==========================================================================

  /**
   * Evaluates dynamic operational alerts on-demand in PostgreSQL.
   */
  async getMonitoringAlerts(projectId?: string): Promise<MonitoringAlertSummary> {
    const response = await apiClient.get<MonitoringAlertSummary>("/monitoring/alerts", {
      params: projectId ? { project_id: projectId } : undefined,
    });
    return response.data;
  },

  /**
   * Aggregates monitoring KPIs, backlog counts, active alerts, and latest observations.
   */
  async getMonitoringDashboard(projectId?: string): Promise<MonitoringDashboard> {
    const response = await apiClient.get<MonitoringDashboard>("/monitoring/dashboard", {
      params: projectId ? { project_id: projectId } : undefined,
    });
    return response.data;
  },
};
