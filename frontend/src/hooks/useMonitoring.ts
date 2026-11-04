/**
 * VANA — Field Monitoring & Follow-up Management TanStack Query Hooks
 * Provides reactive query and mutation hooks with strict cache invalidation and project scoping.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { monitoringService } from "../services/monitoringService";
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

// ============================================================================
// Query Key Factory
// ============================================================================

export const monitoringKeys = {
  all: ["monitoring"] as const,

  // Field Inspections
  inspections: () => [...monitoringKeys.all, "inspections"] as const,
  inspectionLists: () => [...monitoringKeys.inspections(), "list"] as const,
  inspectionList: (filters?: InspectionFilterParams) =>
    [...monitoringKeys.inspectionLists(), filters ?? {}] as const,
  inspectionDetails: () => [...monitoringKeys.inspections(), "detail"] as const,
  inspectionDetail: (id: string) => [...monitoringKeys.inspectionDetails(), id] as const,

  // Maintenance Tasks
  tasks: () => [...monitoringKeys.all, "tasks"] as const,
  taskLists: () => [...monitoringKeys.tasks(), "list"] as const,
  taskList: (filters?: TaskFilterParams) =>
    [...monitoringKeys.taskLists(), filters ?? {}] as const,
  taskDetails: () => [...monitoringKeys.tasks(), "detail"] as const,
  taskDetail: (id: string) => [...monitoringKeys.taskDetails(), id] as const,

  // Survival Observations
  survival: () => [...monitoringKeys.all, "survival"] as const,
  survivalLists: () => [...monitoringKeys.survival(), "list"] as const,
  survivalList: (filters: SurvivalFilterParams) =>
    [...monitoringKeys.survivalLists(), filters] as const,
  survivalDetails: () => [...monitoringKeys.survival(), "detail"] as const,
  survivalDetail: (id: string) => [...monitoringKeys.survivalDetails(), id] as const,
  survivalTrajectories: () => [...monitoringKeys.survival(), "trajectory"] as const,
  survivalTrajectory: (projectId: string, plotId: string, cohortId: string) =>
    [...monitoringKeys.survivalTrajectories(), projectId, plotId, cohortId] as const,

  // Operational Alerts
  alerts: (projectId?: string) =>
    [...monitoringKeys.all, "alerts", projectId ?? "all"] as const,

  // Dashboard Summaries
  dashboard: (projectId?: string) =>
    [...monitoringKeys.all, "dashboard", projectId ?? "all"] as const,
};

// ============================================================================
// Inspection Queries & Mutations
// ============================================================================

export function useInspections(
  filters?: InspectionFilterParams,
  options?: Omit<UseQueryOptions<FieldInspection[], Error>, "queryKey" | "queryFn">
) {
  return useQuery<FieldInspection[], Error>({
    queryKey: monitoringKeys.inspectionList(filters),
    queryFn: () => monitoringService.listInspections(filters),
    ...options,
  });
}

export function useInspection(
  id: string,
  options?: Omit<UseQueryOptions<FieldInspection, Error>, "queryKey" | "queryFn">
) {
  return useQuery<FieldInspection, Error>({
    queryKey: monitoringKeys.inspectionDetail(id),
    queryFn: () => monitoringService.getInspection(id),
    enabled: Boolean(id) && (options?.enabled ?? true),
    ...options,
  });
}

export function useScheduleInspection(
  options?: UseMutationOptions<FieldInspection, Error, InspectionCreateRequest>
) {
  const queryClient = useQueryClient();
  return useMutation<FieldInspection, Error, InspectionCreateRequest>({
    ...options,
    mutationFn: (data) => monitoringService.scheduleInspection(data),
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.inspections() });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "alerts"] });
      options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useStartInspection(
  options?: UseMutationOptions<
    FieldInspection,
    Error,
    { id: string; data?: InspectionStartRequest }
  >
) {
  const queryClient = useQueryClient();
  return useMutation<FieldInspection, Error, { id: string; data?: InspectionStartRequest }>({
    ...options,
    mutationFn: ({ id, data }) => monitoringService.startInspection(id, data),
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.inspections() });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.inspectionDetail(variables.id) });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "alerts"] });
      options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useCompleteInspection(
  options?: UseMutationOptions<
    FieldInspection,
    Error,
    { id: string; data: InspectionCompleteRequest }
  >
) {
  const queryClient = useQueryClient();
  return useMutation<FieldInspection, Error, { id: string; data: InspectionCompleteRequest }>({
    ...options,
    mutationFn: ({ id, data }) => monitoringService.completeInspection(id, data),
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.inspections() });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.inspectionDetail(variables.id) });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "alerts"] });
      options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useCancelInspection(
  options?: UseMutationOptions<
    FieldInspection,
    Error,
    { id: string; data: InspectionCancelRequest }
  >
) {
  const queryClient = useQueryClient();
  return useMutation<FieldInspection, Error, { id: string; data: InspectionCancelRequest }>({
    ...options,
    mutationFn: ({ id, data }) => monitoringService.cancelInspection(id, data),
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.inspections() });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.inspectionDetail(variables.id) });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "alerts"] });
      options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useAddInspectionAddendum(
  options?: UseMutationOptions<
    FieldInspection,
    Error,
    { id: string; data: InspectionAddendumCreate }
  >
) {
  const queryClient = useQueryClient();
  return useMutation<FieldInspection, Error, { id: string; data: InspectionAddendumCreate }>({
    ...options,
    mutationFn: ({ id, data }) => monitoringService.addInspectionAddendum(id, data),
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.inspections() });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.inspectionDetail(variables.id) });
      options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export interface UploadInspectionEvidenceParams {
  id: string;
  fileOrFormData: File | FormData;
  metadata?: { latitude?: number | null; longitude?: number | null; caption?: string | null };
}

export function useUploadInspectionEvidence(
  options?: UseMutationOptions<InspectionEvidence, Error, UploadInspectionEvidenceParams>
) {
  const queryClient = useQueryClient();
  return useMutation<InspectionEvidence, Error, UploadInspectionEvidenceParams>({
    ...options,
    mutationFn: ({ id, fileOrFormData, metadata }) =>
      monitoringService.uploadInspectionEvidence(id, fileOrFormData, metadata),
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.inspections() });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.inspectionDetail(variables.id) });
      options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

// ============================================================================
// Maintenance Task Queries & Mutations
// ============================================================================

export function useMaintenanceTasks(
  filters?: TaskFilterParams,
  options?: Omit<UseQueryOptions<MaintenanceTask[], Error>, "queryKey" | "queryFn">
) {
  return useQuery<MaintenanceTask[], Error>({
    queryKey: monitoringKeys.taskList(filters),
    queryFn: () => monitoringService.listTasks(filters),
    ...options,
  });
}

export function useMaintenanceTask(
  id: string,
  options?: Omit<UseQueryOptions<MaintenanceTask, Error>, "queryKey" | "queryFn">
) {
  return useQuery<MaintenanceTask, Error>({
    queryKey: monitoringKeys.taskDetail(id),
    queryFn: () => monitoringService.getTask(id),
    enabled: Boolean(id) && (options?.enabled ?? true),
    ...options,
  });
}

export function useCreateMaintenanceTask(
  options?: UseMutationOptions<MaintenanceTask, Error, MaintenanceTaskCreateRequest>
) {
  const queryClient = useQueryClient();
  return useMutation<MaintenanceTask, Error, MaintenanceTaskCreateRequest>({
    ...options,
    mutationFn: (data) => monitoringService.createTask(data),
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.tasks() });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "alerts"] });
      options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useStartMaintenanceTask(
  options?: UseMutationOptions<
    MaintenanceTask,
    Error,
    { id: string; data?: TaskStartRequest }
  >
) {
  const queryClient = useQueryClient();
  return useMutation<MaintenanceTask, Error, { id: string; data?: TaskStartRequest }>({
    ...options,
    mutationFn: ({ id, data }) => monitoringService.startTask(id, data),
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.tasks() });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.taskDetail(variables.id) });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "alerts"] });
      options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useCompleteMaintenanceTask(
  options?: UseMutationOptions<
    MaintenanceTask,
    Error,
    { id: string; data: TaskCompleteRequest }
  >
) {
  const queryClient = useQueryClient();
  return useMutation<MaintenanceTask, Error, { id: string; data: TaskCompleteRequest }>({
    ...options,
    mutationFn: ({ id, data }) => monitoringService.completeTask(id, data),
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.tasks() });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.taskDetail(variables.id) });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "alerts"] });
      options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useCancelMaintenanceTask(
  options?: UseMutationOptions<
    MaintenanceTask,
    Error,
    { id: string; data: TaskCancelRequest }
  >
) {
  const queryClient = useQueryClient();
  return useMutation<MaintenanceTask, Error, { id: string; data: TaskCancelRequest }>({
    ...options,
    mutationFn: ({ id, data }) => monitoringService.cancelTask(id, data),
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.tasks() });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.taskDetail(variables.id) });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "alerts"] });
      options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useReopenMaintenanceTask(
  options?: UseMutationOptions<
    MaintenanceTask,
    Error,
    { id: string; data: TaskReopenRequest }
  >
) {
  const queryClient = useQueryClient();
  return useMutation<MaintenanceTask, Error, { id: string; data: TaskReopenRequest }>({
    ...options,
    mutationFn: ({ id, data }) => monitoringService.reopenTask(id, data),
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.tasks() });
      queryClient.invalidateQueries({ queryKey: monitoringKeys.taskDetail(variables.id) });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "alerts"] });
      options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

// ============================================================================
// Survival Observation Queries & Mutations
// ============================================================================

export function useSurvivalObservations(
  filters: SurvivalFilterParams,
  options?: Omit<UseQueryOptions<SurvivalObservation[], Error>, "queryKey" | "queryFn">
) {
  return useQuery<SurvivalObservation[], Error>({
    queryKey: monitoringKeys.survivalList(filters),
    queryFn: () => monitoringService.listSurvivalObservations(filters),
    enabled: Boolean(filters.project_id) && (options?.enabled ?? true),
    ...options,
  });
}

export function useSurvivalObservation(
  id: string,
  options?: Omit<UseQueryOptions<SurvivalObservation, Error>, "queryKey" | "queryFn">
) {
  return useQuery<SurvivalObservation, Error>({
    queryKey: monitoringKeys.survivalDetail(id),
    queryFn: () => monitoringService.getSurvivalObservation(id),
    enabled: Boolean(id) && (options?.enabled ?? true),
    ...options,
  });
}

export function useCreateSurvivalObservation(
  options?: UseMutationOptions<SurvivalObservation, Error, SurvivalObservationCreateRequest>
) {
  const queryClient = useQueryClient();
  return useMutation<SurvivalObservation, Error, SurvivalObservationCreateRequest>({
    ...options,
    mutationFn: (data) => monitoringService.createSurvivalObservation(data),
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.survival() });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });
      options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useCorrectSurvivalObservation(
  options?: UseMutationOptions<
    SurvivalObservation,
    Error,
    { id: string; data: SurvivalObservationCorrectionRequest }
  >
) {
  const queryClient = useQueryClient();
  return useMutation<
    SurvivalObservation,
    Error,
    { id: string; data: SurvivalObservationCorrectionRequest }
  >({
    ...options,
    mutationFn: ({ id, data }) => monitoringService.correctSurvivalObservation(id, data),
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.survival() });
      queryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });
      options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useSurvivalAnalytics(
  params: { projectId: string; plotIdentifier: string; cohortIdentifier: string },
  options?: Omit<UseQueryOptions<SurvivalAnalytics[], Error>, "queryKey" | "queryFn">
) {
  const isEnabled = Boolean(
    params.projectId && params.plotIdentifier && params.cohortIdentifier
  );
  return useQuery<SurvivalAnalytics[], Error>({
    queryKey: monitoringKeys.survivalTrajectory(
      params.projectId,
      params.plotIdentifier,
      params.cohortIdentifier
    ),
    queryFn: () => monitoringService.getSurvivalAnalytics(params),
    enabled: isEnabled && (options?.enabled ?? true),
    ...options,
  });
}

// ============================================================================
// Monitoring Alerts & Dashboard Queries
// ============================================================================

export function useMonitoringAlerts(
  projectId?: string,
  options?: Omit<UseQueryOptions<MonitoringAlertSummary, Error>, "queryKey" | "queryFn">
) {
  return useQuery<MonitoringAlertSummary, Error>({
    queryKey: monitoringKeys.alerts(projectId),
    queryFn: () => monitoringService.getMonitoringAlerts(projectId),
    ...options,
  });
}

export function useMonitoringDashboard(
  projectId?: string,
  options?: Omit<UseQueryOptions<MonitoringDashboard, Error>, "queryKey" | "queryFn">
) {
  return useQuery<MonitoringDashboard, Error>({
    queryKey: monitoringKeys.dashboard(projectId),
    queryFn: () => monitoringService.getMonitoringDashboard(projectId),
    ...options,
  });
}
