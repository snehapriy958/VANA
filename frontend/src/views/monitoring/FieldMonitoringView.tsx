import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  LayoutDashboard,
  Calendar,
  ClipboardList,
  HeartPulse,
  RefreshCw,
  FolderKanban,
} from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { listProjects } from "@/services/projects";
import { apiClient } from "@/services/apiClient";
import type { UserProfile } from "@/types/auth";
import type { Project } from "@/types/projects";
import type { InspectionEvidence } from "@/types/monitoring";
import {
  useAddInspectionAddendum,
  useCancelInspection,
  useCancelMaintenanceTask,
  useCompleteInspection,
  useCompleteMaintenanceTask,
  useCorrectSurvivalObservation,
  useCreateMaintenanceTask,
  useCreateSurvivalObservation,
  useInspections,
  useMaintenanceTasks,
  useMonitoringAlerts,
  useMonitoringDashboard,
  useReopenMaintenanceTask,
  useScheduleInspection,
  useStartInspection,
  useStartMaintenanceTask,
  useSurvivalAnalytics,
  useSurvivalObservations,
  useUploadInspectionEvidence,
} from "@/hooks/useMonitoring";

import { MonitoringDashboardTab } from "./components/MonitoringDashboardTab";
import { InspectionsTab } from "./components/InspectionsTab";
import { MaintenanceTasksTab } from "./components/MaintenanceTasksTab";
import { SurvivalMonitoringTab } from "./components/SurvivalMonitoringTab";
import { EvidenceLightboxModal } from "./components/EvidenceLightboxModal";
import { Button } from "@/components/ui/button";

