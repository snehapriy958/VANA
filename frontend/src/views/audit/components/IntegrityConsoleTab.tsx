import React, { useState } from "react";
import {
  ShieldCheck,
  ShieldQuestion,
  Play,
  RefreshCw,
  AlertTriangle,
  Info,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import type { AuditChainVerificationResponse, AuditVerifyChainRequest } from "@/types/audit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface IntegrityConsoleTabProps {
  report: AuditChainVerificationResponse | null;
  isVerifying: boolean;
  onRunVerification: (params?: AuditVerifyChainRequest) => void;
}

export const IntegrityConsoleTab: React.FC<IntegrityConsoleTabProps> = ({
  report,
  isVerifying,
  onRunVerification,
}) => {
  const [fromSeq, setFromSeq] = useState<string>("");
  const [toSeq, setToSeq] = useState<string>("");

  const handleRun = () => {
    const params: AuditVerifyChainRequest = {};
    if (fromSeq && !isNaN(parseInt(fromSeq, 10))) {
      params.from_sequence = parseInt(fromSeq, 10);
    }
    if (toSeq && !isNaN(parseInt(toSeq, 10))) {
      params.to_sequence = parseInt(toSeq, 10);
    }
    onRunVerification(params);
  };

  return (
    <div className="space-y-6">
      {/* Verification Execution Card */}
      <div className="bg-white p-6 rounded-xl border border-vana-charcoal/10 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-vana-forest flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-vana-forest" /> Cryptographic Chain Integrity Validator
            </h3>
            <p className="text-xs text-vana-charcoal/70 mt-1">
              Recomputes SHA-256 event digests across canonical JSON payloads and verifies sequential previous-hash linkage in PostgreSQL.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={handleRun}
              disabled={isVerifying}
              className="bg-vana-forest hover:bg-vana-forest/90 text-white text-xs font-semibold px-4 h-9"
            >
              <Play className={`w-3.5 h-3.5 mr-1.5 ${isVerifying ? "animate-spin" : ""}`} />
              {isVerifying ? "Verifying Ledger..." : "Run Integrity Verification"}
            </Button>
          </div>
        </div>

        {/* Optional Range Parameters */}
        <div className="pt-3 border-t border-vana-charcoal/10 flex flex-wrap items-center gap-4 text-xs text-vana-charcoal/70">
          <span className="font-semibold text-vana-forest">Sequence Scope (Optional):</span>
          <div className="flex items-center gap-2">
            <label className="text-vana-charcoal/60">From Sequence:</label>
            <Input
              type="number"
              placeholder="1 (Genesis)"
              value={fromSeq}
              onChange={(e) => setFromSeq(e.target.value)}
              className="w-28 text-xs h-8"
              min={1}
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-vana-charcoal/60">To Sequence:</label>
            <Input
              type="number"
              placeholder="Latest Head"
              value={toSeq}
              onChange={(e) => setToSeq(e.target.value)}
              className="w-28 text-xs h-8"
              min={1}
            />
          </div>
          <span className="text-[11px] text-vana-charcoal/50 italic">
            Leave blank to verify all records from Genesis to Chain Head.
          </span>
        </div>
      </div>

      {/* Result Status Display */}
      {isVerifying ? (
        <div className="bg-white p-12 rounded-xl border border-vana-charcoal/10 shadow-xs text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-vana-forest animate-spin mx-auto" />
          <h4 className="font-bold text-sm text-vana-forest">
            Computing SHA-256 Digests & Validating Hash Continuity...
          </h4>
          <p className="text-xs text-vana-charcoal/60 max-w-md mx-auto">
            Verifying zero sequence gaps, monotonic progression, payload-to-hash consistency, and singleton chain-head synchronization.
          </p>
        </div>
      ) : !report ? (
        <div className="bg-vana-ivory/30 p-8 rounded-xl border border-dashed border-vana-charcoal/20 text-center space-y-2">
          <ShieldQuestion className="w-10 h-10 text-vana-charcoal/30 mx-auto" />
          <h4 className="font-bold text-sm text-vana-charcoal/70">
            Ledger Status Not Yet Verified in Current Session
          </h4>
          <p className="text-xs text-vana-charcoal/50 max-w-md mx-auto">
            Click "Run Integrity Verification" above to trigger real-time mathematical validation against the database state.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Main Status Banner */}
          {report.is_valid && report.status === "VALID" ? (
            <div className="bg-emerald-50 border border-emerald-300 rounded-xl p-5 flex items-start gap-4">
              <CheckCircle2 className="w-7 h-7 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-bold text-emerald-900 text-sm">
                  Cryptographic Chain Integrity Verified — Zero Tampering Detected
                </h4>
                <p className="text-xs text-emerald-800 mt-1 leading-relaxed">
                  All {report.total_events_checked.toLocaleString()} audited events across sequence range{" "}
                  <span className="font-mono font-bold">#1..#{report.last_verified_sequence}</span> match their mathematical SHA-256 digests. Sequential continuity, state transitions, and previous-hash linkages are 100% intact.
                </p>
              </div>
            </div>
          ) : report.status === "EMPTY" ? (
            <div className="bg-amber-50 border border-amber-300 rounded-xl p-5 flex items-start gap-4">
              <Info className="w-7 h-7 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-bold text-amber-900 text-sm">Empty Ledger</h4>
                <p className="text-xs text-amber-800 mt-1">
                  The audit chain head is at sequence #0 with zero committed audit events.
                </p>
              </div>
            </div>
          ) : (
            <div className="bg-rose-50 border border-rose-300 rounded-xl p-5 flex items-start gap-4">
              <XCircle className="w-7 h-7 text-vana-crimson shrink-0 mt-0.5" />
              <div>
                <h4 className="font-bold text-rose-900 text-sm">
                  Cryptographic Verification Failed — Integrity Compromised!
                </h4>
                <p className="text-xs text-rose-800 mt-1 leading-relaxed">
                  Integrity violation detected! First failure occurred at sequence{" "}
                  <span className="font-mono font-bold">#{report.first_failure_sequence}</span> (Failure Category:{" "}
                  <span className="font-bold uppercase">{report.failure_category}</span>). Last validly verified sequence was{" "}
                  <span className="font-mono font-bold">
                    {report.last_verified_sequence ? `#${report.last_verified_sequence}` : "None"}
                  </span>.
                </p>
              </div>
            </div>
          )}

          {/* Report Metrics Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-vana-charcoal/10">
              <span className="text-xs text-vana-charcoal/60 block font-semibold uppercase">
                Events Checked
              </span>
              <span className="text-2xl font-bold font-serif text-vana-forest mt-1 block">
                {report.total_events_checked.toLocaleString()}
              </span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-vana-charcoal/10">
              <span className="text-xs text-vana-charcoal/60 block font-semibold uppercase">
                Last Verified Sequence
              </span>
              <span className="text-xl font-bold font-mono text-vana-charcoal mt-1 block">
                {report.last_verified_sequence ? `#${report.last_verified_sequence}` : "—"}
              </span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-vana-charcoal/10">
              <span className="text-xs text-vana-charcoal/60 block font-semibold uppercase">
                Chain Head Sequence
              </span>
              <span className="text-xl font-bold font-mono text-vana-forest mt-1 block">
                #{report.chain_head_sequence}
              </span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-vana-charcoal/10">
              <span className="text-xs text-vana-charcoal/60 block font-semibold uppercase">
                Verified At (UTC)
              </span>
              <span className="text-xs font-medium text-vana-charcoal mt-1 block">
                {new Date(report.verified_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
              </span>
            </div>
          </div>

          {/* Chain Head Checkpoint Hash */}
          <div className="bg-white p-4 rounded-xl border border-vana-charcoal/10 space-y-2">
            <span className="text-xs font-bold text-vana-forest uppercase tracking-wider block">
              Chain Head Checkpoint Hash
            </span>
            <div className="font-mono text-xs p-2.5 bg-vana-ivory/40 rounded border border-vana-charcoal/15 break-all select-all text-vana-charcoal">
              {report.chain_head_hash}
            </div>
          </div>

          {/* Errors Diagnostic Table (if any) */}
          {report.errors.length > 0 && (
            <div className="bg-white rounded-xl border border-rose-200 overflow-hidden shadow-xs">
              <div className="p-4 bg-rose-50 border-b border-rose-200 flex items-center gap-2 text-rose-900 font-bold text-sm">
                <AlertTriangle className="w-4 h-4 text-vana-crimson" />
                Detected Integrity Errors ({report.errors.length})
              </div>
              <div className="divide-y divide-rose-100">
                {report.errors.map((err, idx) => (
                  <div key={idx} className="p-4 text-xs space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-rose-900">
                        {err.sequence_number ? `Seq #${err.sequence_number}` : "Ledger Level"}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-200 text-rose-800">
                        {err.error_type}
                      </span>
                    </div>
                    <div className="text-vana-charcoal font-medium">{err.message}</div>
                    {(err.expected || err.actual) && (
                      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono mt-1 p-2 bg-rose-50/50 rounded">
                        <div>
                          <span className="text-vana-charcoal/60 block">Expected:</span>
                          <span className="text-emerald-700 break-all">{err.expected || "N/A"}</span>
                        </div>
                        <div>
                          <span className="text-vana-charcoal/60 block">Actual:</span>
                          <span className="text-rose-700 break-all">{err.actual || "N/A"}</span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Operational & Legal Disclaimer Box */}
          <div className="bg-vana-ivory/50 rounded-xl p-4 border border-vana-charcoal/15 space-y-2">
            <h5 className="text-xs font-bold uppercase tracking-wider text-vana-forest flex items-center gap-1.5">
              <Info className="w-4 h-4 text-vana-sage" /> Operational Limitations & Threat Boundary
            </h5>
            <p className="text-xs text-vana-charcoal/70 leading-relaxed">
              {report.disclaimer}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
