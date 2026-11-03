import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  getProject,
  updateProject,
  createTarget,
  updateTarget,
  deleteTarget,
  createAssignment,
  deleteAssignment,
} from "@/services/projects";
import { getMetricsCatalog } from "@/services/metrics";
import { analyticsService } from "@/services/analytics";
import { operationsService } from "@/services/operations";
import { apiClient } from "@/services/apiClient";
import { useAuth } from "@/context/AuthContext";
import {
  ProjectTarget,
  ProjectAssignment,
} from "@/types/projects";
import { UserProfile } from "@/types/auth";
import { PageContainer } from "@/components/layout/PageContainer";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  FolderTree,
  Target,
  Users,
  MapPin,
  Calendar,
  Edit,
  Trash2,
  UserPlus,
  Plus,
  ArrowLeft,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Globe,
  Layers,
  Copy,
  TrendingUp,
  BarChart3,
  Activity,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

// Schemas for Modals
const targetSchema = z.object({
  metric_code: z.string().min(1, "Metric code required"),
  target_quantity: z.coerce.number().positive("Quantity must be greater than 0"),
  target_unit: z.string().min(1, "Target unit required"),
  target_date: z.string().min(1, "Target deadline required"),
});
type TargetFormData = z.infer<typeof targetSchema>;

const editProjectSchema = z.object({
  name: z.string().trim().min(3, "Name must be at least 3 characters"),
  description: z.string().trim().optional(),
  status: z.enum(["ACTIVE", "DRAFT", "COMPLETED", "ARCHIVED"] as const),
  latitude: z.coerce.number().min(-90).max(90),
  longitude: z.coerce.number().min(-180).max(180),
  polygonText: z.string().trim().optional(),
});
type EditProjectFormData = z.infer<typeof editProjectSchema>;

const assignmentSchema = z.object({
  user_id: z.string().uuid("Please select a valid user"),
  assigned_role: z.enum(["PROJECT_MANAGER", "FIELD_OFFICER"] as const),
});
type AssignmentFormData = z.infer<typeof assignmentSchema>;