export const FieldMonitoringView: React.FC = () => {
  const { user } = useAuth();

  // Active Workspace Tab
  const [activeTab, setActiveTab] = useState<
    "dashboard" | "inspections" | "maintenance" | "survival"
  >("dashboard");

  // Global Project Filter
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");

  // Survival Curve Plot and Cohort Selection
  const [selectedPlot, setSelectedPlot] = useState<string>("");
  const [selectedCohort, setSelectedCohort] = useState<string>("");

  // Evidence Lightbox State
  const [lightboxEvidence, setLightboxEvidence] = useState<InspectionEvidence | null>(null);

  // Queries
  const { data: projects = [] } = useQuery<Project[]>({
    queryKey: ["projects-dropdown"],
    queryFn: () => listProjects(),
  });

  const { data: orgUsers = [] } = useQuery<UserProfile[]>({
    queryKey: ["orgUsers-monitoring"],
    queryFn: async () => {
      const res = await apiClient.get<any>("/users");
      return Array.isArray(res.data) ? res.data : res.data?.users || [];
    },
    enabled: user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER",
  });

  const {
    data: dashboard,
    isLoading: isDashboardLoading,
    refetch: refetchDashboard,
  } = useMonitoringDashboard(selectedProjectId || undefined);

  const { data: alerts, refetch: refetchAlerts } = useMonitoringAlerts(
    selectedProjectId || undefined
  );

  const { data: inspections = [], refetch: refetchInspections } = useInspections(
    selectedProjectId ? { project_id: selectedProjectId } : undefined
  );

  const { data: tasks = [], refetch: refetchTasks } = useMaintenanceTasks(
    selectedProjectId ? { project_id: selectedProjectId } : undefined
  );

  const { data: survivalObs = [], refetch: refetchSurvival } = useSurvivalObservations({
    project_id: selectedProjectId || projects[0]?.id || "",
    active_only: false,
  });

  const { data: analytics = [] } = useSurvivalAnalytics({
    projectId: selectedProjectId || projects[0]?.id || "",
    plotIdentifier: selectedPlot,
    cohortIdentifier: selectedCohort,
  });

  // Mutation Hooks
  const scheduleInspectionMutation = useScheduleInspection();
  const startInspectionMutation = useStartInspection();
  const completeInspectionMutation = useCompleteInspection();
  const cancelInspectionMutation = useCancelInspection();
  const addAddendumMutation = useAddInspectionAddendum();
  const uploadEvidenceMutation = useUploadInspectionEvidence();

  const createTaskMutation = useCreateMaintenanceTask();
  const startTaskMutation = useStartMaintenanceTask();
  const completeTaskMutation = useCompleteMaintenanceTask();
  const cancelTaskMutation = useCancelMaintenanceTask();
  const reopenTaskMutation = useReopenMaintenanceTask();

  const createSurvivalMutation = useCreateSurvivalObservation();
  const correctSurvivalMutation = useCorrectSurvivalObservation();

  const handleRefreshAll = () => {
    refetchDashboard();
    refetchAlerts();
    refetchInspections();
    refetchTasks();
    refetchSurvival();
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header with Title and Global Project Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-vana-forest/10 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-vana-forest text-white shadow-subtle">
              <Activity className="h-5 w-5 text-vana-sage" />
            </div>
            <div>
              <h1 className="text-2xl font-bold font-manrope text-vana-forest leading-tight">
                Field Monitoring &amp; Follow-up
              </h1>
              <p className="text-xs text-vana-charcoal/70">
                Post-planting surveillance, routine audits, maintenance care, and longitudinal survival tracking.
              </p>
            </div>
          </div>
        </div>

        {/* Global Project Scoping Selector */}
        <div className="flex items-center gap-2 self-start md:self-auto">
          <div className="flex items-center gap-1.5 bg-white px-3 py-1.5 rounded-lg border border-vana-forest/20 shadow-xs text-xs">
            <FolderKanban className="h-4 w-4 text-vana-forest" />
            <select
              value={selectedProjectId}
              onChange={(e) => {
                setSelectedProjectId(e.target.value);
                setSelectedPlot("");
                setSelectedCohort("");
              }}
              className="bg-transparent font-medium text-vana-charcoal focus:outline-none text-xs"
            >
              <option value="">All Scoped Projects</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRefreshAll}
            className="h-8 text-xs border-vana-forest/20 text-vana-forest gap-1 hover:bg-vana-forest/10"
            title="Refresh All Monitoring Data"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Tab Navigation Strip */}
      <div className="flex items-center gap-1 border-b border-vana-charcoal/10 overflow-x-auto">
        <button
          type="button"
          onClick={() => setActiveTab("dashboard")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "dashboard"
              ? "border-vana-forest text-vana-forest"
              : "border-transparent text-vana-charcoal/60 hover:text-vana-forest hover:border-vana-forest/30"
          }`}
        >
          <LayoutDashboard className="h-4 w-4" />
          <span>Monitoring Overview</span>
          {alerts && alerts.total_alerts > 0 && (
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-vana-crimson/15 text-vana-crimson">
              {alerts.total_alerts}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("inspections")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "inspections"
              ? "border-vana-forest text-vana-forest"
              : "border-transparent text-vana-charcoal/60 hover:text-vana-forest hover:border-vana-forest/30"
          }`}
        >
          <Calendar className="h-4 w-4" />
          <span>Field Inspections</span>
          <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-medium bg-vana-forest/10 text-vana-forest">
            {inspections.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("maintenance")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "maintenance"
              ? "border-vana-forest text-vana-forest"
              : "border-transparent text-vana-charcoal/60 hover:text-vana-forest hover:border-vana-forest/30"
          }`}
        >
          <ClipboardList className="h-4 w-4" />
          <span>Maintenance Tasks</span>
          <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-medium bg-vana-forest/10 text-vana-forest">
            {tasks.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("survival")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "survival"
              ? "border-vana-forest text-vana-forest"
              : "border-transparent text-vana-charcoal/60 hover:text-vana-forest hover:border-vana-forest/30"
          }`}
        >
          <HeartPulse className="h-4 w-4" />
          <span>Survival Monitoring</span>
          <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-medium bg-vana-forest/10 text-vana-forest">
            {survivalObs.length}
          </span>
        </button>
      </div>

      {/* Tab 1: Dashboard Overview */}
      {activeTab === "dashboard" && (
        <MonitoringDashboardTab
          dashboard={dashboard}
          alerts={alerts}
          inspections={inspections}
          tasks={tasks}
          isLoading={isDashboardLoading}
          onNavigateTab={setActiveTab}
        />
      )}

      {/* Tab 2: Inspections Workspace */}
      {activeTab === "inspections" && (
        <InspectionsTab
          inspections={inspections}
          projects={projects}
          users={orgUsers}
          currentUserId={user?.id}
          currentUserRole={user?.role}
          selectedProjectId={selectedProjectId}
          onScheduleInspection={(data) => scheduleInspectionMutation.mutateAsync(data)}
          onStartInspection={(id) => startInspectionMutation.mutateAsync({ id })}
          onCompleteInspection={(id, data) =>
            completeInspectionMutation.mutateAsync({ id, data })
          }
          onCancelInspection={(id, data) => cancelInspectionMutation.mutateAsync({ id, data })}
          onAddAddendum={(id, data) => addAddendumMutation.mutateAsync({ id, data })}
          onUploadEvidence={(id, file, metadata) =>
            uploadEvidenceMutation.mutateAsync({ id, fileOrFormData: file, metadata })
          }
          onViewEvidence={(ev) => setLightboxEvidence(ev)}
        />
      )}

      {/* Tab 3: Maintenance Tasks Workspace */}
      {activeTab === "maintenance" && (
        <MaintenanceTasksTab
          tasks={tasks}
          projects={projects}
          users={orgUsers}
          currentUserId={user?.id}
          currentUserRole={user?.role}
          selectedProjectId={selectedProjectId}
          onCreateTask={(data) => createTaskMutation.mutateAsync(data)}
          onStartTask={(id) => startTaskMutation.mutateAsync({ id })}
          onCompleteTask={(id, data) => completeTaskMutation.mutateAsync({ id, data })}
          onCancelTask={(id, data) => cancelTaskMutation.mutateAsync({ id, data })}
          onReopenTask={(id, data) => reopenTaskMutation.mutateAsync({ id, data })}
        />
      )}

      {/* Tab 4: Survival Monitoring Workspace */}
      {activeTab === "survival" && (
        <SurvivalMonitoringTab
          observations={survivalObs}
          analytics={analytics}
          projects={projects}
          selectedProjectId={selectedProjectId}
          selectedPlot={selectedPlot}
          selectedCohort={selectedCohort}
          onSelectPlot={setSelectedPlot}
          onSelectCohort={setSelectedCohort}
          currentUserRole={user?.role}
          onCreateObservation={(data) => createSurvivalMutation.mutateAsync(data)}
          onCorrectObservation={(id, data) =>
            correctSurvivalMutation.mutateAsync({ id, data })
          }
        />
      )}

      {/* Evidence Lightbox Viewer Modal */}
      <EvidenceLightboxModal
        evidence={lightboxEvidence}
        isOpen={!!lightboxEvidence}
        onClose={() => setLightboxEvidence(null)}
      />
    </div>
  );
};
