import React, { useState } from "react";
import {
  Layers,
  Search,
  ArrowRight,
  Clock,
  RefreshCw,
  AlertCircle,
  Eye,
} from "lucide-react";
import type { AuditEntityCategory, AuditLog, AuditLogListResponse } from "@/types/audit";
import type { Project } from "@/types/projects";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface EntityHistoryTabProps {
  data?: AuditLogListResponse;
  isLoading: boolean;
  projects: Project[];
  selectedType: AuditEntityCategory;
  selectedId: string;
  onSearch: (entityType: AuditEntityCategory, entityId: string) => void;
  onSelectEvent: (event: AuditLog) => void;
}

const ENTITY_CATEGORIES: Array<{ value: AuditEntityCategory; label: string }> = [
  { value: "project", label: "Project" },
  { value: "field_activity", label: "Field Activity" },
  { value: "activity_revision", label: "Activity Revision" },
  { value: "environmental_target", label: "Environmental Target" },
  { value: "field_inspection", label: "Field Inspection" },
  { value: "maintenance_task", label: "Maintenance Task" },
  { value: "survival_observation", label: "Survival Observation" },
  { value: "evidence_file", label: "Evidence File" },
  { value: "project_assignment", label: "Project Assignment" },
];

export const EntityHistoryTab: React.FC<EntityHistoryTabProps> = ({
  data,
  isLoading,
  projects,
  selectedType,
  selectedId,
  onSearch,
  onSelectEvent,
}) => {
  const [entityType, setEntityType] = useState<AuditEntityCategory>(selectedType);
  const [entityIdInput, setEntityIdInput] = useState<string>(selectedId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (entityIdInput.trim()) {
      onSearch(entityType, entityIdInput.trim());
    }
  };

  const renderStateDiff = (prev: Record<string, any> | null, curr: Record<string, any> | null) => {
    if (!prev && !curr) {
      return (
        <div className="text-xs text-vana-charcoal/50 italic p-2 bg-white rounded border border-vana-charcoal/10">
          No payload diff available.
        </div>
      );
    }

    if (!prev && curr) {
      return (
        <div className="space-y-1">
          <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-800">
            Initial Entity Creation (No Prior State)
          </div>
          <div className="p-2 bg-emerald-50/50 rounded border border-emerald-200 text-xs font-mono space-y-1">
            {Object.entries(curr).map(([k, v]) => (
              <div key={k} className="flex items-start gap-2">
                <span className="font-semibold text-emerald-900 shrink-0">{k}:</span>
                <span className="text-vana-charcoal break-all">{JSON.stringify(v)}</span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    // Compute key-by-key diff
    const allKeys = Array.from(new Set([...Object.keys(prev || {}), ...Object.keys(curr || {})]));
    const diffKeys = allKeys.filter((k) => JSON.stringify(prev?.[k]) !== JSON.stringify(curr?.[k]));

    if (diffKeys.length === 0) {
      return (
        <div className="text-xs text-vana-charcoal/50 italic p-2 bg-white rounded border border-vana-charcoal/10">
          State unchanged in this mutation.
        </div>
      );
    }

    return (
      <div className="space-y-1.5">
        <div className="text-[10px] font-bold uppercase tracking-wider text-vana-forest">
          Modified Attributes ({diffKeys.length})
        </div>
        <div className="divide-y divide-vana-charcoal/10 border border-vana-charcoal/15 rounded-lg bg-white overflow-hidden text-xs">
          {diffKeys.map((key) => {
            const oldVal = prev?.[key];
            const newVal = curr?.[key];
            return (
              <div key={key} className="p-2 flex flex-col md:flex-row md:items-center justify-between gap-2">
                <span className="font-mono font-semibold text-vana-forest shrink-0">
                  {key}
                </span>
                <div className="flex items-center gap-2 font-mono text-[11px] flex-1 justify-end overflow-hidden">
                  <span className="px-1.5 py-0.5 rounded bg-rose-50 text-rose-800 line-through truncate max-w-xs">
                    {oldVal !== undefined ? JSON.stringify(oldVal) : "undefined"}
                  </span>
                  <ArrowRight className="w-3.5 h-3.5 text-vana-sage shrink-0" />
                  <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 font-semibold truncate max-w-xs">
                    {newVal !== undefined ? JSON.stringify(newVal) : "undefined"}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Entity Selection Form */}
      <form onSubmit={handleSubmit} className="bg-white p-5 rounded-xl border border-vana-charcoal/10 shadow-xs space-y-4">
        <div className="flex items-center gap-2 text-vana-forest font-bold text-sm">
          <Layers className="w-4 h-4" />
          <span>Entity Lifecycle Query & State Diff Inspector</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Entity Type Dropdown */}
          <div>
            <label className="block text-xs font-semibold text-vana-charcoal/70 mb-1">
              Entity Category
            </label>
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value as AuditEntityCategory)}
              className="w-full text-xs h-9 rounded-md border border-vana-charcoal/20 px-3 bg-white text-vana-charcoal focus:outline-none focus:ring-1 focus:ring-vana-forest"
            >
              {ENTITY_CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label} ({cat.value})
                </option>
              ))}
            </select>
          </div>

          {/* Entity UUID Input */}
          <div>
            <label className="block text-xs font-semibold text-vana-charcoal/70 mb-1">
              Entity UUID
            </label>
            <Input
              type="text"
              placeholder="e.g. 1a2b3c4d-..."
              value={entityIdInput}
              onChange={(e) => setEntityIdInput(e.target.value)}
              className="text-xs h-9 font-mono"
              required
            />
          </div>

          {/* Action Button */}
          <div className="flex items-end">
            <Button
              type="submit"
              disabled={isLoading || !entityIdInput.trim()}
              className="w-full bg-vana-forest hover:bg-vana-forest/90 text-white text-xs h-9 font-semibold"
            >
              <Search className={`w-3.5 h-3.5 mr-1.5 ${isLoading ? "animate-spin" : ""}`} />
              {isLoading ? "Fetching Trail..." : "Inspect Entity Trail"}
            </Button>
          </div>
        </div>

        {/* Quick select from projects if entity type is project */}
        {entityType === "project" && projects.length > 0 && (
          <div className="pt-3 border-t border-vana-charcoal/10 flex items-center gap-2 overflow-x-auto text-xs">
            <span className="text-vana-charcoal/60 shrink-0 font-medium">Quick Select Project:</span>
            {projects.slice(0, 5).map((p) => (
              <button
                type="button"
                key={p.id}
                onClick={() => {
                  setEntityIdInput(p.id);
                  onSearch("project", p.id);
                }}
                className="px-2 py-1 bg-vana-ivory rounded border border-vana-charcoal/15 text-vana-forest hover:bg-vana-forest/10 hover:border-vana-forest/30 transition-colors shrink-0 font-mono text-[11px]"
              >
                {p.code}
              </button>
            ))}
          </div>
        )}
      </form>

      {/* Lifecycle Timeline */}
      {isLoading ? (
        <div className="bg-white p-12 rounded-xl border border-vana-charcoal/10 shadow-xs text-center space-y-2">
          <RefreshCw className="w-6 h-6 text-vana-forest animate-spin mx-auto" />
          <div className="text-xs text-vana-charcoal/60">
            Querying immutable ledger for {entityType} #{selectedId}...
          </div>
        </div>
      ) : !data ? (
        <div className="bg-vana-ivory/20 p-8 rounded-xl border border-dashed border-vana-charcoal/20 text-center text-xs text-vana-charcoal/60">
          Enter an Entity UUID above and click "Inspect Entity Trail" to review its chronological audit history.
        </div>
      ) : data.items.length === 0 ? (
        <div className="bg-white p-8 rounded-xl border border-vana-charcoal/10 text-center space-y-2">
          <AlertCircle className="w-8 h-8 text-vana-charcoal/30 mx-auto" />
          <div className="text-sm font-bold text-vana-forest">Zero Audit Records Found</div>
          <div className="text-xs text-vana-charcoal/60 max-w-md mx-auto">
            No audit events exist for entity {entityType} with ID {selectedId}. Records created prior to audit capture or in unassigned projects are unavailable.
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-vana-charcoal/70 px-1">
            <span>
              Found <span className="font-bold text-vana-forest">{data.total}</span> chronological event(s) for{" "}
              <span className="font-mono font-semibold">{entityType}</span>
            </span>
            <span className="font-mono text-[11px]">UUID: {selectedId}</span>
          </div>

          <div className="space-y-4">
            {data.items.map((event, idx) => (
              <div
                key={event.id}
                className="bg-white rounded-xl border border-vana-charcoal/10 shadow-xs overflow-hidden"
              >
                {/* Event Card Header */}
                <div className="p-4 bg-vana-ivory/30 border-b border-vana-charcoal/10 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 bg-vana-forest/10 text-vana-forest rounded border border-vana-forest/20">
                      Step {idx + 1} (Seq #{event.sequence_number})
                    </span>
                    <Badge variant="verified">{event.action_type}</Badge>
                    <span className="text-xs text-vana-charcoal/60 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-vana-sage" />
                      {new Date(event.created_at).toLocaleString()}
                    </span>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onSelectEvent(event)}
                    className="h-7 px-2 text-xs text-vana-forest hover:bg-vana-forest/10"
                  >
                    <Eye className="w-3.5 h-3.5 mr-1" /> Full Details
                  </Button>
                </div>

                {/* State Diff Content */}
                <div className="p-4 space-y-3">
                  {renderStateDiff(event.previous_state, event.new_state)}

                  {/* Cryptographic Link Preview */}
                  <div className="pt-2 border-t border-vana-charcoal/5 flex flex-wrap items-center justify-between text-[11px] font-mono text-vana-charcoal/60 gap-2">
                    <div>
                      <span>Previous: </span>
                      <span className="text-vana-charcoal/80">{event.previous_hash.slice(0, 16)}...</span>
                    </div>
                    <div>
                      <span>Digest: </span>
                      <span className="text-emerald-800 font-semibold">{event.current_hash.slice(0, 16)}...</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
