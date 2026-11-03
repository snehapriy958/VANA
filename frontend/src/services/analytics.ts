/**
 * VANA — Environmental Analytics & Dashboard Service
 * Connects frontend to backend dashboard overview and analytics endpoints.
 */

import { apiClient } from "@/services/apiClient";
import type {
  DashboardOverviewResponse,
  DashboardProjectsResponse,
  MetricCatalogSummaryItem,
  ProjectImpactDetailResponse,
  ProjectTrendsResponse,
  RecentActivityItem,
} from "@/types/analytics";

export const analyticsService = {
  /**
   * Retrieves high-level portfolio or scoped dashboard overview.
   */
  async getDashboardOverview(): Promise<DashboardOverviewResponse> {
    const res = await apiClient.get<DashboardOverviewResponse>("/dashboard/overview");
    return res.data;
  },

  /**
   * Retrieves list of projects with their target progress, verified quantities, and coordinates.
   */
  async getDashboardProjects(params?: {
    status?: string;
    search?: string;
  }): Promise<DashboardProjectsResponse> {
    const res = await apiClient.get<DashboardProjectsResponse>("/dashboard/projects", {
      params,
    });
    return res.data;
  },

  /**
   * Retrieves recent operational activity stream (submissions, verifications, rejections).
   */
  async getRecentActivity(limit: number = 15): Promise<RecentActivityItem[]> {
    const res = await apiClient.get<RecentActivityItem[]>("/dashboard/recent-activity", {
      params: { limit },
    });
    return res.data;
  },

  /**
   * Retrieves detailed environmental impact balance sheet for a project.
   */
  async getProjectImpact(projectId: string): Promise<ProjectImpactDetailResponse> {
    const res = await apiClient.get<ProjectImpactDetailResponse>(
      `/analytics/projects/${projectId}/impact`
    );
    return res.data;
  },

  /**
   * Retrieves time-series data of verified activities for charting.
   */
  async getProjectTrends(
    projectId: string,
    params?: {
      metric_code?: string;
      start_date?: string;
      end_date?: string;
    }
  ): Promise<ProjectTrendsResponse> {
    const res = await apiClient.get<ProjectTrendsResponse>(
      `/analytics/projects/${projectId}/trends`,
      { params }
    );
    return res.data;
  },

  /**
   * Retrieves active metrics catalog summary with portfolio totals.
   */
  async getMetricsCatalogSummary(): Promise<MetricCatalogSummaryItem[]> {
    const res = await apiClient.get<MetricCatalogSummaryItem[]>("/analytics/metrics");
    return res.data;
  },
};
