import React, { useState } from "react";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Eye,
  RefreshCw,
} from "lucide-react";
import type { AuditEventFilterParams, AuditLog, AuditLogListResponse } from "@/types/audit";
import type { Project } from "@/types/projects";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface AuditTimelineTabProps {
  data?: AuditLogListResponse;
  isLoading: boolean;
  projects: Project[];
  filters: AuditEventFilterParams;
  onFilterChange: (filters: AuditEventFilterParams) => void;
  onSelectEvent: (event: AuditLog) => void;
  onRefresh: () => void;
}

const COMMON_ACTIONS = [
  "ALL",
  "ACTIVITY_CREATED",
  "ACTIVITY_VERIFIED",
  "ACTIVITY_REJECTED",
  "ACTIVITY_AMENDED",
  "ACTIVITY_ARCHIVED",
  "EVIDENCE_UPLOADED",
  "PROJECT_CREATED",
  "PROJECT_UPDATED",
  "TARGET_CREATED",
  "USER_LOGIN_SUCCESS",
  "USER_ROLE_CHANGED",
  "INSPECTION_SCHEDULED",
  "INSPECTION_COMPLETED",
  "TASK_CREATED",
  "TASK_COMPLETED",
  "SURVIVAL_OBSERVATION_CREATED",
  "SURVIVAL_OBSERVATION_SUPERSEDED",
];

