import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { analyticsService } from "@/services/analytics";
import { KPICard } from "@/components/dashboard/KPICard";
import { EnvironmentalImpactChart } from "@/components/dashboard/EnvironmentalImpactChart";
import { AttentionProjectsList } from "@/components/dashboard/AttentionProjectsList";
import { RecentActivityFeed } from "@/components/dashboard/RecentActivityFeed";
import { LivingEarthMap } from "@/components/map/LivingEarthMap";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  FolderKanban,
  Clock,
  Layers,
  Search,
  ExternalLink,
  Map as MapIcon,
  ShieldCheck,
  PlusCircle,
  Sparkles,
} from "lucide-react";

export const OrganizationDashboardView: React.FC = () => {
  const { user } = useAuth();
  const [projectSearch, setProjectSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  // Query 1: Dashboard Overview
  const {
    data: overview,
    isLoading: isOverviewLoading,
    error: overviewError,
  } = useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: () => analyticsService.getDashboardOverview(),
    staleTime: 30000,
  });

  // Query 2: Projects with Target Progress
  const {
    data: projectsData,
    isLoading: isProjectsLoading,
  } = useQuery({
    queryKey: ["dashboard", "projects", statusFilter, projectSearch],
    queryFn: () =>
      analyticsService.getDashboardProjects({
        status: statusFilter === "ALL" ? undefined : statusFilter,
        search: projectSearch || undefined,
      }),
    staleTime: 30000,
  });

  // Query 3: Recent Activity Stream
  const {
    data: recentActivity = [],
  } = useQuery({
    queryKey: ["dashboard", "recent-activity"],
    queryFn: () => analyticsService.getRecentActivity(15),
    staleTime: 30000,
  });

  const projects = projectsData?.projects || [];

  return (
    <div className="space-y-6 pb-12">
      {/* 1. Header & Role Scoping Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-forest/10 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold font-manrope text-forest tracking-tight">
              Environmental Operations Dashboard
            </h1>
            <Badge
              variant="outline"
              className="text-xs bg-forest/5 text-forest border-forest/20 capitalize font-medium"
            >
              {overview?.is_portfolio_wide
                ? "Organization-Wide (Admin)"
                : `Scoped View (${user?.role.replace("_", " ")})`}
            </Badge>
          </div>
          <p className="text-xs text-charcoal/70 mt-1 max-w-2xl">
            Real-time environmental intelligence, verified ledger rollups, and operational velocity across active intervention zones.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {user?.role !== "FIELD_OFFICER" && (
            <Link to="/verification">
              <Button
                variant="outline"
                size="sm"
                className="text-xs border-forest/20 text-forest hover:bg-forest/5 relative"
              >
                <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-700" />
                Verification Centre
                {overview && overview.total_pending_verifications > 0 && (
                  <span className="ml-1.5 px-1.5 py-0.2 rounded-full text-[10px] bg-amber-100 text-amber-900 font-bold border border-amber-300">
                    {overview.total_pending_verifications}
                  </span>
                )}
              </Button>
            </Link>
          )}

          <Link to="/operations">
            <Button size="sm" className="bg-forest text-white hover:bg-forest/90 text-xs shadow-xs">
              <PlusCircle className="w-3.5 h-3.5 mr-1" />
              Report Field Activity
            </Button>
          </Link>
        </div>
      </div>

      {overviewError && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center justify-between">
          <span>Failed to load live environmental ledger rollups from PostgreSQL backend.</span>
          <Button variant="outline" size="sm" onClick={() => window.location.reload()} className="text-xs h-7">
            Retry
          </Button>
        </div>
      )}

      {/* 2. Top Executive KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          title="Total Projects"
          value={isOverviewLoading ? "..." : (overview?.total_projects ?? 0)}
          subtitle="Portfolio count"
          icon={<FolderKanban className="w-5 h-5" />}
        />
        <KPICard
          title="Active Interventions"
          value={isOverviewLoading ? "..." : (overview?.active_projects ?? 0)}
          subtitle={`${overview?.completed_projects ?? 0} completed`}
          icon={<Layers className="w-5 h-5 text-emerald-700" />}
          badge={{ text: `${overview?.active_projects ?? 0} active`, variant: "success" }}
        />
        <KPICard
          title="Pending Verification"
          value={isOverviewLoading ? "..." : (overview?.total_pending_verifications ?? 0)}
          subtitle="Awaiting review"
          icon={<Clock className="w-5 h-5 text-amber-700" />}
          badge={
            overview && overview.total_pending_verifications > 0
              ? { text: "Action Needed", variant: "warning" }
              : { text: "Queue Clear", variant: "success" }
          }
        />
        <KPICard
          title="Projects Needing Attention"
          value={isOverviewLoading ? "..." : (overview?.attention_projects.length ?? 0)}
          subtitle="Operational alerts"
          icon={<Sparkles className="w-5 h-5 text-gold" />}
          badge={
            overview && overview.attention_projects.length > 0
              ? { text: "Review Below", variant: "warning" }
              : { text: "On Track", variant: "success" }
          }
        />
      </div>

      {/* 3. Verified Environmental Achievements (Metric by Metric - Highest Priority) */}
      <Card className="border-forest/15 shadow-sm">
        <CardHeader className="pb-3 border-b border-forest/10">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <CardTitle className="text-base font-manrope text-forest font-bold">
                Official Environmental Achievements (Active Ledger)
              </CardTitle>
              <CardDescription className="text-xs text-charcoal/70">
                Calculated strictly from approved active revisions (Rule 7: Verified-Only Official Achievements)
              </CardDescription>
            </div>
            <span className="text-[11px] text-charcoal/50 italic">
              Units isolated by metric code
            </span>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {isOverviewLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-28 rounded-xl bg-forest/5 animate-pulse" />
              ))}
            </div>
          ) : overview?.metric_achievements.length === 0 ? (
            <div className="py-8 text-center text-charcoal/60 text-xs">
              No active targets or verified activities recorded yet in the system of record.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {overview?.metric_achievements.map((m) => (
                <div
                  key={m.metric_code}
                  className="p-4 rounded-xl border border-forest/10 bg-ivory/40 hover:bg-ivory/80 transition-colors space-y-2"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-charcoal/60">
                        {m.category.replace("_", " ")}
                      </span>
                      <h4 className="text-sm font-bold font-manrope text-forest">
                        {m.display_name}
                      </h4>
                    </div>
                    <Badge variant="outline" className="text-[10px] h-4 font-mono text-charcoal/70">
                      {m.canonical_unit}
                    </Badge>
                  </div>

                  <div className="pt-1">
                    <div className="text-xl font-bold font-manrope text-forest">
                      {Number(m.total_verified_quantity).toLocaleString()}{" "}
                      <span className="text-xs font-normal text-charcoal/60">
                        {m.canonical_unit}
                      </span>
                    </div>

                    {m.total_target_quantity !== null && (
                      <p className="text-[11px] text-charcoal/60 mt-0.5">
                        Target: {Number(m.total_target_quantity).toLocaleString()} {m.canonical_unit}
                        {m.overall_achievement_percentage !== null && (
                          <span className="ml-1 font-semibold text-forest">
                            ({m.overall_achievement_percentage}%)
                          </span>
                        )}
                      </p>
                    )}

                    {Number(m.total_pending_adjustment) !== 0 && (
                      <div className="mt-2 text-[11px] font-medium text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200/60 inline-flex items-center gap-1">
                        <span>Pending Net:</span>
                        <span>
                          {Number(m.total_pending_adjustment) > 0 ? "+" : ""}
                          {Number(m.total_pending_adjustment).toLocaleString()} {m.canonical_unit}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 4. Middle Section: Impact Charts and Interactive Living Earth Map */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7">
          <EnvironmentalImpactChart
            metrics={overview?.metric_achievements || []}
            className="h-full"
          />
        </div>
        <div className="lg:col-span-5">
          <Card className="h-full flex flex-col border-forest/15 shadow-sm">
            <CardHeader className="pb-3 border-b border-forest/10">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-manrope text-forest font-bold flex items-center gap-2">
                    <MapIcon className="w-4 h-4 text-forest" />
                    Living Earth Project Map
                  </CardTitle>
                  <CardDescription className="text-xs text-charcoal/70">
                    Geospatial visualization of projects across active biomes
                  </CardDescription>
                </div>
                <Link
                  to="/map"
                  className="text-xs font-semibold text-forest hover:underline flex items-center gap-1"
                >
                  Full Map <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            </CardHeader>
            <CardContent className="p-3 flex-1 flex flex-col justify-center">
              <LivingEarthMap
                projects={projects}
                height="300px"
              />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 5. Operational Alerts & Recent Activity Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-6">
          <AttentionProjectsList
            projects={overview?.attention_projects || []}
            className="h-full"
          />
        </div>
        <div className="lg:col-span-6">
          <RecentActivityFeed
            activities={recentActivity}
            className="h-full"
          />
        </div>
      </div>

      {/* 6. Portfolio Projects Progress Table */}
      <Card className="border-forest/15 shadow-sm">
        <CardHeader className="pb-3 border-b border-forest/10">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <CardTitle className="text-base font-manrope text-forest font-bold">
                Project Portfolio Impact & Target Progress
              </CardTitle>
              <CardDescription className="text-xs text-charcoal/70">
                Individual project balance sheets reconciling target commitments against official verified achievements
              </CardDescription>
            </div>

            <div className="flex items-center gap-2.5">
              <div className="relative w-48 sm:w-64">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-charcoal/40" />
                <Input
                  value={projectSearch}
                  onChange={(e) => setProjectSearch(e.target.value)}
                  placeholder="Search project name or code..."
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
        </CardHeader>

        <CardContent className="p-0">
          {isProjectsLoading ? (
            <div className="p-8 text-center text-xs text-charcoal/50">Loading projects...</div>
          ) : projects.length === 0 ? (
            <div className="py-12 text-center text-xs text-charcoal/50">
              No projects found matching current filters.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-forest/10 bg-forest/5 font-semibold text-charcoal/80">
                    <th className="py-3 px-4">Project</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-4">Target & Verified Progress</th>
                    <th className="py-3 px-3 text-right">Achievement</th>
                    <th className="py-3 px-3 text-right">Pending Net</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-forest/5">
                  {projects.map((p) => (
                    <tr key={p.id} className="hover:bg-forest/5 transition-colors">
                      <td className="py-3 px-4">
                        <Link
                          to={`/projects/${p.id}`}
                          className="font-bold text-forest hover:underline font-manrope text-sm block"
                        >
                          {p.name}
                        </Link>
                        <span className="font-mono text-[10px] text-charcoal/50">
                          {p.code}
                        </span>
                      </td>

                      <td className="py-3 px-3">
                        <Badge
                          variant="outline"
                          className="text-[10px] uppercase font-semibold h-4 px-1.5"
                        >
                          {p.status}
                        </Badge>
                      </td>

                      <td className="py-3 px-4">
                        {p.targets.length === 0 ? (
                          <span className="text-charcoal/50 italic text-[11px]">
                            No targets configured
                          </span>
                        ) : (
                          <div className="space-y-1.5 max-w-xs">
                            {p.targets.map((t) => (
                              <div key={t.target_id} className="space-y-0.5">
                                <div className="flex justify-between text-[11px]">
                                  <span className="text-charcoal/80 truncate">{t.metric_name}</span>
                                  <span className="font-medium text-forest">
                                    {Number(t.verified_quantity).toLocaleString()} / {Number(t.target_quantity).toLocaleString()} {t.target_unit}
                                  </span>
                                </div>
                                <div className="h-1.5 w-full bg-forest/10 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-forest rounded-full"
                                    style={{ width: `${Math.min(100, Math.max(0, t.achievement_percentage))}%` }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </td>

                      <td className="py-3 px-3 text-right font-medium">
                        {p.overall_achievement_percentage !== null ? (
                          <span
                            className={
                              p.overall_achievement_percentage >= 80
                                ? "text-emerald-700 font-bold"
                                : p.overall_achievement_percentage >= 40
                                ? "text-forest"
                                : "text-amber-700"
                            }
                          >
                            {p.overall_achievement_percentage}%
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>

                      <td className="py-3 px-3 text-right">
                        {p.targets.some((t) => Number(t.net_pending_adjustment) !== 0) ? (
                          <div className="space-y-0.5 text-[11px] font-medium text-amber-800">
                            {p.targets
                              .filter((t) => Number(t.net_pending_adjustment) !== 0)
                              .map((t) => (
                                <div key={t.target_id}>
                                  {Number(t.net_pending_adjustment) > 0 ? "+" : ""}
                                  {Number(t.net_pending_adjustment).toLocaleString()} {t.target_unit}
                                </div>
                              ))}
                          </div>
                        ) : (
                          <span className="text-charcoal/40 text-[11px]">0</span>
                        )}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <Link to={`/projects/${p.id}`}>
                          <Button variant="ghost" size="sm" className="h-7 text-xs text-forest hover:bg-forest/10 px-2.5">
                            Workspace <ExternalLink className="w-3 h-3 ml-1" />
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
