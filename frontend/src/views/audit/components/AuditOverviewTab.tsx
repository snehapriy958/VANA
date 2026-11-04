import React from "react";
import {
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  History,
  FileCheck,
  ArrowRight,
  Hash,
  Database,
  ChevronRight,
} from "lucide-react";
import type { AuditChainVerificationResponse, AuditLog } from "@/types/audit";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface AuditOverviewTabProps {
  totalEvents: number;
  totalVerifications: number;
  recentEvents: AuditLog[];
  verificationReport: AuditChainVerificationResponse | null;
  onNavigateTab: (tab: "timeline" | "verification" | "integrity" | "entity") => void;
  onSelectEvent: (event: AuditLog) => void;
}

export const AuditOverviewTab: React.FC<AuditOverviewTabProps> = ({
  totalEvents,
  totalVerifications,
  recentEvents,
  verificationReport,
  onNavigateTab,
  onSelectEvent,
}) => {
  // Integrity Status Derivation (Zero Mock Data)
  const renderIntegrityBadge = () => {
    if (!verificationReport) {
      return (
        <div className="flex items-center gap-2 text-vana-charcoal/60">
          <ShieldQuestion className="w-5 h-5 text-vana-charcoal/40" />
          <div>
            <span className="font-semibold text-xs uppercase tracking-wide block text-vana-charcoal/70">
              Ledger State Unverified
            </span>
            <span className="text-[11px] text-vana-charcoal/50">
              Run verification in console
            </span>
          </div>
        </div>
      );
    }

    if (verificationReport.is_valid && verificationReport.status === "VALID") {
      return (
        <div className="flex items-center gap-2 text-emerald-800">
          <ShieldCheck className="w-5 h-5 text-emerald-600" />
          <div>
            <span className="font-semibold text-xs uppercase tracking-wide block text-emerald-800">
              Cryptographically Valid
            </span>
            <span className="text-[11px] text-emerald-700">
              {verificationReport.total_events_checked} events checked
            </span>
          </div>
        </div>
      );
    }

    return (
      <div className="flex items-center gap-2 text-vana-crimson">
        <ShieldAlert className="w-5 h-5 text-vana-crimson" />
        <div>
          <span className="font-semibold text-xs uppercase tracking-wide block text-vana-crimson">
            Integrity Alert / Broken Link
          </span>
          <span className="text-[11px] text-vana-crimson/80">
            {verificationReport.failure_category || "Discrepancy detected"}
          </span>
        </div>
      </div>
    );
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
    <div className="space-y-6">
      {/* Top Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Events */}
        <div className="bg-white p-5 rounded-xl border border-vana-charcoal/10 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-vana-charcoal/60 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-vana-forest">
                Total Audit Events
              </span>
              <Database className="w-4 h-4 text-vana-sage" />
            </div>
            <div className="text-3xl font-extrabold text-vana-forest font-serif">
              {totalEvents.toLocaleString()}
            </div>
          </div>
          <button
            onClick={() => onNavigateTab("timeline")}
            className="mt-3 pt-3 border-t border-vana-charcoal/5 flex items-center justify-between text-xs text-vana-forest font-medium hover:underline cursor-pointer"
          >
            <span>View full timeline</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Card 2: Verification Decisions */}
        <div className="bg-white p-5 rounded-xl border border-vana-charcoal/10 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-vana-charcoal/60 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-vana-forest">
                Verification Decisions
              </span>
              <FileCheck className="w-4 h-4 text-vana-sage" />
            </div>
            <div className="text-3xl font-extrabold text-vana-forest font-serif">
              {totalVerifications.toLocaleString()}
            </div>
          </div>
          <button
            onClick={() => onNavigateTab("verification")}
            className="mt-3 pt-3 border-t border-vana-charcoal/5 flex items-center justify-between text-xs text-vana-forest font-medium hover:underline cursor-pointer"
          >
            <span>Inspect decisions</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Card 3: Ledger Integrity Status */}
        <div className="bg-white p-5 rounded-xl border border-vana-charcoal/10 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-vana-charcoal/60 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-vana-forest">
                Integrity Status
              </span>
              <ShieldCheck className="w-4 h-4 text-vana-sage" />
            </div>
            <div className="mt-1">{renderIntegrityBadge()}</div>
          </div>
          <button
            onClick={() => onNavigateTab("integrity")}
            className="mt-3 pt-3 border-t border-vana-charcoal/5 flex items-center justify-between text-xs text-vana-forest font-medium hover:underline cursor-pointer"
          >
            <span>Open integrity console</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Card 4: Last Verified Sequence */}
        <div className="bg-white p-5 rounded-xl border border-vana-charcoal/10 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-vana-charcoal/60 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-vana-forest">
                Last Verified Sequence
              </span>
              <Hash className="w-4 h-4 text-vana-sage" />
            </div>
            <div className="text-2xl font-bold font-mono text-vana-charcoal">
              {verificationReport?.last_verified_sequence
                ? `#${verificationReport.last_verified_sequence}`
                : verificationReport?.status === "EMPTY"
                ? "#0 (Empty)"
                : "Not Run"}
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-vana-charcoal/5 text-[11px] text-vana-charcoal/50">
            {verificationReport?.verified_at
              ? `Checked at ${new Date(verificationReport.verified_at).toLocaleTimeString()}`
              : "Awaiting execution"}
          </div>
        </div>
      </div>

      {/* Quick Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <button
          onClick={() => onNavigateTab("timeline")}
          className="p-4 bg-vana-ivory/40 rounded-xl border border-vana-charcoal/10 hover:border-vana-forest/40 hover:bg-vana-ivory/70 transition-all text-left flex items-start justify-between cursor-pointer group"
        >
          <div>
            <h4 className="font-semibold text-sm text-vana-forest group-hover:text-emerald-900">
              Audit Timeline
            </h4>
            <p className="text-xs text-vana-charcoal/70 mt-1">
              Chronological log with multi-criteria filters and search.
            </p>
          </div>
          <ArrowRight className="w-4 h-4 text-vana-sage group-hover:text-vana-forest group-hover:translate-x-0.5 transition-all mt-1" />
        </button>

        <button
          onClick={() => onNavigateTab("verification")}
          className="p-4 bg-vana-ivory/40 rounded-xl border border-vana-charcoal/10 hover:border-vana-forest/40 hover:bg-vana-ivory/70 transition-all text-left flex items-start justify-between cursor-pointer group"
        >
          <div>
            <h4 className="font-semibold text-sm text-vana-forest group-hover:text-emerald-900">
              Verification History
            </h4>
            <p className="text-xs text-vana-charcoal/70 mt-1">
              Immutable approvals, rejections, and amendment logs.
            </p>
          </div>
          <ArrowRight className="w-4 h-4 text-vana-sage group-hover:text-vana-forest group-hover:translate-x-0.5 transition-all mt-1" />
        </button>

        <button
          onClick={() => onNavigateTab("integrity")}
          className="p-4 bg-vana-ivory/40 rounded-xl border border-vana-charcoal/10 hover:border-vana-forest/40 hover:bg-vana-ivory/70 transition-all text-left flex items-start justify-between cursor-pointer group"
        >
          <div>
            <h4 className="font-semibold text-sm text-vana-forest group-hover:text-emerald-900">
              Integrity Console
            </h4>
            <p className="text-xs text-vana-charcoal/70 mt-1">
              Real-time SHA-256 chain recomputation and proof validator.
            </p>
          </div>
          <ArrowRight className="w-4 h-4 text-vana-sage group-hover:text-vana-forest group-hover:translate-x-0.5 transition-all mt-1" />
        </button>

        <button
          onClick={() => onNavigateTab("entity")}
          className="p-4 bg-vana-ivory/40 rounded-xl border border-vana-charcoal/10 hover:border-vana-forest/40 hover:bg-vana-ivory/70 transition-all text-left flex items-start justify-between cursor-pointer group"
        >
          <div>
            <h4 className="font-semibold text-sm text-vana-forest group-hover:text-emerald-900">
              Entity History
            </h4>
            <p className="text-xs text-vana-charcoal/70 mt-1">
              Before-and-after lifecycle diffs for projects & activities.
            </p>
          </div>
          <ArrowRight className="w-4 h-4 text-vana-sage group-hover:text-vana-forest group-hover:translate-x-0.5 transition-all mt-1" />
        </button>
      </div>

      {/* Recent Audit Activity Stream */}
      <div className="bg-white rounded-xl border border-vana-charcoal/10 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-vana-charcoal/10 bg-vana-ivory/20 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-vana-forest" />
            <h3 className="font-bold text-sm text-vana-forest">
              Recent Audit Activity Stream
            </h3>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onNavigateTab("timeline")}
            className="text-xs border-vana-charcoal/20"
          >
            View All Events
          </Button>
        </div>

        <div className="divide-y divide-vana-charcoal/5">
          {recentEvents.length === 0 ? (
            <div className="p-8 text-center text-xs text-vana-charcoal/60">
              No audit events recorded yet.
            </div>
          ) : (
            recentEvents.map((event) => (
              <div
                key={event.id}
                onClick={() => onSelectEvent(event)}
                className="p-4 hover:bg-vana-ivory/30 transition-colors cursor-pointer flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs font-bold px-2 py-0.5 bg-vana-forest/10 text-vana-forest rounded border border-vana-forest/20 shrink-0">
                    #{event.sequence_number}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge variant={getActionBadgeVariant(event.action_type)}>
                        {event.action_type}
                      </Badge>
                      <span className="text-xs text-vana-charcoal/60">
                        {event.entity_type}
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-vana-charcoal/50 mt-1 truncate max-w-md">
                      Digest: {event.current_hash.slice(0, 24)}...
                    </div>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <div className="text-xs text-vana-charcoal font-medium">
                    {new Date(event.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                  <div className="text-[11px] text-vana-charcoal/50">
                    {new Date(event.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
