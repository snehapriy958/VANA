import React, { useState } from "react";
import {
  X,
  Copy,
  Check,
  ShieldCheck,
  Clock,
  User as UserIcon,
  FolderKanban,
  FileCode,
  ArrowRight,
  Database,
} from "lucide-react";
import type { AuditLog } from "@/types/audit";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface EventDetailDrawerProps {
  event: AuditLog | null;
  onClose: () => void;
}

export const EventDetailDrawer: React.FC<EventDetailDrawerProps> = ({ event, onClose }) => {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  if (!event) return null;

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
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
    <div className="fixed inset-0 z-50 flex justify-end bg-vana-charcoal/40 backdrop-blur-xs transition-opacity animate-in fade-in duration-200">
      <div
        className="fixed inset-0"
        onClick={onClose}
        aria-label="Close modal backdrop"
      />
      <div className="relative w-full max-w-2xl bg-white h-full shadow-2xl flex flex-col z-10 border-l border-vana-charcoal/15 animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="p-5 border-b border-vana-charcoal/10 flex items-center justify-between bg-vana-ivory/40">
          <div className="flex items-center gap-3">
            <span className="font-mono text-sm font-bold px-2.5 py-1 bg-vana-forest/10 text-vana-forest rounded border border-vana-forest/20">
              #{event.sequence_number}
            </span>
            <Badge variant={getActionBadgeVariant(event.action_type)}>
              {event.action_type}
            </Badge>
            {event.is_backfilled && (
              <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 bg-amber-100 text-amber-800 rounded border border-amber-300">
                Backfilled
              </span>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0 rounded-full hover:bg-vana-charcoal/10 text-vana-charcoal"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Drawer Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Metadata Grid */}
          <div className="bg-vana-ivory/30 rounded-xl p-4 border border-vana-charcoal/10 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-vana-forest flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5" /> Event Metadata
            </h4>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-vana-charcoal/60 block">Event UUID</span>
                <span className="font-mono text-vana-charcoal font-medium break-all flex items-center gap-1">
                  {event.id}
                  <button
                    onClick={() => copyToClipboard(event.id, "id")}
                    className="text-vana-charcoal/40 hover:text-vana-forest cursor-pointer"
                    title="Copy Event ID"
                  >
                    {copiedKey === "id" ? (
                      <Check className="w-3 h-3 text-emerald-600" />
                    ) : (
                      <Copy className="w-3 h-3" />
                    )}
                  </button>
                </span>
              </div>
              <div>
                <span className="text-vana-charcoal/60 block">Timestamp (UTC)</span>
                <span className="text-vana-charcoal font-medium flex items-center gap-1">
                  <Clock className="w-3 h-3 text-vana-sage" />
                  {new Date(event.created_at).toISOString()}
                </span>
              </div>
              <div>
                <span className="text-vana-charcoal/60 block">Entity Reference</span>
                <span className="font-mono text-vana-charcoal font-medium">
                  {event.entity_type} / {event.entity_id.slice(0, 8)}...
                </span>
              </div>
              <div>
                <span className="text-vana-charcoal/60 block">Actor</span>
                <span className="font-mono text-vana-charcoal font-medium flex items-center gap-1">
                  <UserIcon className="w-3 h-3 text-vana-sage" />
                  {event.actor_id ? `${event.actor_id.slice(0, 8)}...` : "System / Automated"}
                </span>
              </div>
              <div>
                <span className="text-vana-charcoal/60 block">Project ID</span>
                <span className="font-mono text-vana-charcoal font-medium flex items-center gap-1">
                  <FolderKanban className="w-3 h-3 text-vana-sage" />
                  {event.project_id ? `${event.project_id.slice(0, 8)}...` : "None (Global)"}
                </span>
              </div>
              <div>
                <span className="text-vana-charcoal/60 block">IP Address</span>
                <span className="font-mono text-vana-charcoal font-medium">
                  {event.ip_address || "Internal / Local"}
                </span>
              </div>
            </div>
          </div>

          {/* Cryptographic Linkage Block */}
          <div className="bg-vana-forest/5 rounded-xl p-4 border border-vana-forest/20 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-vana-forest flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-vana-forest" /> Cryptographic SHA-256 Linkage
            </h4>
            <div className="space-y-2 text-xs">
              <div>
                <div className="flex items-center justify-between text-vana-charcoal/60 mb-1">
                  <span>Previous Event Hash (Link)</span>
                  <button
                    onClick={() => copyToClipboard(event.previous_hash, "prev_hash")}
                    className="flex items-center gap-1 text-[11px] text-vana-forest hover:underline cursor-pointer"
                  >
                    {copiedKey === "prev_hash" ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-600" /> Copied
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" /> Copy
                      </>
                    )}
                  </button>
                </div>
                <div className="font-mono p-2 bg-white rounded border border-vana-charcoal/15 text-[11px] break-all select-all text-vana-charcoal/80">
                  {event.previous_hash}
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between text-vana-charcoal/60 mb-1">
                  <span>Current Event Digest (SHA-256 v{event.hash_version})</span>
                  <button
                    onClick={() => copyToClipboard(event.current_hash, "curr_hash")}
                    className="flex items-center gap-1 text-[11px] text-vana-forest hover:underline cursor-pointer"
                  >
                    {copiedKey === "curr_hash" ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-600" /> Copied
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" /> Copy
                      </>
                    )}
                  </button>
                </div>
                <div className="font-mono p-2 bg-emerald-50 rounded border border-emerald-300 text-[11px] break-all select-all text-emerald-900 font-semibold">
                  {event.current_hash}
                </div>
              </div>
            </div>
          </div>

          {/* State Transition (Previous vs New) */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-vana-charcoal/70 flex items-center gap-1.5">
              <ArrowRight className="w-3.5 h-3.5 text-vana-forest" /> State Transition Delta
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* Previous State */}
              <div className="border border-vana-charcoal/15 rounded-lg p-3 bg-vana-ivory/20">
                <div className="text-xs font-semibold text-vana-charcoal/60 mb-1.5 flex items-center justify-between">
                  <span>Previous State</span>
                  {!event.previous_state && (
                    <span className="text-[10px] italic text-vana-charcoal/50">Initial Creation</span>
                  )}
                </div>
                <pre className="text-[11px] font-mono overflow-x-auto p-2 bg-white rounded border border-vana-charcoal/10 max-h-48 text-vana-charcoal/80">
                  {event.previous_state
                    ? JSON.stringify(event.previous_state, null, 2)
                    : "// No prior state (initial entity creation)"}
                </pre>
              </div>

              {/* New State */}
              <div className="border border-vana-charcoal/15 rounded-lg p-3 bg-vana-ivory/20">
                <div className="text-xs font-semibold text-vana-forest mb-1.5 flex items-center justify-between">
                  <span>New State</span>
                  <span className="text-[10px] font-medium text-emerald-700">Committed</span>
                </div>
                <pre className="text-[11px] font-mono overflow-x-auto p-2 bg-white rounded border border-emerald-200 max-h-48 text-vana-charcoal">
                  {event.new_state
                    ? JSON.stringify(event.new_state, null, 2)
                    : "// No state mutation payload recorded"}
                </pre>
              </div>
            </div>
          </div>

          {/* Full Canonical Payload */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-vana-charcoal/70 flex items-center gap-1.5">
                <FileCode className="w-3.5 h-3.5 text-vana-forest" /> Deterministic Canonical Payload
              </h4>
              <button
                onClick={() =>
                  copyToClipboard(JSON.stringify(event.canonical_payload, null, 2), "payload")
                }
                className="flex items-center gap-1 text-[11px] text-vana-forest hover:underline cursor-pointer"
              >
                {copiedKey === "payload" ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-600" /> Copied Payload
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" /> Copy JSON
                  </>
                )}
              </button>
            </div>
            <pre className="text-[11px] font-mono overflow-x-auto p-3 bg-vana-charcoal text-vana-ivory rounded-lg max-h-60">
              {JSON.stringify(event.canonical_payload, null, 2)}
            </pre>
          </div>
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-vana-charcoal/10 bg-vana-ivory/30 flex justify-end">
          <Button variant="outline" size="sm" onClick={onClose} className="border-vana-charcoal/20">
            Close Inspector
          </Button>
        </div>
      </div>
    </div>
  );
};