export const AuditTimelineTab: React.FC<AuditTimelineTabProps> = ({
  data,
  isLoading,
  projects,
  filters,
  onFilterChange,
  onSelectEvent,
  onRefresh,
}) => {
  const [searchTerm, setSearchTerm] = useState<string>(filters.search || "");

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onFilterChange({ ...filters, search: searchTerm || undefined, page: 1 });
  };

  const getActionBadgeVariant = (action: string) => {
    if (action.includes("VERIFIED") || action.includes("SUCCESS")) return "verified";
    if (action.includes("REJECTED") || action.includes("FAILED") || action.includes("CANCEL"))
      return "rejected";
    if (action.includes("AMENDED") || action.includes("PENDING")) return "pending";
    if (action.includes("CREATED") || action.includes("SCHEDULED")) return "sage";
    return "neutral";
  };

  return (
    <div className="space-y-4">
      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-vana-charcoal/10 shadow-xs space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {/* Search box */}
          <form onSubmit={handleSearchSubmit} className="relative">
            <Search className="w-4 h-4 text-vana-charcoal/40 absolute left-3 top-2.5" />
            <Input
              type="text"
              placeholder="Search ID, action, or actor..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 text-xs"
            />
          </form>

          {/* Action Type Filter */}
          <div>
            <select
              value={filters.action_type || "ALL"}
              onChange={(e) =>
                onFilterChange({
                  ...filters,
                  action_type: e.target.value === "ALL" ? undefined : e.target.value,
                  page: 1,
                })
              }
              className="w-full text-xs h-9 rounded-md border border-vana-charcoal/20 px-3 bg-white text-vana-charcoal focus:outline-none focus:ring-1 focus:ring-vana-forest"
            >
              {COMMON_ACTIONS.map((act) => (
                <option key={act} value={act}>
                  {act === "ALL" ? "All Action Types" : act}
                </option>
              ))}
            </select>
          </div>

          {/* Project Filter */}
          <div>
            <select
              value={filters.project_id || "ALL"}
              onChange={(e) =>
                onFilterChange({
                  ...filters,
                  project_id: e.target.value === "ALL" ? undefined : e.target.value,
                  page: 1,
                })
              }
              className="w-full text-xs h-9 rounded-md border border-vana-charcoal/20 px-3 bg-white text-vana-charcoal focus:outline-none focus:ring-1 focus:ring-vana-forest"
            >
              <option value="ALL">All Projects</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} — {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Refresh / Reset */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={isLoading}
              className="text-xs flex-1 border-vana-charcoal/20"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            {(filters.action_type || filters.project_id || filters.search) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSearchTerm("");
                  onFilterChange({ page: 1, page_size: filters.page_size || 20 });
                }}
                className="text-xs text-vana-crimson hover:bg-vana-crimson/10"
              >
                Clear
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Events Table */}
      <div className="bg-white rounded-xl border border-vana-charcoal/10 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-vana-ivory/40 text-vana-forest border-b border-vana-charcoal/10 uppercase tracking-wider font-semibold">
              <tr>
                <th className="p-3 w-16">Seq #</th>
                <th className="p-3">Action Type</th>
                <th className="p-3">Entity</th>
                <th className="p-3">Project</th>
                <th className="p-3">Actor</th>
                <th className="p-3">Timestamp (UTC)</th>
                <th className="p-3">SHA-256 Digest</th>
                <th className="p-3 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-vana-charcoal/5">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-vana-charcoal/60">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-vana-forest" />
                    Loading cryptographic audit events...
                  </td>
                </tr>
              ) : !data || data.items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-vana-charcoal/60">
                    No audit records match the applied criteria.
                  </td>
                </tr>
              ) : (
                data.items.map((event) => (
                  <tr
                    key={event.id}
                    className="hover:bg-vana-ivory/25 transition-colors cursor-pointer"
                    onClick={() => onSelectEvent(event)}
                  >
                    <td className="p-3 font-mono font-bold text-vana-forest">
                      #{event.sequence_number}
                    </td>
                    <td className="p-3">
                      <Badge variant={getActionBadgeVariant(event.action_type)}>
                        {event.action_type}
                      </Badge>
                      {event.is_backfilled && (
                        <span className="ml-1 text-[9px] px-1 py-0.2 bg-amber-100 text-amber-800 rounded font-semibold">
                          BF
                        </span>
                      )}
                    </td>
                    <td className="p-3 font-mono text-vana-charcoal/80">
                      <div>{event.entity_type}</div>
                      <div className="text-[10px] text-vana-charcoal/50">
                        {event.entity_id.slice(0, 8)}...
                      </div>
                    </td>
                    <td className="p-3 font-mono text-vana-charcoal/70">
                      {event.project_id ? `${event.project_id.slice(0, 8)}...` : "—"}
                    </td>
                    <td className="p-3 font-mono text-vana-charcoal/70">
                      {event.actor_id ? `${event.actor_id.slice(0, 8)}...` : "System"}
                    </td>
                    <td className="p-3 text-vana-charcoal/80 whitespace-nowrap">
                      {new Date(event.created_at).toLocaleString([], {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </td>
                    <td className="p-3 font-mono text-[11px] text-emerald-800 truncate max-w-xs">
                      {event.current_hash.slice(0, 16)}...
                    </td>
                    <td className="p-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectEvent(event);
                        }}
                        className="h-7 px-2 text-xs text-vana-forest hover:bg-vana-forest/10"
                      >
                        <Eye className="w-3.5 h-3.5 mr-1" /> Inspect
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {data && data.total_pages > 1 && (
          <div className="p-3 border-t border-vana-charcoal/10 bg-vana-ivory/20 flex items-center justify-between text-xs text-vana-charcoal/70">
            <div>
              Showing page <span className="font-bold">{data.page}</span> of{" "}
              <span className="font-bold">{data.total_pages}</span> ({data.total.toLocaleString()} total events)
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={data.page <= 1 || isLoading}
                onClick={() => onFilterChange({ ...filters, page: data.page - 1 })}
                className="h-7 px-2 text-xs border-vana-charcoal/20"
              >
                <ChevronLeft className="w-3.5 h-3.5 mr-1" /> Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={data.page >= data.total_pages || isLoading}
                onClick={() => onFilterChange({ ...filters, page: data.page + 1 })}
                className="h-7 px-2 text-xs border-vana-charcoal/20"
              >
                Next <ChevronRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
