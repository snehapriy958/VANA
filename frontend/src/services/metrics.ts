import { apiClient } from "./apiClient";
import type { MetricDefinition } from "@/types/projects";

export async function getMetricsCatalog(): Promise<MetricDefinition[]> {
  const response = await apiClient.get<MetricDefinition[]>("/metrics/catalog");
  return response.data;
}
