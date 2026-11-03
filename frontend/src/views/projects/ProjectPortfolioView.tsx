import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { listProjects, createProject } from "@/services/projects";
import { useAuth } from "@/context/AuthContext";
import { Project, ProjectStatus } from "@/types/projects";
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
  Plus,
  Search,
  Filter,
  MapPin,
  Users,
  Target,
  ArrowRight,
  RefreshCw,
  AlertCircle,
  Loader2,
  LayoutGrid,
  List as ListIcon,
} from "lucide-react";

const createProjectSchema = z.object({
  name: z.string().trim().min(3, "Project name must be at least 3 characters"),
  code: z
    .string()
    .trim()
    .regex(/^[A-Z0-9_\-]*$/, "Code must be uppercase alphanumeric, dashes, or underscores")
    .optional()
    .or(z.literal("")),
  description: z.string().trim().optional(),
  status: z.enum(["ACTIVE", "DRAFT", "COMPLETED", "ARCHIVED"] as const),
  latitude: z.coerce.number().min(-90, "Latitude must be >= -90").max(90, "Latitude must be <= 90"),
  longitude: z.coerce.number().min(-180, "Longitude must be >= -180").max(180, "Longitude must be <= 180"),
  polygonText: z.string().trim().optional(),
});

type CreateProjectFormData = z.infer<typeof createProjectSchema>;

