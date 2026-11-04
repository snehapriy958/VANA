/**
 * VANA — Audit History & Immutability Ledger TanStack Query Hooks
 * Provides reactive query hooks and mutations with automatic cache invalidation.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { auditService } from "../services/auditService";
import type {
  AuditEventFilterParams,
  AuditLog,
  AuditLogListResponse,
  AuditVerificationFilterParams,
  AuditVerificationHistoryResponse,
  AuditVerifyChainRequest,
} from "../types/audit";

export const auditKeys = {
  all: ["audit"] as const,
  events: () => [...auditKeys.all, "events"] as const,
  eventList: (params?: AuditEventFilterParams) =>
    [...auditKeys.events(), "list", params ?? {}] as const,
  eventDetail: (id: string) =>
    [...auditKeys.events(), "detail", id] as const,
  verification: () => [...auditKeys.all, "verification"] as const,
  verificationList: (params?: AuditVerificationFilterParams) =>
    [...auditKeys.verification(), "list", params ?? {}] as const,
  entityTrails: () => [...auditKeys.all, "entity"] as const,
  entityTrail: (entityType: string, entityId: string, page: number = 1) =>
    [...auditKeys.entityTrails(), entityType, entityId, page] as const,
  chainVerification: () => [...auditKeys.all, "chain-verification"] as const,
};

export function useAuditEvents(
  params?: AuditEventFilterParams,
  options?: Omit<UseQueryOptions<AuditLogListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: auditKeys.eventList(params),
    queryFn: () => auditService.listEvents(params),
    placeholderData: (previousData) => previousData,
    ...options,
  });
}

export function useAuditEvent(
  id?: string,
  options?: Omit<UseQueryOptions<AuditLog, Error>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: auditKeys.eventDetail(id ?? ""),
    queryFn: () => auditService.getEvent(id!),
    enabled: Boolean(id),
    ...options,
  });
}

export function useVerificationHistory(
  params?: AuditVerificationFilterParams,
  options?: Omit<
    UseQueryOptions<AuditVerificationHistoryResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: auditKeys.verificationList(params),
    queryFn: () => auditService.getVerificationHistory(params),
    placeholderData: (previousData) => previousData,
    ...options,
  });
}

export function useEntityAuditTrail(
  entityType?: string,
  entityId?: string,
  page: number = 1,
  options?: Omit<UseQueryOptions<AuditLogListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: auditKeys.entityTrail(entityType ?? "", entityId ?? "", page),
    queryFn: () => auditService.getEntityTrail(entityType!, entityId!, page),
    enabled: Boolean(entityType && entityId),
    placeholderData: (previousData) => previousData,
    ...options,
  });
}

export function useVerifyAuditChain() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request?: AuditVerifyChainRequest) => auditService.verifyChain(request),
    onSuccess: (data) => {
      // Set query cache for quick inspection and invalidate event lists
      queryClient.setQueryData(auditKeys.chainVerification(), data);
      queryClient.invalidateQueries({ queryKey: auditKeys.events() });
    },
  });
}
