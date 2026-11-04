import React from "react";
import {
  Calendar,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ClipboardList,
  HeartPulse,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type {
  FieldInspection,
  MaintenanceTask,
  MonitoringAlertSummary,
  MonitoringDashboard,
} from "@/types/monitoring";

interface MonitoringDashboardTabProps {
  dashboard: MonitoringDashboard | undefined;
  alerts: MonitoringAlertSummary | undefined;
  inspections: FieldInspection[] | undefined;
  tasks: MaintenanceTask[] | undefined;
  isLoading: boolean;
  onNavigateTab: (tab: "inspections" | "maintenance" | "survival") => void;
  onSelectInspection?: (inspection: FieldInspection) => void;
  onSelectTask?: (task: MaintenanceTask) => void;
}

export const MonitoringDashboardTab: React.FC<MonitoringDashboardTabProps> = ({
  dashboard,
  alerts,
  inspections = [],
  tasks = [],
  isLoading,
  onNavigateTab,
  onSelectInspection,
}) => {
  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-28 bg-vana-forest/5 rounded-xl border border-vana-forest/10" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-72 bg-vana-forest/5 rounded-xl border border-vana-forest/10" />
          <div className="h-72 bg-vana-forest/5 rounded-xl border border-vana-forest/10" />
        </div>
      </div>
    );
  }

  const overdueInspectionsCount =
    alerts?.alerts.filter((a) => a.alert_type === "OVERDUE_INSPECTION").length ?? 0;
  const overdueTasksCount =
    dashboard?.overdue_tasks ??
    alerts?.alerts.filter((a) => a.alert_type === "OVERDUE_TASK").length ??
    0;

  // Upcoming inspections (SCHEDULED, sorted by date asc)
  const upcomingInspections = [...inspections]
    .filter((insp) => insp.status === "SCHEDULED")
    .sort((a, b) => a.scheduled_date.localeCompare(b.scheduled_date))
    .slice(0, 5);

  // Attention tasks (TODO or IN_PROGRESS, priority URGENT or HIGH, or overdue)
  const todayStr = new Date().toISOString().split("T")[0];
  const attentionTasks = [...tasks]
    .filter(
      (t) =>
        t.status !== "COMPLETED" &&
        t.status !== "CANCELLED" &&
        (t.priority === "URGENT" || t.priority === "HIGH" || t.due_date < todayStr)
    )
    .sort((a, b) => a.due_date.localeCompare(b.due_date))
    .slice(0, 5);

  // Latest observations from dashboard response
  const latestObs = dashboard?.latest_observations ?? [];

  return (
    <div className="space-y-6">
      {/* Dynamic Alerts Banner */}
      {alerts && alerts.total_alerts > 0 && (
        <Card className="border-vana-crimson/30 bg-vana-crimson/5 shadow-xs overflow-hidden">
          <CardHeader className="py-3 px-4 bg-vana-crimson/10 border-b border-vana-crimson/20 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-vana-crimson animate-pulse" />
              <CardTitle className="text-sm font-bold font-manrope text-vana-crimson">
                Active Operational Monitoring Alerts ({alerts.total_alerts})
              </CardTitle>
            </div>
            <div className="flex items-center gap-2 text-xs">
              {alerts.high_count > 0 && (
                <Badge variant="rejected" className="text-[10px] px-2 py-0.5">
                  {alerts.high_count} HIGH
                </Badge>
              )}
              {alerts.medium_count > 0 && (
                <Badge variant="pending" className="text-[10px] px-2 py-0.5">
                  {alerts.medium_count} MEDIUM
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-4 space-y-2.5">
            {alerts.alerts.slice(0, 4).map((alert, idx) => (
              <div
                key={idx}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2.5 bg-white/80 rounded-lg border border-vana-crimson/15 text-xs"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`font-semibold uppercase tracking-wider text-[10px] px-1.5 py-0.5 rounded ${
                        alert.severity === "HIGH"
                          ? "bg-vana-crimson/15 text-vana-crimson"
                          : "bg-vana-gold/20 text-[#8C6228]"
                      }`}
                    >
                      {alert.alert_type.replace(/_/g, " ")}
                    </span>
                    <span className="font-semibold text-vana-charcoal">{alert.title}</span>
                  </div>
                  {alert.details && (
                    <p className="text-vana-charcoal/70 text-[11px]">{alert.details}</p>
                  )}
                </div>
                <div className="flex items-center gap-3 text-vana-charcoal/60 shrink-0">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5 text-vana-crimson" />
                    Due {alert.due_date}
                  </span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* KPI Cards Row (6 metrics) */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* 1. Scheduled Inspections */}
        <Card className="border border-vana-forest/15 bg-white shadow-subtle hover:border-vana-forest/30 transition-colors">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-vana-forest">
              <span className="text-[11px] font-semibold text-vana-charcoal/60 uppercase tracking-wide">
                Scheduled
              </span>
              <Calendar className="h-4 w-4" />
            </div>
            <div className="text-2xl font-bold font-manrope text-vana-forest">
              {dashboard?.scheduled_inspections ?? 0}
            </div>
            <p className="text-[11px] text-vana-charcoal/60">Upcoming inspections</p>
          </CardContent>
        </Card>

        {/* 2. Overdue Inspections */}
        <Card className="border border-vana-crimson/20 bg-white shadow-subtle hover:border-vana-crimson/40 transition-colors">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-vana-crimson">
              <span className="text-[11px] font-semibold text-vana-crimson uppercase tracking-wide">
                Overdue Insp.
              </span>
              <AlertTriangle className="h-4 w-4" />
            </div>
            <div className="text-2xl font-bold font-manrope text-vana-crimson">
              {overdueInspectionsCount}
            </div>
            <p className="text-[11px] text-vana-charcoal/60">Past scheduled date</p>
          </CardContent>
        </Card>

        {/* 3. Completed Inspections */}
        <Card className="border border-vana-forest/15 bg-white shadow-subtle hover:border-vana-forest/30 transition-colors">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-vana-forest">
              <span className="text-[11px] font-semibold text-vana-charcoal/60 uppercase tracking-wide">
                Completed
              </span>
              <CheckCircle2 className="h-4 w-4 text-emerald-700" />
            </div>
            <div className="text-2xl font-bold font-manrope text-emerald-800">
              {dashboard?.completed_inspections ?? 0}
            </div>
            <p className="text-[11px] text-vana-charcoal/60">Total completed</p>
          </CardContent>
        </Card>

        {/* 4. Open Tasks */}
        <Card className="border border-vana-forest/15 bg-white shadow-subtle hover:border-vana-forest/30 transition-colors">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-vana-gold">
              <span className="text-[11px] font-semibold text-vana-charcoal/60 uppercase tracking-wide">
                Open Tasks
              </span>
              <ClipboardList className="h-4 w-4 text-vana-gold" />
            </div>
            <div className="text-2xl font-bold font-manrope text-vana-charcoal">
              {dashboard?.open_tasks ?? 0}
            </div>
            <p className="text-[11px] text-vana-charcoal/60">Active maintenance</p>
          </CardContent>
        </Card>

        {/* 5. Overdue Tasks */}
        <Card className="border border-vana-crimson/20 bg-white shadow-subtle hover:border-vana-crimson/40 transition-colors">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-vana-crimson">
              <span className="text-[11px] font-semibold text-vana-crimson uppercase tracking-wide">
                Overdue Tasks
              </span>
              <Clock className="h-4 w-4 text-vana-crimson" />
            </div>
            <div className="text-2xl font-bold font-manrope text-vana-crimson">
              {overdueTasksCount}
            </div>
            <p className="text-[11px] text-vana-charcoal/60">Require immediate action</p>
          </CardContent>
        </Card>

        {/* 6. Survival Observations */}
        <Card className="border border-vana-forest/15 bg-white shadow-subtle hover:border-vana-forest/30 transition-colors">
          <CardContent className="p-4 space-y-1">
            <div className="flex items-center justify-between text-vana-forest">
              <span className="text-[11px] font-semibold text-vana-charcoal/60 uppercase tracking-wide">
                Survival Records
              </span>
              <HeartPulse className="h-4 w-4 text-vana-sage" />
            </div>
            <div className="text-2xl font-bold font-manrope text-vana-forest">
              {latestObs.length}
            </div>
            <p className="text-[11px] text-vana-charcoal/60">Active sample cohorts</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Sections: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upcoming Inspections Section */}
        <Card className="border border-vana-forest/15 bg-white shadow-subtle">
          <CardHeader className="pb-3 border-b border-vana-forest/10 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base font-bold font-manrope text-vana-forest flex items-center gap-2">
                <Calendar className="h-4 w-4 text-vana-forest" /> Upcoming Inspections
              </CardTitle>
              <CardDescription className="text-xs text-vana-charcoal/60">
                Next scheduled field audits
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-vana-forest gap-1"
              onClick={() => onNavigateTab("inspections")}
            >
              View all <ArrowRight className="h-3 w-3" />
            </Button>
          </CardHeader>
          <CardContent className="p-4 space-y-2.5">
            {upcomingInspections.length === 0 ? (
              <div className="text-center py-8 text-vana-charcoal/60 text-xs">
                No scheduled inspections currently pending.
              </div>
            ) : (
              upcomingInspections.map((insp) => (
                <div
                  key={insp.id}
                  onClick={() => onSelectInspection?.(insp)}
                  className="flex items-center justify-between p-3 rounded-lg border border-vana-forest/10 bg-vana-forest/5 hover:bg-vana-forest/10 cursor-pointer transition-colors text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-vana-forest">
                        {insp.inspection_type.replace(/_/g, " ")}
                      </span>
                      <Badge variant="pending" className="text-[10px] px-2 py-0">
                        {insp.status}
                      </Badge>
                    </div>
                    <p className="text-vana-charcoal/70 text-[11px] flex items-center gap-2">
                      <span>Scheduled: {insp.scheduled_date}</span>
                      {insp.addenda?.length > 0 && (
                        <span>• {insp.addenda.length} addenda</span>
                      )}
                    </p>
                  </div>
                  <Button variant="outline" size="sm" className="h-7 text-xs">
                    Inspect
                  </Button>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Maintenance Tasks Requiring Attention */}
        <Card className="border border-vana-forest/15 bg-white shadow-subtle">
          <CardHeader className="pb-3 border-b border-vana-forest/10 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base font-bold font-manrope text-vana-forest flex items-center gap-2">
                <ClipboardList className="h-4 w-4 text-vana-gold" /> Maintenance Tasks Needing Action
              </CardTitle>
              <CardDescription className="text-xs text-vana-charcoal/60">
                High-priority and overdue field tasks
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-vana-forest gap-1"
              onClick={() => onNavigateTab("maintenance")}
            >
              View all <ArrowRight className="h-3 w-3" />
            </Button>
          </CardHeader>
          <CardContent className="p-4 space-y-2.5">
            {attentionTasks.length === 0 ? (
              <div className="text-center py-8 text-vana-charcoal/60 text-xs">
                All maintenance tasks are on schedule and healthy!
              </div>
            ) : (
              attentionTasks.map((task) => {
                const isOverdue = task.due_date < todayStr;
                return (
                  <div
                    key={task.id}
                    className={`flex items-center justify-between p-3 rounded-lg border text-xs transition-colors ${
                      isOverdue
                        ? "border-vana-crimson/25 bg-vana-crimson/5"
                        : "border-vana-forest/10 bg-white hover:bg-vana-forest/5"
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-vana-charcoal">{task.title}</span>
                        <Badge
                          variant={
                            task.priority === "URGENT" || isOverdue ? "rejected" : "pending"
                          }
                          className="text-[10px] px-1.5 py-0"
                        >
                          {task.priority}
                        </Badge>
                      </div>
                      <p className="text-vana-charcoal/60 text-[11px]">
                        Category: {task.category.replace(/_/g, " ")} • Due:{" "}
                        <span className={isOverdue ? "text-vana-crimson font-semibold" : ""}>
                          {task.due_date} {isOverdue ? "(OVERDUE)" : ""}
                        </span>
                      </p>
                    </div>
                    <Badge variant="outline" className="text-[10px]">
                      {task.status}
                    </Badge>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>

      {/* Latest Survival Observations Feed */}
      <Card className="border border-vana-forest/15 bg-white shadow-subtle">
        <CardHeader className="pb-3 border-b border-vana-forest/10 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base font-bold font-manrope text-vana-forest flex items-center gap-2">
              <HeartPulse className="h-4 w-4 text-emerald-700" /> Latest Survival Monitoring Observations
            </CardTitle>
            <CardDescription className="text-xs text-vana-charcoal/60">
              Active sample-based field assessments and derived survival rates
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="text-xs text-vana-forest gap-1"
            onClick={() => onNavigateTab("survival")}
          >
            Analytics &amp; History <ArrowRight className="h-3 w-3" />
          </Button>
        </CardHeader>
        <CardContent className="p-4">
          {latestObs.length === 0 ? (
            <div className="text-center py-8 text-vana-charcoal/60 text-xs">
              No survival observations recorded yet. Head to Survival Monitoring to submit a new sample observation.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-vana-forest/5 text-vana-charcoal/80 uppercase text-[10px] font-semibold border-b border-vana-forest/10">
                  <tr>
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Plot Identifier</th>
                    <th className="py-2.5 px-3">Cohort</th>
                    <th className="py-2.5 px-3">Methodology</th>
                    <th className="py-2.5 px-3 text-right">Sample Size</th>
                    <th className="py-2.5 px-3 text-right">Alive</th>
                    <th className="py-2.5 px-3 text-right">Dead</th>
                    <th className="py-2.5 px-3 text-right">Derived Survival</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-vana-forest/10">
                  {latestObs.slice(0, 5).map((obs) => (
                    <tr key={obs.id} className="hover:bg-vana-forest/5 transition-colors">
                      <td className="py-2.5 px-3 font-medium text-vana-charcoal">
                        {obs.observation_date}
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-vana-forest">
                        {obs.plot_identifier}
                      </td>
                      <td className="py-2.5 px-3 text-vana-charcoal/80">{obs.cohort_identifier}</td>
                      <td className="py-2.5 px-3">
                        <Badge variant="sage" className="text-[10px] px-1.5 py-0">
                          {obs.methodology}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono">{obs.sample_size}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-emerald-800 font-semibold">
                        {obs.alive_count}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-vana-crimson">
                        {obs.dead_count}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold">
                        {obs.survival_rate !== null ? (
                          <span
                            className={
                              obs.survival_rate >= 80
                                ? "text-emerald-800"
                                : obs.survival_rate >= 50
                                ? "text-[#8C6228]"
                                : "text-vana-crimson"
                            }
                          >
                            {obs.survival_rate.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-vana-charcoal/40 italic">N/A</span>
                        )}
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