export const ProjectPortfolioView: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const isAdmin = user?.role === "ADMIN";

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateProjectFormData>({
    resolver: zodResolver(createProjectSchema),
    defaultValues: {
      name: "",
      code: "",
      description: "",
      status: "ACTIVE",
      latitude: 21.9497,
      longitude: 89.1833,
      polygonText: "",
    },
  });

  const {
    data: projects = [],
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["projects", searchTerm, selectedStatus],
    queryFn: () =>
      listProjects({
        search: searchTerm || undefined,
        status: selectedStatus === "ALL" ? undefined : selectedStatus,
      }),
  });

  const createMutation = useMutation({
    mutationFn: async (data: CreateProjectFormData) => {
      let boundaryGeojson = undefined;
      if (data.polygonText && data.polygonText.trim()) {
        try {
          boundaryGeojson = JSON.parse(data.polygonText);
        } catch {
          throw new Error("Invalid GeoJSON polygon format. Must be valid JSON.");
        }
      }
      return createProject({
        name: data.name,
        code: data.code || undefined,
        description: data.description || undefined,
        status: data.status as ProjectStatus,
        latitude: data.latitude,
        longitude: data.longitude,
        boundary_geojson: boundaryGeojson,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setDialogOpen(false);
      reset();
      setActionError(null);
    },
    onError: (err: any) => {
      const msg =
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        err.message ||
        "Failed to create project.";
      setActionError(msg);
    },
  });

  const onSubmit = (data: CreateProjectFormData) => {
    setActionError(null);
    createMutation.mutate(data);
  };

  const getStatusBadge = (status: ProjectStatus) => {
    switch (status) {
      case "ACTIVE":
        return (
          <Badge className="bg-forest/10 text-forest border-forest/30 font-medium">
            Active
          </Badge>
        );
      case "COMPLETED":
        return (
          <Badge className="bg-sage/20 text-forest border-sage font-medium">
            Completed
          </Badge>
        );
      case "DRAFT":
        return (
          <Badge className="bg-ivory text-charcoal/70 border-charcoal/20 font-medium">
            Draft
          </Badge>
        );
      case "ARCHIVED":
        return (
          <Badge className="bg-charcoal/10 text-charcoal/50 border-charcoal/10 font-medium">
            Archived
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <PageContainer>
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FolderTree className="w-6 h-6 text-forest" />
            <h1 className="text-2xl font-bold font-manrope text-charcoal">
              Environmental Project Portfolio
            </h1>
          </div>
          <p className="text-sm text-charcoal/70">
            {isAdmin
              ? "Organization-wide environmental initiatives, geographic boundaries, and target balance sheets."
              : "Assigned environmental initiatives and field operations workspaces."}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="border-charcoal/20 text-charcoal hover:bg-forest/5"
          >
            <RefreshCw
              className={`w-4 h-4 mr-2 ${isFetching ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>

          {isAdmin && (
            <Button
              size="sm"
              onClick={() => {
                reset();
                setActionError(null);
                setDialogOpen(true);
              }}
              className="bg-forest hover:bg-forest/90 text-white shadow-sm"
            >
              <Plus className="w-4 h-4 mr-2" />
              New Project
            </Button>
          )}
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-charcoal/10 shadow-sm mb-6 flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-charcoal/40" />
          <Input
            placeholder="Search projects or codes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 bg-ivory/50 border-charcoal/15 text-sm focus:border-forest"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <span className="text-xs font-semibold uppercase tracking-wider text-charcoal/50 mr-1 flex items-center">
            <Filter className="w-3 h-3 mr-1" /> Status:
          </span>
          {["ALL", "ACTIVE", "DRAFT", "COMPLETED", "ARCHIVED"].map((st) => (
            <button
              key={st}
              onClick={() => setSelectedStatus(st)}
              className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
                selectedStatus === st
                  ? "bg-forest text-white shadow-xs"
                  : "bg-ivory text-charcoal/70 hover:bg-forest/10"
              }`}
            >
              {st}
            </button>
          ))}

          <div className="h-4 w-px bg-charcoal/15 mx-1 hidden md:block" />

          {/* Grid vs Table toggle */}
          <div className="flex items-center border border-charcoal/15 rounded-lg overflow-hidden bg-ivory/40">
            <button
              onClick={() => setViewMode("grid")}
              className={`p-1.5 ${
                viewMode === "grid" ? "bg-forest text-white" : "text-charcoal/60 hover:text-charcoal"
              }`}
              title="Grid view"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode("table")}
              className={`p-1.5 ${
                viewMode === "table" ? "bg-forest text-white" : "text-charcoal/60 hover:text-charcoal"
              }`}
              title="Table view"
            >
              <ListIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse bg-white border-charcoal/10">
              <CardHeader className="space-y-2">
                <div className="h-5 bg-charcoal/10 rounded w-1/3" />
                <div className="h-6 bg-charcoal/10 rounded w-3/4" />
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="h-12 bg-charcoal/5 rounded" />
                <div className="h-4 bg-charcoal/10 rounded w-1/2" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : isError ? (
        <div className="p-8 text-center bg-crimson/5 border border-crimson/20 rounded-xl">
          <AlertCircle className="w-8 h-8 text-crimson mx-auto mb-2" />
          <h3 className="font-semibold text-charcoal">Unable to load projects</h3>
          <p className="text-sm text-charcoal/70 mt-1 mb-4">
            {(error as any)?.message || "Failed to communicate with project service."}
          </p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      ) : projects.length === 0 ? (
        <div className="text-center py-16 px-4 bg-white rounded-xl border border-charcoal/10 shadow-sm">
          <FolderTree className="w-12 h-12 text-forest/30 mx-auto mb-3" />
          <h3 className="text-lg font-bold font-manrope text-charcoal">
            No environmental projects found
          </h3>
          <p className="text-sm text-charcoal/60 max-w-md mx-auto mt-1 mb-6">
            {searchTerm || selectedStatus !== "ALL"
              ? "No projects match your search or status filter criteria. Try clearing filters."
              : "No projects exist in the registry yet. Create the first environmental initiative to begin."}
          </p>
          {searchTerm || selectedStatus !== "ALL" ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchTerm("");
                setSelectedStatus("ALL");
              }}
            >
              Clear Filters
            </Button>
          ) : isAdmin ? (
            <Button
              size="sm"
              onClick={() => setDialogOpen(true)}
              className="bg-forest text-white"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Project
            </Button>
          ) : null}
        </div>
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project: Project) => (
            <Card
              key={project.id}
              className="bg-white border-charcoal/10 hover:border-forest/40 hover:shadow-md transition-all flex flex-col justify-between"
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-xs font-mono font-bold text-forest bg-forest/5 px-2 py-0.5 rounded border border-forest/15">
                    {project.code}
                  </span>
                  {getStatusBadge(project.status)}
                </div>
                <CardTitle className="text-lg font-bold font-manrope text-charcoal leading-snug line-clamp-1">
                  {project.name}
                </CardTitle>
                <CardDescription className="text-xs text-charcoal/60 line-clamp-2 min-h-[2rem]">
                  {project.description || "No project description provided."}
                </CardDescription>
              </CardHeader>

              <CardContent className="pt-0 space-y-4">
                <div className="grid grid-cols-2 gap-2 text-xs text-charcoal/70 bg-ivory/60 p-2.5 rounded-lg border border-charcoal/5">
                  <div className="flex items-center gap-1.5">
                    <Target className="w-3.5 h-3.5 text-forest" />
                    <span>
                      <strong className="text-charcoal font-semibold">
                        {project.targets_count}
                      </strong>{" "}
                      Targets
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5 text-forest" />
                    <span>
                      <strong className="text-charcoal font-semibold">
                        {project.team_count}
                      </strong>{" "}
                      Staff
                    </span>
                  </div>
                  <div className="col-span-2 flex items-center gap-1.5 pt-1 border-t border-charcoal/10 font-mono text-[11px] text-charcoal/60">
                    <MapPin className="w-3.5 h-3.5 text-forest shrink-0" />
                    <span className="truncate">
                      {project.latitude.toFixed(4)}°, {project.longitude.toFixed(4)}°
                      {project.boundary_geojson && " (Polygon Defined)"}
                    </span>
                  </div>
                </div>

                <Link
                  to={`/projects/${project.id}`}
                  className="w-full inline-flex items-center justify-center gap-1 text-xs font-semibold py-2 px-3 rounded-lg bg-forest/5 text-forest hover:bg-forest hover:text-white transition-colors border border-forest/20"
                >
                  Open Workspace
                  <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-charcoal/10 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-ivory/80 border-b border-charcoal/10 text-xs font-semibold text-charcoal/70">
                  <th className="py-3 px-4">Code</th>
                  <th className="py-3 px-4">Project Name</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Coordinates</th>
                  <th className="py-3 px-4 text-center">Targets</th>
                  <th className="py-3 px-4 text-center">Team</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-charcoal/10 text-charcoal">
                {projects.map((p: Project) => (
                  <tr key={p.id} className="hover:bg-forest/5 transition-colors">
                    <td className="py-3 px-4 font-mono font-semibold text-xs text-forest">
                      {p.code}
                    </td>
                    <td className="py-3 px-4 font-medium text-charcoal">
                      {p.name}
                    </td>
                    <td className="py-3 px-4">{getStatusBadge(p.status)}</td>
                    <td className="py-3 px-4 text-xs font-mono text-charcoal/70">
                      {p.latitude.toFixed(4)}°, {p.longitude.toFixed(4)}°
                    </td>
                    <td className="py-3 px-4 text-center font-semibold text-xs">
                      {p.targets_count}
                    </td>
                    <td className="py-3 px-4 text-center font-semibold text-xs">
                      {p.team_count}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        to={`/projects/${p.id}`}
                        className="inline-flex items-center gap-1 text-xs font-medium text-forest hover:underline"
                      >
                        Workspace <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Project Creation Modal Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-[550px] bg-white border-charcoal/15">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold font-manrope text-charcoal flex items-center gap-2">
              <FolderTree className="w-5 h-5 text-forest" />
              Create Environmental Project
            </DialogTitle>
            <DialogDescription className="text-xs text-charcoal/70">
              Establish a new ecological restoration or conservation project with geographic coordinates.
            </DialogDescription>
          </DialogHeader>

          {actionError && (
            <div className="p-3 bg-crimson/10 border border-crimson/20 rounded-lg text-xs text-crimson flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{actionError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Project Name <span className="text-crimson">*</span>
              </label>
              <Input
                {...register("name")}
                placeholder="e.g. Sundarbans Mangrove Conservation"
                className="text-sm"
              />
              {errors.name && (
                <p className="text-xs text-crimson mt-1">{errors.name.message}</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-charcoal mb-1">
                  Project Code (Optional)
                </label>
                <Input
                  {...register("code")}
                  placeholder="e.g. VANA-SUNDAR-01"
                  className="text-sm font-mono uppercase"
                />
                {errors.code && (
                  <p className="text-xs text-crimson mt-1">{errors.code.message}</p>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-charcoal mb-1">
                  Initial Status
                </label>
                <select
                  {...register("status")}
                  className="w-full text-sm rounded-lg border border-charcoal/20 px-3 py-2 bg-white text-charcoal focus:outline-none focus:border-forest"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="DRAFT">DRAFT</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Project Description
              </label>
              <textarea
                {...register("description")}
                rows={2}
                placeholder="Key ecological goals, location details, or biomes..."
                className="w-full text-sm rounded-lg border border-charcoal/20 p-2.5 bg-white text-charcoal focus:outline-none focus:border-forest"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-charcoal mb-1">
                  Latitude (-90 to 90) <span className="text-crimson">*</span>
                </label>
                <Input
                  type="number"
                  step="any"
                  {...register("latitude")}
                  className="text-sm font-mono"
                />
                {errors.latitude && (
                  <p className="text-xs text-crimson mt-1">
                    {errors.latitude.message}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-charcoal mb-1">
                  Longitude (-180 to 180) <span className="text-crimson">*</span>
                </label>
                <Input
                  type="number"
                  step="any"
                  {...register("longitude")}
                  className="text-sm font-mono"
                />
                {errors.longitude && (
                  <p className="text-xs text-crimson mt-1">
                    {errors.longitude.message}
                  </p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Optional GeoJSON Boundary Polygon
              </label>
              <textarea
                {...register("polygonText")}
                rows={3}
                placeholder='{"type": "Polygon", "coordinates": [[[89.18, 21.94], [89.19, 21.94], [89.19, 21.95], [89.18, 21.95], [89.18, 21.94]]]}'
                className="w-full text-xs font-mono rounded-lg border border-charcoal/20 p-2 bg-ivory/50 text-charcoal focus:outline-none focus:border-forest"
              />
              <p className="text-[11px] text-charcoal/50 mt-0.5">
                Standard GeoJSON Polygon with closed ring (first coordinate equals last coordinate).
              </p>
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setDialogOpen(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isSubmitting}
                className="bg-forest text-white hover:bg-forest/90"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating Project...
                  </>
                ) : (
                  "Create Project"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
};
