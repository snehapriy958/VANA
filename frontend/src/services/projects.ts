import { apiClient } from "./apiClient";
import type {
  Project,
  ProjectDetail,
  ProjectCreateInput,
  ProjectUpdateInput,
  ProjectTarget,
  ProjectTargetCreateInput,
  ProjectTargetUpdateInput,
  ProjectAssignment,
  ProjectAssignmentCreateInput,
} from "@/types/projects";

export async function listProjects(params?: {
  search?: string;
  status?: string;
}): Promise<Project[]> {
  const response = await apiClient.get<Project[]>("/projects", { params });
  return response.data;
}

export async function getProject(projectId: string): Promise<ProjectDetail> {
  const response = await apiClient.get<ProjectDetail>(`/projects/${projectId}`);
  return response.data;
}

export async function createProject(data: ProjectCreateInput): Promise<Project> {
  const response = await apiClient.post<Project>("/projects", data);
  return response.data;
}

export async function updateProject(
  projectId: string,
  data: ProjectUpdateInput
): Promise<Project> {
  const response = await apiClient.put<Project>(`/projects/${projectId}`, data);
  return response.data;
}

// Environmental Targets
export async function listTargets(projectId: string): Promise<ProjectTarget[]> {
  const response = await apiClient.get<ProjectTarget[]>(
    `/projects/${projectId}/targets`
  );
  return response.data;
}

export async function createTarget(
  projectId: string,
  data: ProjectTargetCreateInput
): Promise<ProjectTarget> {
  const response = await apiClient.post<ProjectTarget>(
    `/projects/${projectId}/targets`,
    data
  );
  return response.data;
}

export async function updateTarget(
  projectId: string,
  targetId: string,
  data: ProjectTargetUpdateInput
): Promise<ProjectTarget> {
  const response = await apiClient.put<ProjectTarget>(
    `/projects/${projectId}/targets/${targetId}`,
    data
  );
  return response.data;
}

export async function deleteTarget(
  projectId: string,
  targetId: string
): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/targets/${targetId}`);
}

// Project Team Assignments
export async function listAssignments(
  projectId: string
): Promise<ProjectAssignment[]> {
  const response = await apiClient.get<ProjectAssignment[]>(
    `/projects/${projectId}/assignments`
  );
  return response.data;
}

export async function createAssignment(
  projectId: string,
  data: ProjectAssignmentCreateInput
): Promise<ProjectAssignment> {
  const response = await apiClient.post<ProjectAssignment>(
    `/projects/${projectId}/assignments`,
    data
  );
  return response.data;
}

export async function deleteAssignment(
  projectId: string,
  userId: string
): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/assignments/${userId}`);
}