export const ProjectWorkspaceView: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { user: currentUser } = useAuth();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<"overview" | "targets" | "impact" | "team" | "geography">("overview");

  // Modals
  const [targetModalOpen, setTargetModalOpen] = useState(false);
  const [editProjectModalOpen, setEditProjectModalOpen] = useState(false);
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Editing existing target state
  const [editingTargetId, setEditingTargetId] = useState<string | null>(null);

  // Queries
  const {
    data: project,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId!),
    enabled: !!projectId,
  });

  const { data: metricsCatalog = [] } = useQuery({
    queryKey: ["metricsCatalog"],
    queryFn: getMetricsCatalog,
  });

  const { data: orgUsers = [] } = useQuery({
    queryKey: ["orgUsers"],
    queryFn: async () => {
      const res = await apiClient.get<UserProfile[]>("/users");
      return res.data;
    },
    enabled: currentUser?.role === "ADMIN" || currentUser?.role === "PROJECT_MANAGER",
  });

  const { data: projectImpact, isLoading: isImpactLoading } = useQuery({
    queryKey: ["projectImpact", projectId],
    queryFn: () => analyticsService.getProjectImpact(projectId!),
    enabled: !!projectId,
    staleTime: 30000,
  });

  const { data: projectTrends } = useQuery({
    queryKey: ["projectTrends", projectId],
    queryFn: () => analyticsService.getProjectTrends(projectId!),
    enabled: !!projectId && activeTab === "impact",
    staleTime: 30000,
  });

  const { data: projectActivities = [], isLoading: isLoadingActivities } = useQuery({
    queryKey: ["projectActivities", projectId],
    queryFn: () => operationsService.getActivities({ projectId, isArchived: false }),
    enabled: !!projectId && (activeTab === "impact" || activeTab === "overview"),
    staleTime: 30000,
  });

  // Determine permissions
  const isAdmin = currentUser?.role === "ADMIN";
  const isAssignedPM =
    project?.assignments?.some(
      (a) => a.user_id === currentUser?.id && a.assigned_role === "PROJECT_MANAGER"
    ) || false;
  const canManage = isAdmin || isAssignedPM;

  // Target Form
  const {
    register: registerTarget,
    handleSubmit: handleTargetSubmit,
    watch: watchTarget,
    setValue: setTargetValue,
    reset: resetTarget,
    formState: { errors: targetErrors, isSubmitting: isSubmittingTarget },
  } = useForm<TargetFormData>({
    resolver: zodResolver(targetSchema),
    defaultValues: {
      metric_code: "TREES_PLANTED",
      target_quantity: 1000,
      target_unit: "trees",
      target_date: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
    },
  });

  const selectedMetricCode = watchTarget("metric_code");
  const selectedMetricDef = metricsCatalog.find((m) => m.metric_code === selectedMetricCode);

  // Edit Project Form
  const {
    register: registerEditProject,
    handleSubmit: handleEditProjectSubmit,
    reset: resetEditProject,
    formState: { errors: editProjectErrors, isSubmitting: isSubmittingEditProject },
  } = useForm<EditProjectFormData>({
    resolver: zodResolver(editProjectSchema),
  });

  // Assignment Form
  const {
    register: registerAssignment,
    handleSubmit: handleAssignmentSubmit,
    reset: resetAssignment,
    formState: { errors: assignErrors, isSubmitting: isSubmittingAssign },
  } = useForm<AssignmentFormData>({
    resolver: zodResolver(assignmentSchema),
    defaultValues: {
      assigned_role: "FIELD_OFFICER",
    },
  });

  // Mutations
  const createTargetMutation = useMutation({
    mutationFn: (data: TargetFormData) =>
      createTarget(projectId!, {
        metric_code: data.metric_code,
        target_quantity: data.target_quantity,
        target_unit: data.target_unit,
        target_date: data.target_date,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      setTargetModalOpen(false);
      resetTarget();
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail?.message || err.message || "Failed to create target.");
    },
  });

  const updateTargetMutation = useMutation({
    mutationFn: (data: TargetFormData) =>
      updateTarget(projectId!, editingTargetId!, {
        target_quantity: data.target_quantity,
        target_unit: data.target_unit,
        target_date: data.target_date,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      setTargetModalOpen(false);
      setEditingTargetId(null);
      resetTarget();
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail?.message || err.message || "Failed to update target.");
    },
  });

  const deleteTargetMutation = useMutation({
    mutationFn: (targetId: string) => deleteTarget(projectId!, targetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });

  const updateProjectMutation = useMutation({
    mutationFn: async (data: EditProjectFormData) => {
      let boundaryGeojson = undefined;
      if (data.polygonText && data.polygonText.trim()) {
        boundaryGeojson = JSON.parse(data.polygonText);
      }
      return updateProject(projectId!, {
        name: data.name,
        description: data.description,
        status: data.status,
        latitude: data.latitude,
        longitude: data.longitude,
        boundary_geojson: boundaryGeojson,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setEditProjectModalOpen(false);
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail?.message || err.message || "Failed to update project.");
    },
  });

  const assignMutation = useMutation({
    mutationFn: (data: AssignmentFormData) =>
      createAssignment(projectId!, {
        user_id: data.user_id,
        assigned_role: data.assigned_role,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      setAssignModalOpen(false);
      resetAssignment();
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail?.message || err.message || "Failed to assign team member.");
    },
  });

  const removeAssignmentMutation = useMutation({
    mutationFn: (userId: string) => deleteAssignment(projectId!, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });

  if (isLoading) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center min-h-[50vh]">
          <Loader2 className="w-8 h-8 text-forest animate-spin" />
        </div>
      </PageContainer>
    );
  }

  if (isError || !project) {
    return (
      <PageContainer>
        <div className="p-8 text-center bg-crimson/5 border border-crimson/20 rounded-xl my-8">
          <AlertCircle className="w-8 h-8 text-crimson mx-auto mb-2" />
          <h3 className="font-semibold text-charcoal">Project Not Accessible</h3>
          <p className="text-sm text-charcoal/70 mt-1 mb-4">
            {(error as any)?.response?.data?.detail?.message ||
              "Project does not exist or you do not have permission to view this project."}
          </p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Retry Connection
          </Button>
          <Link to="/projects" className="ml-2">
            <Button variant="outline" size="sm">
              Back to Projects
            </Button>
          </Link>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      {/* Top Breadcrumb & Nav */}
      <div className="flex items-center gap-2 text-xs text-charcoal/60 mb-4">
        <Link to="/projects" className="hover:text-forest flex items-center gap-1 font-medium">
          <ArrowLeft className="w-3.5 h-3.5" />
          Project Portfolio
        </Link>
        <span>/</span>
        <span className="text-charcoal font-semibold">{project.name}</span>
      </div>

      {/* Hero Workspace Banner */}
      <div className="bg-white rounded-xl border border-charcoal/10 shadow-sm p-6 mb-6">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="font-mono text-xs font-bold text-forest bg-forest/10 px-2.5 py-1 rounded border border-forest/20">
                {project.code}
              </span>
              <Badge
                className={
                  project.status === "ACTIVE"
                    ? "bg-forest/10 text-forest border-forest/30"
                    : project.status === "COMPLETED"
                    ? "bg-sage/20 text-forest border-sage"
                    : "bg-ivory text-charcoal/70"
                }
              >
                {project.status}
              </Badge>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold font-manrope text-charcoal">
              {project.name}
            </h1>
            <p className="text-sm text-charcoal/70 max-w-3xl mt-1.5">
              {project.description || "No project overview description provided."}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {canManage && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setActionError(null);
                  resetEditProject({
                    name: project.name,
                    description: project.description || "",
                    status: project.status,
                    latitude: project.latitude,
                    longitude: project.longitude,
                    polygonText: project.boundary_geojson
                      ? JSON.stringify(project.boundary_geojson, null, 2)
                      : "",
                  });
                  setEditProjectModalOpen(true);
                }}
                className="border-charcoal/20 text-charcoal hover:bg-forest/5"
              >
                <Edit className="w-4 h-4 mr-1.5" />
                Edit Project
              </Button>
            )}
          </div>
        </div>

        {/* Quick summary bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-4 border-t border-charcoal/10">
          <div>
            <span className="text-[11px] uppercase tracking-wider font-semibold text-charcoal/50">
              Coordinates
            </span>
            <p className="text-xs font-mono font-medium text-charcoal mt-0.5">
              {project.latitude.toFixed(4)}°, {project.longitude.toFixed(4)}°
            </p>
          </div>
          <div>
            <span className="text-[11px] uppercase tracking-wider font-semibold text-charcoal/50">
              Targets Set
            </span>
            <p className="text-xs font-bold text-forest mt-0.5">
              {project.targets?.length || 0} Dimensional Targets
            </p>
          </div>
          <div>
            <span className="text-[11px] uppercase tracking-wider font-semibold text-charcoal/50">
              Staff Allocated
            </span>
            <p className="text-xs font-bold text-charcoal mt-0.5">
              {project.assignments?.length || 0} Personnel
            </p>
          </div>
          <div>
            <span className="text-[11px] uppercase tracking-wider font-semibold text-charcoal/50">
              Boundary Status
            </span>
            <p className="text-xs font-semibold text-charcoal mt-0.5">
              {project.boundary_geojson ? "GeoJSON Polygon Attached" : "Point Marker Only"}
            </p>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 border-b border-charcoal/15 mb-6">
        <button
          onClick={() => setActiveTab("overview")}
          className={`py-2.5 px-4 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === "overview"
              ? "border-forest text-forest"
              : "border-transparent text-charcoal/60 hover:text-charcoal"
          }`}
        >
          <FolderTree className="w-3.5 h-3.5" />
          Overview
        </button>

        <button
          onClick={() => setActiveTab("targets")}
          className={`py-2.5 px-4 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === "targets"
              ? "border-forest text-forest"
              : "border-transparent text-charcoal/60 hover:text-charcoal"
          }`}
        >
          <Target className="w-3.5 h-3.5" />
          Environmental Targets
          <span className="ml-1 text-[10px] bg-forest/10 text-forest px-1.5 py-0.2 rounded-full font-bold">
            {project.targets?.length || 0}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("impact")}
          className={`py-2.5 px-4 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === "impact"
              ? "border-forest text-forest"
              : "border-transparent text-charcoal/60 hover:text-charcoal"
          }`}
        >
          <TrendingUp className="w-3.5 h-3.5" />
          Impact & Analytics
        </button>

        <button
          onClick={() => setActiveTab("team")}
          className={`py-2.5 px-4 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === "team"
              ? "border-forest text-forest"
              : "border-transparent text-charcoal/60 hover:text-charcoal"
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          Team Roster
          <span className="ml-1 text-[10px] bg-forest/10 text-forest px-1.5 py-0.2 rounded-full font-bold">
            {project.assignments?.length || 0}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("geography")}
          className={`py-2.5 px-4 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === "geography"
              ? "border-forest text-forest"
              : "border-transparent text-charcoal/60 hover:text-charcoal"
          }`}
        >
          <MapPin className="w-3.5 h-3.5" />
          Geographic Information
        </button>
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            <Card className="bg-white border-charcoal/10 shadow-sm">
              <CardHeader>
                <CardTitle className="text-base font-bold font-manrope text-charcoal">
                  Initiative Scope & Objectives
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm text-charcoal/80 leading-relaxed">
                <p>
                  {project.description ||
                    "This environmental initiative manages verified ecological interventions across its assigned geographic jurisdiction. Active targets, personnel allocations, and field verifications contribute toward Akshaya Vana official achievements."}
                </p>
                <div className="p-4 bg-ivory/60 rounded-xl border border-charcoal/10 text-xs text-charcoal/70">
                  <span className="font-bold text-forest">Governing Standard:</span> All environmental measurements and target achievements are bounded strictly by metric codes and dimensional conservation rules. Targets must not be cross-aggregated or mixed across distinct dimensions.
                </div>
              </CardContent>
            </Card>

            {/* Target Balance Overview */}
            <Card className="bg-white border-charcoal/10 shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-base font-bold font-manrope text-charcoal">
                  Dimensional Targets Summary
                </CardTitle>
                <button
                  onClick={() => setActiveTab("targets")}
                  className="text-xs text-forest hover:underline font-semibold"
                >
                  View All Targets &rarr;
                </button>
              </CardHeader>
              <CardContent>
                {project.targets?.length === 0 ? (
                  <p className="text-xs text-charcoal/50 py-4 text-center">
                    No environmental targets have been configured for this project yet.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {project.targets.map((t) => (
                      <div
                        key={t.id}
                        className="flex items-center justify-between p-3 rounded-lg border border-charcoal/10 bg-ivory/30"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-xs text-charcoal">
                              {t.display_name}
                            </span>
                            <span className="text-[10px] font-mono text-charcoal/50 bg-charcoal/5 px-1.5 py-0.5 rounded">
                              {t.metric_code}
                            </span>
                          </div>
                          <span className="text-[11px] text-charcoal/60">
                            Target Date: {t.target_date}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-sm font-bold text-forest font-mono">
                            {Number(t.target_quantity).toLocaleString()} {t.target_unit}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            {/* Leadership & Personnel Card */}
            <Card className="bg-white border-charcoal/10 shadow-sm">
              <CardHeader>
                <CardTitle className="text-base font-bold font-manrope text-charcoal">
                  Project Leadership
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {project.assignments?.filter((a) => a.assigned_role === "PROJECT_MANAGER").length === 0 ? (
                  <p className="text-xs text-charcoal/50">No Project Manager assigned yet.</p>
                ) : (
                  project.assignments
                    .filter((a) => a.assigned_role === "PROJECT_MANAGER")
                    .map((pm) => (
                      <div key={pm.id} className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full bg-forest text-white flex items-center justify-center font-bold text-xs">
                          {pm.user_full_name?.charAt(0) || "P"}
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-charcoal">{pm.user_full_name}</p>
                          <p className="text-[11px] text-charcoal/60">{pm.user_email}</p>
                        </div>
                      </div>
                    ))
                )}
              </CardContent>
            </Card>

            {/* Geographic Card */}
            <Card className="bg-white border-charcoal/10 shadow-sm">
              <CardHeader>
                <CardTitle className="text-base font-bold font-manrope text-charcoal flex items-center gap-1.5">
                  <MapPin className="w-4 h-4 text-forest" />
                  Site Location
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-charcoal/5 font-mono">
                  <span className="text-charcoal/60">Center Latitude:</span>
                  <span className="font-semibold text-charcoal">{project.latitude.toFixed(6)}°</span>
                </div>
                <div className="flex justify-between py-1 border-b border-charcoal/5 font-mono">
                  <span className="text-charcoal/60">Center Longitude:</span>
                  <span className="font-semibold text-charcoal">{project.longitude.toFixed(6)}°</span>
                </div>
                <div className="flex justify-between py-1 border-b border-charcoal/5">
                  <span className="text-charcoal/60">Boundary Polygon:</span>
                  <span className="font-semibold text-forest">
                    {project.boundary_geojson ? "Defined" : "None"}
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setActiveTab("geography")}
                  className="w-full mt-3 text-xs border-charcoal/20"
                >
                  Inspect Coordinates & Boundary
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* TAB 2: ENVIRONMENTAL TARGETS */}
      {activeTab === "targets" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold font-manrope text-charcoal">
                Project Environmental Targets
              </h2>
              <p className="text-xs text-charcoal/70">
                Official dimensional conservation metrics approved for this project.
              </p>
            </div>

            {canManage && (
              <Button
                size="sm"
                onClick={() => {
                  setActionError(null);
                  setEditingTargetId(null);
                  resetTarget({
                    metric_code: "TREES_PLANTED",
                    target_quantity: 10000,
                    target_unit: "trees",
                    target_date: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
                  });
                  setTargetModalOpen(true);
                }}
                className="bg-forest text-white hover:bg-forest/90"
              >
                <Plus className="w-4 h-4 mr-1.5" />
                Add Target
              </Button>
            )}
          </div>

          {project.targets?.length === 0 ? (
            <div className="text-center py-12 px-4 bg-white rounded-xl border border-charcoal/10 shadow-sm">
              <Target className="w-10 h-10 text-forest/30 mx-auto mb-2" />
              <h3 className="font-bold text-charcoal">No Environmental Targets Defined</h3>
              <p className="text-xs text-charcoal/60 max-w-sm mx-auto mt-1 mb-4">
                Establish measurable goals (e.g. Trees Planted, Area Restored) from the approved environmental catalog.
              </p>
              {canManage && (
                <Button
                  size="sm"
                  onClick={() => {
                    setActionError(null);
                    setEditingTargetId(null);
                    setTargetModalOpen(true);
                  }}
                  className="bg-forest text-white"
                >
                  <Plus className="w-4 h-4 mr-1.5" />
                  Define First Target
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {project.targets.map((t: ProjectTarget) => (
                <Card key={t.id} className="bg-white border-charcoal/10 shadow-sm flex flex-col justify-between">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <Badge className="bg-forest/10 text-forest border-forest/20 text-[10px]">
                        {t.category}
                      </Badge>
                      <span className="text-[10px] font-mono text-charcoal/50 bg-charcoal/5 px-1.5 py-0.5 rounded">
                        {t.dimension}
                      </span>
                    </div>
                    <CardTitle className="text-base font-bold font-manrope text-charcoal">
                      {t.display_name}
                    </CardTitle>
                    <CardDescription className="text-xs font-mono text-charcoal/60">
                      {t.metric_code}
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="space-y-4 pt-0">
                    <div className="bg-ivory/60 p-3 rounded-lg border border-charcoal/5">
                      <span className="text-[11px] uppercase tracking-wider font-semibold text-charcoal/50 block">
                        Target Goal
                      </span>
                      <p className="text-xl font-bold font-mono text-forest mt-0.5">
                        {Number(t.target_quantity).toLocaleString()}{" "}
                        <span className="text-sm font-normal text-charcoal/70">{t.target_unit}</span>
                      </p>
                      <div className="flex items-center gap-1.5 text-xs text-charcoal/60 mt-2 pt-2 border-t border-charcoal/10">
                        <Calendar className="w-3.5 h-3.5 text-forest" />
                        <span>Deadline: {t.target_date}</span>
                      </div>
                    </div>

                    {canManage && (
                      <div className="flex items-center justify-end gap-2 pt-2 border-t border-charcoal/10">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setActionError(null);
                            setEditingTargetId(t.id);
                            resetTarget({
                              metric_code: t.metric_code,
                              target_quantity: Number(t.target_quantity),
                              target_unit: t.target_unit,
                              target_date: t.target_date,
                            });
                            setTargetModalOpen(true);
                          }}
                          className="h-7 text-xs border-charcoal/20"
                        >
                          <Edit className="w-3 h-3 mr-1" /> Edit
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            if (confirm(`Are you sure you want to delete the target for ${t.display_name}?`)) {
                              deleteTargetMutation.mutate(t.id);
                            }
                          }}
                          className="h-7 text-xs border-crimson/20 text-crimson hover:bg-crimson/5"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: ENVIRONMENTAL IMPACT & ANALYTICS */}
      {activeTab === "impact" && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold font-manrope text-charcoal flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-forest" />
                Official Environmental Ledger & Impact Intelligence
              </h2>
              <p className="text-xs text-charcoal/70 mt-0.5">
                Authoritative quantities aggregated strictly from active verified revisions (
                <code className="bg-ivory px-1 rounded font-mono text-forest">is_active_ledger_entry = True</code>
                ). Excludes unreviewed and rejected submissions.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Link to="/operations">
                <Button variant="outline" size="sm" className="h-8 text-xs border-forest/20 text-forest hover:bg-forest/5">
                  <Activity className="w-3.5 h-3.5 mr-1" /> Field Operations
                </Button>
              </Link>
              {canManage && (
                <Link to="/verification">
                  <Button size="sm" className="h-8 text-xs bg-forest text-white hover:bg-forest/90">
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Verification Centre
                  </Button>
                </Link>
              )}
            </div>
          </div>

          {/* Target Progress Breakdown Cards */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-charcoal/60 mb-3">
              Environmental Targets Progress & Ledger Status
            </h3>

            {isImpactLoading ? (
              <div className="p-8 text-center bg-white rounded-xl border border-charcoal/10">
                <Loader2 className="w-6 h-6 animate-spin text-forest mx-auto mb-2" />
                <p className="text-xs text-charcoal/60">Computing ledger quantities from PostgreSQL...</p>
              </div>
            ) : !projectImpact?.targets || projectImpact.targets.length === 0 ? (
              <Card className="bg-white border-dashed border-charcoal/20">
                <CardContent className="p-6 text-center text-xs text-charcoal/60">
                  No targets configured for this project yet. Add targets in the Environmental Targets tab to enable impact tracking.
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {projectImpact.targets.map((t) => {
                  const targetQty = Number(t.target_quantity) || 0;
                  const verifiedQty = Number(t.verified_quantity) || 0;
                  const pendingAdj = Number(t.net_pending_adjustment) || 0;
                  const remainingQty = Number(t.remaining_quantity) || 0;
                  const verifiedPct = Math.min(t.achievement_percentage || 0, 100);
                  const pendingPct = targetQty > 0 && pendingAdj > 0
                    ? Math.min((pendingAdj / targetQty) * 100, Math.max(0, 100 - verifiedPct))
                    : 0;

                  return (
                    <Card key={t.target_id} className="bg-white border-charcoal/10 shadow-sm hover:border-forest/30 transition-all">
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between">
                          <div>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-forest/10 text-forest font-semibold">
                              {t.metric_code}
                            </span>
                            <CardTitle className="text-base font-bold font-manrope text-charcoal mt-1.5">
                              {t.metric_name}
                            </CardTitle>
                          </div>
                          <div className="text-right">
                            <span className="text-2xl font-bold font-manrope text-forest">
                              {t.achievement_percentage}%
                            </span>
                            <p className="text-[10px] text-charcoal/50 font-medium">Verified Progress</p>
                          </div>
                        </div>
                      </CardHeader>

                      <CardContent className="space-y-4 pt-0">
                        {/* Bi-level Progress Bar */}
                        <div className="space-y-1.5">
                          <div className="h-3 w-full bg-ivory rounded-full overflow-hidden flex border border-charcoal/10">
                            {/* Official Verified (Solid Forest Green) */}
                            <div
                              className="bg-forest h-full transition-all duration-500"
                              style={{ width: `${verifiedPct}%` }}
                              title={`Verified: ${verifiedQty.toLocaleString()} ${t.target_unit} (${verifiedPct}%)`}
                            />
                            {/* Net Pending Adjustment (Secondary Striped Earth Gold) */}
                            {pendingPct > 0 && (
                              <div
                                className="bg-earth h-full opacity-80 transition-all duration-500 border-l border-white/30"
                                style={{ width: `${pendingPct}%` }}
                                title={`Pending Adjustment: +${pendingAdj.toLocaleString()} ${t.target_unit}`}
                              />
                            )}
                          </div>

                          <div className="flex items-center justify-between text-[11px] text-charcoal/70">
                            <span className="flex items-center gap-1">
                              <span className="w-2 h-2 rounded-full bg-forest inline-block" />
                              <strong>Verified:</strong> {verifiedQty.toLocaleString()} {t.target_unit}
                            </span>
                            {pendingAdj !== 0 && (
                              <span className="flex items-center gap-1 text-earth font-medium">
                                <span className="w-2 h-2 rounded-full bg-earth inline-block" />
                                <strong>Pending:</strong> {pendingAdj > 0 ? `+${pendingAdj.toLocaleString()}` : pendingAdj.toLocaleString()} {t.target_unit}
                              </span>
                            )}
                            <span>
                              <strong>Target:</strong> {targetQty.toLocaleString()} {t.target_unit}
                            </span>
                          </div>
                        </div>

                        {/* Quantity Breakdown Grid */}
                        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-charcoal/10 text-xs">
                          <div className="p-2 bg-ivory/50 rounded-lg">
                            <span className="text-[10px] text-charcoal/50 uppercase block font-semibold">Remaining</span>
                            <span className="font-bold font-mono text-charcoal text-sm">
                              {remainingQty.toLocaleString()}
                            </span>
                            <span className="text-[10px] text-charcoal/50 ml-1">{t.target_unit}</span>
                          </div>

                          <div className="p-2 bg-ivory/50 rounded-lg">
                            <span className="text-[10px] text-charcoal/50 uppercase block font-semibold">Deadline</span>
                            <span className="font-mono text-charcoal font-semibold text-xs">
                              {t.target_date}
                            </span>
                          </div>

                          <div className="p-2 bg-ivory/50 rounded-lg">
                            <span className="text-[10px] text-charcoal/50 uppercase block font-semibold">Milestone Ref</span>
                            <span className="font-mono text-charcoal/80 text-xs truncate block" title={t.milestone_id || "None"}>
                              {t.milestone_id || "None"}
                            </span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>

          {/* Activity Velocity Chart */}
          <Card className="bg-white border-charcoal/10 shadow-sm">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-bold font-manrope text-charcoal flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-forest" />
                    Activity Velocity & Cumulative Progress Over Time
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Time-series visualization of verified environmental achievements.
                  </CardDescription>
                </div>
                {projectTrends?.available_metrics && projectTrends.available_metrics.length > 0 && (
                  <Badge variant="outline" className="text-[10px] border-forest/20 text-forest">
                    {projectTrends.available_metrics.join(", ")}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {projectTrends?.trends && projectTrends.trends.length > 0 ? (
                <div className="h-64 w-full pt-3">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={projectTrends.trends}
                      margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#29332F10" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 11, fill: "#29332F80" }}
                        axisLine={{ stroke: "#29332F20" }}
                      />
                      <YAxis
                        tick={{ fontSize: 11, fill: "#29332F80" }}
                        axisLine={{ stroke: "#29332F20" }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#29332F",
                          border: "none",
                          borderRadius: "8px",
                          color: "#F5F3EA",
                          fontSize: "12px",
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="cumulative_quantity"
                        name="Cumulative Quantity"
                        stroke="#183D32"
                        strokeWidth={2}
                        fill="#183D32"
                        fillOpacity={0.15}
                      />
                      <Area
                        type="monotone"
                        dataKey="period_quantity"
                        name="Period Quantity"
                        stroke="#D6A76A"
                        strokeWidth={1.5}
                        fill="#D6A76A"
                        fillOpacity={0.2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-40 flex flex-col items-center justify-center text-center text-xs text-charcoal/50 bg-ivory/30 rounded-lg">
                  <Activity className="w-6 h-6 text-charcoal/30 mb-2" />
                  <p>No verified activities recorded yet for time-series trend calculation.</p>
                  <p className="text-[10px] text-charcoal/40 mt-1">Activities must be verified by a Project Manager or Admin to contribute to the official ledger.</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Activity Accounting & Verification Health Breakdown */}
          {projectImpact?.activities_summary && (
            <Card className="bg-white border-charcoal/10 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold font-manrope text-charcoal flex items-center gap-2">
                  <Activity className="w-4 h-4 text-forest" />
                  Operational Activity Accounting & Verification Audit
                </CardTitle>
                <CardDescription className="text-xs">
                  Immutable revision state breakdown ensuring zero double-counting.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2">
                  <div className="p-3 bg-ivory/50 rounded-lg border border-charcoal/5">
                    <span className="text-[10px] text-charcoal/50 uppercase font-semibold block">Total Submissions</span>
                    <p className="text-lg font-bold font-mono text-charcoal mt-1">
                      {projectImpact.activities_summary.total_activities_count}
                    </p>
                    <span className="text-[10px] text-charcoal/50">Recorded activities</span>
                  </div>

                  <div className="p-3 bg-forest/5 rounded-lg border border-forest/15">
                    <span className="text-[10px] text-forest uppercase font-semibold block">Active Verified</span>
                    <p className="text-lg font-bold font-mono text-forest mt-1">
                      {projectImpact.activities_summary.verified_active_revisions_count}
                    </p>
                    <span className="text-[10px] text-forest/70">In official ledger</span>
                  </div>

                  <div className="p-3 bg-earth/10 rounded-lg border border-earth/20">
                    <span className="text-[10px] text-earth uppercase font-semibold block">Pending Review</span>
                    <p className="text-lg font-bold font-mono text-earth mt-1">
                      {projectImpact.activities_summary.pending_revisions_count}
                    </p>
                    <span className="text-[10px] text-earth/70">Awaiting verification</span>
                  </div>

                  <div className="p-3 bg-crimson/5 rounded-lg border border-crimson/15">
                    <span className="text-[10px] text-crimson uppercase font-semibold block">Current Rejected</span>
                    <p className="text-lg font-bold font-mono text-crimson mt-1">
                      {projectImpact.activities_summary.current_rejected_revisions_count}
                    </p>
                    <span className="text-[10px] text-crimson/70">Not contributing</span>
                  </div>

                  <div className="p-3 bg-charcoal/5 rounded-lg border border-charcoal/10">
                    <span className="text-[10px] text-charcoal/60 uppercase font-semibold block">Historical Rejections</span>
                    <p className="text-lg font-bold font-mono text-charcoal mt-1">
                      {projectImpact.historical_rejected_count}
                    </p>
                    <span className="text-[10px] text-charcoal/50">Audit log events</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Activity History & Field Operations Integration */}
          <Card className="bg-white border-charcoal/10 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div>
                <CardTitle className="text-sm font-bold font-manrope text-charcoal flex items-center gap-2">
                  <Activity className="w-4 h-4 text-forest" />
                  Recent Field Activity & Verification History
                </CardTitle>
                <CardDescription className="text-xs">
                  Field reports submitted for this project and their current verification status.
                </CardDescription>
              </div>
              <Link to="/operations">
                <Button variant="outline" size="sm" className="h-7 text-xs border-forest/20 text-forest">
                  Open Operations Module
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {isLoadingActivities ? (
                <div className="p-6 text-center text-xs text-charcoal/60">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto text-forest mb-2" />
                  Loading field activities...
                </div>
              ) : projectActivities.length === 0 ? (
                <div className="p-6 text-center text-xs text-charcoal/50 bg-ivory/30 rounded-lg">
                  No field activities submitted for this project yet. Field officers can submit reports in the Field Operations module.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-charcoal/10 text-charcoal/50 font-semibold text-left">
                        <th className="pb-2">Metric</th>
                        <th className="pb-2">Reported Qty</th>
                        <th className="pb-2">Activity Date</th>
                        <th className="pb-2">Status</th>
                        <th className="pb-2">Revision</th>
                        <th className="pb-2">Submitter</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-charcoal/5">
                      {projectActivities.slice(0, 10).map((act) => {
                        const curRev = act.current_revision;
                        const statusColors: Record<string, string> = {
                          VERIFIED: "bg-forest/10 text-forest border-forest/20",
                          PENDING: "bg-earth/15 text-earth border-earth/30",
                          REJECTED: "bg-crimson/10 text-crimson border-crimson/20",
                        };
                        return (
                          <tr key={act.id} className="hover:bg-ivory/40">
                            <td className="py-2.5 font-mono font-semibold text-charcoal">
                              {act.metric_code}
                            </td>
                            <td className="py-2.5 font-mono">
                              {curRev ? `${curRev.quantity} ${act.unit}` : `— ${act.unit}`}
                            </td>
                            <td className="py-2.5 text-charcoal/70">
                              {curRev?.activity_date || "—"}
                            </td>
                            <td className="py-2.5">
                              <Badge
                                variant="outline"
                                className={`text-[10px] font-semibold ${
                                  curRev ? statusColors[curRev.status] || "" : ""
                                }`}
                              >
                                {curRev?.status || "PENDING"}
                              </Badge>
                            </td>
                            <td className="py-2.5 font-mono text-charcoal/60">
                              v{curRev?.revision_number || 1}
                            </td>
                            <td className="py-2.5 text-charcoal/70">
                              {act.created_by_name || "Field Officer"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB 4: TEAM ROSTER */}
      {activeTab === "team" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold font-manrope text-charcoal">
                Project Team Allocations
              </h2>
              <p className="text-xs text-charcoal/70">
                Authorized Project Managers and Field Officers assigned to this project roster.
              </p>
            </div>

            {canManage && (
              <Button
                size="sm"
                onClick={() => {
                  setActionError(null);
                  resetAssignment();
                  setAssignModalOpen(true);
                }}
                className="bg-forest text-white hover:bg-forest/90"
              >
                <UserPlus className="w-4 h-4 mr-1.5" />
                Assign Member
              </Button>
            )}
          </div>

          <div className="bg-white rounded-xl border border-charcoal/10 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="bg-ivory/80 border-b border-charcoal/10 text-xs font-semibold text-charcoal/70">
                    <th className="py-3 px-4">Member Name</th>
                    <th className="py-3 px-4">Email Address</th>
                    <th className="py-3 px-4">Project Role</th>
                    <th className="py-3 px-4">Account Status</th>
                    <th className="py-3 px-4">Assigned On</th>
                    {canManage && <th className="py-3 px-4 text-right">Action</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-charcoal/10 text-charcoal">
                  {project.assignments?.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-xs text-charcoal/50">
                        No team members currently allocated to this project.
                      </td>
                    </tr>
                  ) : (
                    project.assignments.map((member: ProjectAssignment) => (
                      <tr key={member.id} className="hover:bg-forest/5 transition-colors">
                        <td className="py-3 px-4 font-medium text-charcoal">
                          {member.user_full_name || "N/A"}
                        </td>
                        <td className="py-3 px-4 text-xs text-charcoal/70">
                          {member.user_email}
                        </td>
                        <td className="py-3 px-4">
                          <Badge
                            className={
                              member.assigned_role === "PROJECT_MANAGER"
                                ? "bg-forest text-white"
                                : "bg-sage/20 text-forest border-sage"
                            }
                          >
                            {member.assigned_role.replace("_", " ")}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-xs">
                          {member.user_is_active ? (
                            <span className="text-forest font-semibold flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Active
                            </span>
                          ) : (
                            <span className="text-crimson font-semibold">Deactivated</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-xs text-charcoal/60">
                          {new Date(member.assigned_at).toLocaleDateString()}
                        </td>
                        {canManage && (
                          <td className="py-3 px-4 text-right">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                if (
                                  confirm(
                                    `Remove ${member.user_full_name || member.user_email} from this project?`
                                  )
                                ) {
                                  removeAssignmentMutation.mutate(member.user_id);
                                }
                              }}
                              className="h-7 text-xs border-crimson/20 text-crimson hover:bg-crimson/5"
                            >
                              Remove
                            </Button>
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: GEOGRAPHIC INFORMATION */}
      {activeTab === "geography" && (
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-bold font-manrope text-charcoal">
              Geographic Coordinates & Boundaries
            </h2>
            <p className="text-xs text-charcoal/70">
              Spatial reference and verified boundary polygon in native PostgreSQL JSONB format.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="bg-white border-charcoal/10 shadow-sm">
              <CardHeader>
                <CardTitle className="text-base font-bold font-manrope text-charcoal flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-forest" />
                  Center Coordinate Point
                </CardTitle>
                <CardDescription className="text-xs">
                  Official project centroid used for mapping clusters and localized activity scoping.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-ivory/60 rounded-lg border border-charcoal/10">
                    <span className="text-[11px] font-semibold text-charcoal/50 uppercase">Latitude</span>
                    <p className="text-lg font-mono font-bold text-forest mt-1">
                      {project.latitude.toFixed(6)}°
                    </p>
                  </div>
                  <div className="p-3 bg-ivory/60 rounded-lg border border-charcoal/10">
                    <span className="text-[11px] font-semibold text-charcoal/50 uppercase">Longitude</span>
                    <p className="text-lg font-mono font-bold text-forest mt-1">
                      {project.longitude.toFixed(6)}°
                    </p>
                  </div>
                </div>

                <div className="p-3 bg-ivory/40 rounded-lg border border-charcoal/10 text-xs text-charcoal/70 space-y-1">
                  <p><strong>Hemisphere:</strong> {project.latitude >= 0 ? "Northern" : "Southern"} / {project.longitude >= 0 ? "Eastern" : "Western"}</p>
                  <p><strong>Coordinate Range Validity:</strong> [-90..90, -180..180] Verified</p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white border-charcoal/10 shadow-sm">
              <CardHeader>
                <CardTitle className="text-base font-bold font-manrope text-charcoal flex items-center gap-2">
                  <Globe className="w-4 h-4 text-forest" />
                  Boundary Geometry Metadata
                </CardTitle>
                <CardDescription className="text-xs">
                  Standard RFC 7946 GeoJSON Polygon specification.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                {project.boundary_geojson ? (
                  <>
                    <div className="flex justify-between py-1.5 border-b border-charcoal/10">
                      <span className="text-charcoal/60">Geometry Type:</span>
                      <span className="font-semibold text-forest font-mono">
                        {project.boundary_geojson.type}
                      </span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-charcoal/10">
                      <span className="text-charcoal/60">Rings Count:</span>
                      <span className="font-semibold text-charcoal font-mono">
                        {project.boundary_geojson.coordinates.length} Linear Ring(s)
                      </span>
                    </div>
                    <div className="flex justify-between py-1.5 border-b border-charcoal/10">
                      <span className="text-charcoal/60">Exterior Vertices:</span>
                      <span className="font-semibold text-charcoal font-mono">
                        {project.boundary_geojson.coordinates[0]?.length || 0} Points (Closed Ring)
                      </span>
                    </div>
                  </>
                ) : (
                  <div className="p-4 bg-ivory text-center rounded-lg text-charcoal/60">
                    No boundary polygon has been submitted for this project.
                    The system operates with point-radius coordinates.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Raw GeoJSON Viewer */}
          {project.boundary_geojson && (
            <Card className="bg-white border-charcoal/10 shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-bold font-manrope text-charcoal flex items-center gap-2">
                    <Layers className="w-4 h-4 text-forest" />
                    Boundary GeoJSON Payload
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Native JSONB storage representation in PostgreSQL.
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(project.boundary_geojson, null, 2));
                    alert("GeoJSON copied to clipboard!");
                  }}
                  className="text-xs border-charcoal/20"
                >
                  <Copy className="w-3.5 h-3.5 mr-1" /> Copy JSON
                </Button>
              </CardHeader>
              <CardContent>
                <pre className="p-3 bg-charcoal text-ivory rounded-lg text-xs font-mono overflow-x-auto max-h-60">
                  {JSON.stringify(project.boundary_geojson, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Target Modal (Add / Edit) */}
      <Dialog open={targetModalOpen} onOpenChange={setTargetModalOpen}>
        <DialogContent className="sm:max-w-[480px] bg-white border-charcoal/15">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold font-manrope text-charcoal flex items-center gap-2">
              <Target className="w-5 h-5 text-forest" />
              {editingTargetId ? "Edit Environmental Target" : "Define Environmental Target"}
            </DialogTitle>
            <DialogDescription className="text-xs text-charcoal/70">
              Dimensional conservation targets anchored to approved metrics and units.
            </DialogDescription>
          </DialogHeader>

          {actionError && (
            <div className="p-2.5 bg-crimson/10 border border-crimson/20 rounded-lg text-xs text-crimson flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{actionError}</span>
            </div>
          )}

          <form
            onSubmit={handleTargetSubmit((data) => {
              if (editingTargetId) {
                updateTargetMutation.mutate(data);
              } else {
                createTargetMutation.mutate(data);
              }
            })}
            className="space-y-4 py-2"
          >
            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Environmental Metric <span className="text-crimson">*</span>
              </label>
              <select
                {...registerTarget("metric_code")}
                disabled={!!editingTargetId}
                onChange={(e) => {
                  const m = metricsCatalog.find((x) => x.metric_code === e.target.value);
                  setTargetValue("metric_code", e.target.value);
                  if (m && m.supported_units[0]) {
                    setTargetValue("target_unit", m.supported_units[0]);
                  }
                }}
                className="w-full text-sm rounded-lg border border-charcoal/20 px-3 py-2 bg-white text-charcoal focus:outline-none focus:border-forest disabled:bg-ivory/70"
              >
                {metricsCatalog.map((m) => (
                  <option key={m.metric_code} value={m.metric_code}>
                    {m.display_name} ({m.category})
                  </option>
                ))}
              </select>
            </div>

            {selectedMetricDef && (
              <div className="p-2.5 bg-ivory/80 rounded-lg border border-charcoal/10 text-xs space-y-1">
                <p>
                  <strong>Dimension:</strong> {selectedMetricDef.dimension} | <strong>Base Unit:</strong>{" "}
                  {selectedMetricDef.canonical_unit}
                </p>
                <p className="text-[11px] text-charcoal/60">
                  {selectedMetricDef.methodology_summary}
                </p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-charcoal mb-1">
                  Target Quantity <span className="text-crimson">*</span>
                </label>
                <Input
                  type="number"
                  step="any"
                  {...registerTarget("target_quantity")}
                  className="text-sm font-mono"
                />
                {targetErrors.target_quantity && (
                  <p className="text-xs text-crimson mt-1">
                    {targetErrors.target_quantity.message}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-charcoal mb-1">
                  Measurement Unit <span className="text-crimson">*</span>
                </label>
                <select
                  {...registerTarget("target_unit")}
                  className="w-full text-sm rounded-lg border border-charcoal/20 px-3 py-2 bg-white text-charcoal focus:outline-none focus:border-forest"
                >
                  {(selectedMetricDef?.supported_units || ["trees"]).map((u) => (
                    <option key={u} value={u}>
                      {u}
                    </option>
                  ))}
                </select>
                {targetErrors.target_unit && (
                  <p className="text-xs text-crimson mt-1">{targetErrors.target_unit.message}</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Target Deadline <span className="text-crimson">*</span>
              </label>
              <Input
                type="date"
                {...registerTarget("target_date")}
                className="text-sm font-mono"
              />
              {targetErrors.target_date && (
                <p className="text-xs text-crimson mt-1">{targetErrors.target_date.message}</p>
              )}
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setTargetModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isSubmittingTarget}
                className="bg-forest text-white"
              >
                {isSubmittingTarget ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : editingTargetId ? (
                  "Update Target"
                ) : (
                  "Save Target"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Project Modal */}
      <Dialog open={editProjectModalOpen} onOpenChange={setEditProjectModalOpen}>
        <DialogContent className="sm:max-w-[500px] bg-white border-charcoal/15">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold font-manrope text-charcoal">
              Edit Project Details
            </DialogTitle>
          </DialogHeader>

          {actionError && (
            <div className="p-2.5 bg-crimson/10 border border-crimson/20 rounded-lg text-xs text-crimson flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{actionError}</span>
            </div>
          )}

          <form onSubmit={handleEditProjectSubmit((data) => updateProjectMutation.mutate(data))} className="space-y-4 py-2">
            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Project Name
              </label>
              <Input {...registerEditProject("name")} className="text-sm" />
              {editProjectErrors.name && (
                <p className="text-xs text-crimson mt-1">{editProjectErrors.name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Status
              </label>
              <select
                {...registerEditProject("status")}
                className="w-full text-sm rounded-lg border border-charcoal/20 px-3 py-2 bg-white text-charcoal focus:outline-none focus:border-forest"
              >
                <option value="ACTIVE">ACTIVE</option>
                <option value="DRAFT">DRAFT</option>
                <option value="COMPLETED">COMPLETED</option>
                <option value="ARCHIVED">ARCHIVED</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Description
              </label>
              <textarea
                {...registerEditProject("description")}
                rows={2}
                className="w-full text-sm rounded-lg border border-charcoal/20 p-2.5 bg-white text-charcoal focus:outline-none focus:border-forest"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-charcoal mb-1">
                  Latitude
                </label>
                <Input type="number" step="any" {...registerEditProject("latitude")} className="text-sm font-mono" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-charcoal mb-1">
                  Longitude
                </label>
                <Input type="number" step="any" {...registerEditProject("longitude")} className="text-sm font-mono" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                GeoJSON Boundary Polygon
              </label>
              <textarea
                {...registerEditProject("polygonText")}
                rows={3}
                className="w-full text-xs font-mono rounded-lg border border-charcoal/20 p-2 bg-ivory/50 text-charcoal focus:outline-none focus:border-forest"
              />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setEditProjectModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isSubmittingEditProject} className="bg-forest text-white">
                {isSubmittingEditProject ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save Changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Assign Team Member Modal */}
      <Dialog open={assignModalOpen} onOpenChange={setAssignModalOpen}>
        <DialogContent className="sm:max-w-[450px] bg-white border-charcoal/15">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold font-manrope text-charcoal flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-forest" />
              Assign Team Member
            </DialogTitle>
            <DialogDescription className="text-xs text-charcoal/70">
              Select an active user to allocate to this project roster.
            </DialogDescription>
          </DialogHeader>

          {actionError && (
            <div className="p-2.5 bg-crimson/10 border border-crimson/20 rounded-lg text-xs text-crimson flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{actionError}</span>
            </div>
          )}

          <form onSubmit={handleAssignmentSubmit((data) => assignMutation.mutate(data))} className="space-y-4 py-2">
            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Select Personnel <span className="text-crimson">*</span>
              </label>
              <select
                {...registerAssignment("user_id")}
                className="w-full text-sm rounded-lg border border-charcoal/20 px-3 py-2 bg-white text-charcoal focus:outline-none focus:border-forest"
              >
                <option value="">-- Choose User --</option>
                {orgUsers
                  .filter((u) => u.is_active && !project.assignments?.some((a) => a.user_id === u.id))
                  .map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.email}) - {u.role}
                    </option>
                  ))}
              </select>
              {assignErrors.user_id && (
                <p className="text-xs text-crimson mt-1">{assignErrors.user_id.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Assigned Project Role <span className="text-crimson">*</span>
              </label>
              <select
                {...registerAssignment("assigned_role")}
                className="w-full text-sm rounded-lg border border-charcoal/20 px-3 py-2 bg-white text-charcoal focus:outline-none focus:border-forest"
              >
                <option value="FIELD_OFFICER">FIELD OFFICER</option>
                <option value="PROJECT_MANAGER">PROJECT MANAGER</option>
              </select>
              {assignErrors.assigned_role && (
                <p className="text-xs text-crimson mt-1">{assignErrors.assigned_role.message}</p>
              )}
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setAssignModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isSubmittingAssign} className="bg-forest text-white">
                {isSubmittingAssign ? <Loader2 className="w-4 h-4 animate-spin" /> : "Confirm Allocation"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
};
