import React from "react";
import {
  FileCheck,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Archive,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Eye,
} from "lucide-react";
import type {
  AuditVerificationFilterParams,
  AuditVerificationHistoryResponse,
} from "@/types/audit";
import type { Project } from "@/types/projects";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface VerificationHistoryTabProps {
  data?: AuditVerificationHistoryResponse;
  isLoading: boolean;
  projects: Project[];
  filters: AuditVerificationFilterParams;
  onFilterChange: (filters: AuditVerificationFilterParams) => void;
  onInspectEventId: (eventId: string) => void;
  onRefresh: () => void;
}

export const VerificationHistoryTab: React.FC<VerificationHistoryTabProps> = ({
  data,
  isLoading,
  projects,
  filters,
  onFilterChange,
  onInspectEventId,
  onRefresh,
}) => {
  const getDecisionIcon = (action: string) => {
    switch (action) {
      case "ACTIVITY_VERIFIED":
        return <CheckCircle2 className="w-4 h-4 text-emerald-600" />;
      case "ACTIVITY_REJECTED":
        return <XCircle className="w-4 h-4 text-vana-crimson" />;
      case "ACTIVITY_AMENDED":
        return <AlertCircle className="w-4 h-4 text-[#8C6228]" />;
      case "ACTIVITY_ARCHIVED":
        return <Archive className="w-4 h-4 text-vana-charcoal/70" />;
      default:
        return <FileCheck className="w-4 h-4 text-vana-forest" />;
    }
  };

  const getDecisionBadge = (action: string) => {
    switch (action) {
      case "ACTIVITY_VERIFIED":
        return <Badge variant="verified">APPROVED / VERIFIED</Badge>;
      case "ACTIVITY_REJECTED":
        return <Badge variant="rejected">REJECTED</Badge>;
      case "ACTIVITY_AMENDED":
        return <Badge variant="pending">AMENDMENT SUBMITTED</Badge>;
      case "ACTIVITY_ARCHIVED":
        return <Badge variant="neutral">ARCHIVED</Badge>;
      default:
        return <Badge variant="sage">SUBMITTED</Badge>;
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-vana-charcoal/10 shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-1 min-w-[280px]">
          <select
            value={filters.project_id || "ALL"}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                project_id: e.target.value === "ALL" ? undefined : e.target.value,
                page: 1,
              })
            }
            className="text-xs h-9 rounded-md border border-vana-charcoal/20 px-3 bg-white text-vana-charcoal focus:outline-none focus:ring-1 focus:ring-vana-forest w-64"
          >
            <option value="ALL">All Projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code} — {p.name}
              </option>
            ))}
          </select>

          {filters.project_id && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onFilterChange({ ...filters, project_id: undefined, page: 1 })}
              className="text-xs text-vana-crimson hover:bg-vana-crimson/10"
            >
              Clear Project Filter
            </Button>
          )}
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          disabled={isLoading}
          className="text-xs border-vana-charcoal/20"
        >
          <RefreshCw className={`w-3.5 h-3.5 mr-1 ${isLoading ? "animate-spin" : ""}`} />
          Refresh Decisions
        </Button>
      </div>

      {/* Decisions Registry */}
      <div className="bg-white rounded-xl border border-vana-charcoal/10 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-vana-ivory/40 text-vana-forest border-b border-vana-charcoal/10 uppercase tracking-wider font-semibold">
              <tr>
                <th className="p-3 w-16">Seq #</th>
                <th className="p-3">Decision</th>
                <th className="p-3">Activity & Rev</th>
                <th className="p-3">Quantity</th>
                <th className="p-3">Reviewer / Verifier</th>
                <th className="p-3">Notes & Reason</th>
                <th className="p-3">Timestamp (UTC)</th>
                <th className="p-3 text-right">Audit Record</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-vana-charcoal/5">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-vana-charcoal/60">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-vana-forest" />
                    Loading immutable verification history...
                  </td>
                </tr>
              ) : !data || data.items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-vana-charcoal/60">
                    No verification lifecycle events found.
                  </td>
                </tr>
              ) : (
                data.items.map((item) => (
                  <tr key={item.event_id} className="hover:bg-vana-ivory/25 transition-colors">
                    <td className="p-3 font-mono font-bold text-vana-forest">
                      #{item.sequence_number}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-1.5">
                        {getDecisionIcon(item.action_type)}
                        {getDecisionBadge(item.action_type)}
                      </div>
                    </td>
                    <td className="p-3 font-mono text-vana-charcoal/80">
                      <div>
                        {item.activity_id ? `Act: ${item.activity_id.slice(0, 8)}...` : "—"}
                      </div>
                      {item.revision_number && (
                        <div className="text-[10px] text-vana-charcoal/50">
                          Revision #{item.revision_number}
                        </div>
                      )}
                    </td>
                    <td className="p-3 font-semibold text-vana-charcoal">
                      {item.verified_quantity !== null && item.verified_quantity !== undefined ? (
                        <span>{item.verified_quantity.toLocaleString()}</span>
                      ) : (
                        <span className="text-vana-charcoal/40 font-normal">—</span>
                      )}
                    </td>
                    <td className="p-3 font-mono text-vana-charcoal/70">
                      {item.verifier_id ? (
                        <span title={`Verifier: ${item.verifier_id}`}>
                          {item.verifier_id.slice(0, 8)}...
                        </span>
                      ) : item.actor_id ? (
                        <span title={`Actor: ${item.actor_id}`}>{item.actor_id.slice(0, 8)}...</span>
                      ) : (
                        "System"
                      )}
                    </td>
                    <td className="p-3 max-w-xs">
                      {item.rejection_reason_code && (
                        <div className="font-semibold text-[11px] text-vana-crimson mb-0.5">
                          Code: {item.rejection_reason_code}
                        </div>
                      )}
                      <div className="text-[11px] text-vana-charcoal/70 truncate">
                        {item.review_notes || "—"}
                      </div>
                    </td>
                    <td className="p-3 text-vana-charcoal/80 whitespace-nowrap">
                      {new Date(item.created_at).toLocaleString([], {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="p-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onInspectEventId(item.event_id)}
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
              <span className="font-bold">{data.total_pages}</span> ({data.total.toLocaleString()} verification records)
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
