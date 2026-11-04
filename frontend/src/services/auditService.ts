/**
 * VANA — Audit History & Immutability Ledger Service
 * Communicates with FastAPI read-only audit endpoints under /api/v1/audit
 */

import { apiClient } from "./apiClient";
import type {
  AuditChainVerificationResponse,
  AuditEventFilterParams,
  AuditLog,
  AuditLogListResponse,
  AuditVerificationFilterParams,
  AuditVerificationHistoryResponse,
  AuditVerifyChainRequest,
} from "../types/audit";

export const auditService = {
  /**
   * Retrieves paginated, filterable audit event log stream.
   */
  async listEvents(params?: AuditEventFilterParams): Promise<AuditLogListResponse> {
    const response = await apiClient.get<AuditLogListResponse>("/audit/events", {
      params,
    });
    return response.data;
  },

  /**
   * Retrieves single audit log record by UUID with full canonical payload and states.
   */
  async getEvent(id: string): Promise<AuditLog> {
    const response = await apiClient.get<AuditLog>(`/audit/events/${id}`);
    return response.data;
  },

  /**
   * Retrieves immutable verification decision history.
   */
  async getVerificationHistory(
    params?: AuditVerificationFilterParams
  ): Promise<AuditVerificationHistoryResponse> {
    const response = await apiClient.get<AuditVerificationHistoryResponse>("/audit/verification", {
      params,
    });
    return response.data;
  },

  /**
   * Retrieves full chronological change history for a specific entity.
   */
  async getEntityTrail(
    entityType: string,
    entityId: string,
    page: number = 1,
    pageSize: number = 50
  ): Promise<AuditLogListResponse> {
    const response = await apiClient.get<AuditLogListResponse>(
      `/audit/entities/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}`,
      {
        params: { page, page_size: pageSize },
      }
    );
    return response.data;
  },

  /**
   * Triggers real-time read-only cryptographic SHA-256 chain verification.
   */
  async verifyChain(
    request?: AuditVerifyChainRequest
  ): Promise<AuditChainVerificationResponse> {
    const response = await apiClient.post<AuditChainVerificationResponse>(
      "/audit/verify-chain",
      request || {}
    );
    return response.data;
  },
};
