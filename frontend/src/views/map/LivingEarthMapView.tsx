import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { analyticsService } from "@/services/analytics";
import { LivingEarthMap } from "@/components/map/LivingEarthMap";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, MapPin, ExternalLink, Layers, ArrowLeft } from "lucide-react";
import type { ProjectProgressItem } from "@/types/analytics";

export const LivingEarthMapView: React.FC = () => {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [selectedProject, setSelectedProject] = useState<ProjectProgressItem | null>(null);

  const { data: projectsData, isLoading } = useQuery({
    queryKey: ["dashboard", "projects", statusFilter, search],
    queryFn: () =>
      analyticsService.getDashboardProjects({
        status: statusFilter === "ALL" ? undefined : statusFilter,
        search: search || undefined,
      }),
  });

  const projects = projectsData?.projects || [];

  return (
    <div className="space-y-4 pb-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-forest/10 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <Link to="/dashboard">
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-charcoal/60 hover:text-forest">
                <ArrowLeft className="w-4 h-4" />
              </Button>
            </Link>
            <h1 className="text-xl font-bold font-manrope text-forest tracking-tight flex items-center gap-2">
              <Layers className="w-5 h-5 text-forest" />
              Living Earth — Interactive Project Map
            </h1>
          </div>
          <p className="text-xs text-charcoal/70 mt-0.5 ml-9">
            Geospatial representation of conservation, afforestation, and water harvesting projects.
          </p>
        </div>

        {/* Filter Toolbar */}
        <div className="flex items-center gap-2 ml-9 sm:ml-0">
          <div className="relative w-48">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-charcoal/40" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search projects..."
              className="h-8 pl-8 text-xs bg-white"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-8 px-2.5 text-xs rounded-md border border-forest/20 bg-white text-charcoal font-medium"
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="COMPLETED">Completed</option>
            <option value="DRAFT">Draft</option>
          </select>
        </div>
      </div>

      {/* Main Map & Inspection Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Map Canvas */}
        <div className="lg:col-span-8">
          <LivingEarthMap
            projects={projects}
            height="560px"
            selectedProjectId={selectedProject?.id}
            onSelectProject={(p) => setSelectedProject(p)}
          />
        </div>

        {/* Selected Project Inspection Drawer / Project List */}
        <div className="lg:col-span-4 space-y-4">
          {selectedProject ? (
            <Card className="border-forest/20 shadow-sm animate-in fade-in duration-200">
              <CardHeader className="pb-3 border-b border-forest/10">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <CardTitle className="text-base font-manrope text-forest font-bold">
                      {selectedProject.name}
                    </CardTitle>
                    <span className="font-mono text-xs text-charcoal/60">
                      {selectedProject.code}
                    </span>
                  </div>
                  <Badge variant="outline" className="text-xs uppercase font-semibold">
                    {selectedProject.status}
                  </Badge>
                </div>
                {selectedProject.description && (
                  <CardDescription className="text-xs text-charcoal/80 pt-1">
                    {selectedProject.description}
                  </CardDescription>
                )}
              </CardHeader>

              <CardContent className="pt-4 space-y-4">
                <div className="flex items-center gap-2 text-xs text-charcoal/70 bg-forest/5 p-2 rounded-lg">
                  <MapPin className="w-4 h-4 text-forest shrink-0" />
                  <span>
                    Lat: {selectedProject.latitude?.toFixed(4)}, Lng: {selectedProject.longitude?.toFixed(4)}
                  </span>
                </div>

                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-charcoal/60">
                    Verified Target Progress
                  </p>
                  {selectedProject.targets.length === 0 ? (
                    <p className="text-xs text-charcoal/50 italic">No targets defined for this project.</p>
                  ) : (
                    <div className="space-y-2.5">
                      {selectedProject.targets.map((t) => (
                        <div key={t.target_id} className="p-2.5 rounded-lg border border-forest/10 bg-ivory/30 space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="font-medium text-forest">{t.metric_name}</span>
                            <span className="font-bold text-forest">{t.achievement_percentage}%</span>
                          </div>
                          <div className="h-1.5 w-full bg-forest/10 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-forest rounded-full"
                              style={{ width: `${Math.min(100, Math.max(0, t.achievement_percentage))}%` }}
                            />
                          </div>
                          <div className="flex justify-between text-[11px] text-charcoal/60 pt-0.5">
                            <span>Verified: {Number(t.verified_quantity).toLocaleString()} {t.target_unit}</span>
                            <span>Target: {Number(t.target_quantity).toLocaleString()}</span>
                          </div>
                          {Number(t.net_pending_adjustment) !== 0 && (
                            <p className="text-[10px] text-amber-800 font-medium pt-0.5">
                              Pending net claim: {Number(t.net_pending_adjustment) > 0 ? "+" : ""}
                              {Number(t.net_pending_adjustment).toLocaleString()} {t.target_unit}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="pt-2 border-t border-forest/10 flex items-center justify-between">
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-xs h-8"
                    onClick={() => setSelectedProject(null)}
                  >
                    Clear Selection
                  </Button>
                  <Link to={`/projects/${selectedProject.id}`}>
                    <Button size="sm" className="bg-forest text-white hover:bg-forest/90 text-xs h-8">
                      Open Workspace <ExternalLink className="w-3.5 h-3.5 ml-1" />
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-forest/15 shadow-sm">
              <CardHeader className="pb-3 border-b border-forest/10">
                <CardTitle className="text-sm font-manrope text-forest font-bold">
                  Intervention Directory ({projects.length})
                </CardTitle>
                <CardDescription className="text-xs text-charcoal/60">
                  Click any project pin or row to view localized impact
                </CardDescription>
              </CardHeader>
              <CardContent className="p-2 max-h-[480px] overflow-y-auto divide-y divide-forest/5">
                {isLoading ? (
                  <div className="p-6 text-center text-xs text-charcoal/50">Loading projects...</div>
                ) : projects.length === 0 ? (
                  <div className="p-6 text-center text-xs text-charcoal/50">No matching projects.</div>
                ) : (
                  projects.map((p) => (
                    <div
                      key={p.id}
                      onClick={() => setSelectedProject(p)}
                      className="p-2.5 rounded-lg hover:bg-forest/5 cursor-pointer transition-colors space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-xs text-forest">{p.name}</span>
                        <Badge variant="outline" className="text-[10px] h-4 uppercase">
                          {p.status}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-charcoal/60">
                        <span className="font-mono text-[10px]">{p.code}</span>
                        <span>
                          {p.overall_achievement_percentage !== null
                            ? `${p.overall_achievement_percentage}% progress`
                            : "No targets"}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
