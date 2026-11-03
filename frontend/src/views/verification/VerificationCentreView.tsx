import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  MapPin,
  Camera,
  Eye,
  Search,
  ChevronRight,
  RefreshCw,
  X,
  Lock,
} from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { operationsService } from "@/services/operations";
import { listProjects } from "@/services/projects";
import {
  RejectionReasonCode,
  VerificationDecisionPayload,
} from "@/types/operations";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

const REJECTION_REASONS: { code: RejectionReasonCode; label: string; description: string }[] = [
  {
    code: "INSUFFICIENT_EVIDENCE",
    label: "Insufficient Evidence",
    description: "Photos are blurry, out of focus, or lack verifiable measurement tags.",
  },
  {
    code: "COORDINATES_MISMATCH",
    label: "Coordinates Mismatch",
    description: "Reported GPS location falls outside project boundaries or in an invalid zone.",
  },
  {
    code: "INCORRECT_UNIT_OR_QUANTITY",
    label: "Incorrect Unit or Quantity",
    description: "Claimed numbers or measurement units conflict with field methodology rules.",
  },
  {
    code: "DUPLICATE_SUBMISSION",
    label: "Duplicate Submission",
    description: "This plot or planting activity has already been reported and verified.",
  },
  {
    code: "DATA_ENTRY_ERROR",
    label: "Data Entry Error",
    description: "Typographical mistake, inverted coordinates, or incorrect date entry.",
  },
];

export const VerificationCentreView: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<string>("ALL");

  // Selected Queue Item for Deep Inspection
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);

  // Modals & Lightbox
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [isApproveModalOpen, setIsApproveModalOpen] = useState(false);
  const [approveNotes, setApproveNotes] = useState("");
  const [rejectionReasonCode, setRejectionReasonCode] = useState<RejectionReasonCode>(
    "INSUFFICIENT_EVIDENCE"
  );
  const [rejectionNotes, setRejectionNotes] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [lightboxImageUrl, setLightboxImageUrl] = useState<string | null>(null);

  // Queries
  const {
    data: queueItems = [],
    isLoading: isQueueLoading,
    refetch: refetchQueue,
  } = useQuery({
    queryKey: ["verification-queue"],
    queryFn: () => operationsService.getVerificationQueue(),
  });

  const { data: projects = [] } = useQuery({
    queryKey: ["projects-dropdown"],
    queryFn: () => listProjects(),
  });

  // Automatically select first item if none selected
  const filteredQueue = queueItems.filter((item) => {
    if (selectedProjectId !== "ALL" && item.project_id !== selectedProjectId) return false;
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.metric_code.toLowerCase().includes(q) ||
      item.project_name.toLowerCase().includes(q) ||
      item.project_code.toLowerCase().includes(q) ||
      item.creator_name.toLowerCase().includes(q)
    );
  });

  const activeItem =
    filteredQueue.find((i) => i.revision_id === selectedItemId) ||
    filteredQueue[0] ||
    null;

  // Verification Decision Mutation
  const decisionMutation = useMutation({
    mutationFn: ({
      revisionId,
      payload,
    }: {
      revisionId: string;
      payload: VerificationDecisionPayload;
    }) => operationsService.submitVerificationDecision(revisionId, payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["verification-queue"] });
      queryClient.invalidateQueries({ queryKey: ["field-activities"] });

      if (data.status === "VERIFIED") {
        setActionSuccess("Activity verified; project ledger recalculated successfully.");
      } else {
        setActionSuccess("Activity rejected; previous verified revision preserved in ledger.");
      }

      setIsApproveModalOpen(false);
      setIsRejectModalOpen(false);
      setApproveNotes("");
      setRejectionNotes("");
      setActionError(null);

      // Auto dismiss success toast after 4s
      setTimeout(() => setActionSuccess(null), 4000);
    },
    onError: (err: any) => {
      const msg =
        err.response?.data?.detail?.message || err.message || "Failed to process decision";
      setActionError(msg);
    },
  });

  const handleApprove = () => {
    if (!activeItem) return;
    decisionMutation.mutate({
      revisionId: activeItem.revision_id,
      payload: {
        decision: "VERIFIED",
        review_notes: approveNotes.trim() || undefined,
      },
    });
  };

  const handleReject = () => {
    if (!activeItem) return;
    if (!rejectionNotes.trim()) {
      setActionError("Review notes explaining the rejection are mandatory.");
      return;
    }

    decisionMutation.mutate({
      revisionId: activeItem.revision_id,
      payload: {
        decision: "REJECTED",
        rejection_reason_code: rejectionReasonCode,
        review_notes: rejectionNotes.trim(),
      },
    });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-vana-charcoal/10">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-heading font-extrabold text-vana-forest tracking-tight">
              Activity Verification Centre
            </h1>
            <Badge className="bg-amber-100 text-amber-900 border-amber-300 font-semibold gap-1">
              <Clock className="w-3.5 h-3.5 text-amber-700" />
              {queueItems.length} Pending Review
            </Badge>
          </div>
          <p className="text-sm text-vana-charcoal/70 mt-1">
            Operational triage queue for digital sign-off, photo scrutiny, and anti-self-verification audit.
            {user?.full_name && (
              <span className="ml-2 font-medium text-vana-forest">
                (Reviewer: {user.full_name})
              </span>
            )}
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => refetchQueue()}
          className="text-xs gap-1.5 border-vana-forest/20 text-vana-forest hover:bg-vana-sage/15"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Queue
        </Button>
      </div>

      {/* Success / Error Notification Banners */}
      {actionSuccess && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-900 flex items-center justify-between shadow-subtle">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-semibold">{actionSuccess}</span>
          </div>
          <button
            onClick={() => setActionSuccess(null)}
            className="text-emerald-700 hover:text-emerald-900"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {actionError && (
        <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl text-xs text-red-900 flex items-center justify-between shadow-subtle">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
            <span className="font-semibold">{actionError}</span>
          </div>
          <button
            onClick={() => setActionError(null)}
            className="text-red-700 hover:text-red-900"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Dual-Pane Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ========================================================================= */}
        {/* Left Pane (40% width): Triage Queue                                     */}
        {/* ========================================================================= */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white p-3 rounded-xl border border-vana-charcoal/10 shadow-subtle space-y-2">
            {/* Filter Controls */}
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-2.5 top-2.5 text-vana-charcoal/40" />
                <Input
                  placeholder="Filter queue..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 h-9 text-xs bg-vana-ivory/30 border-vana-charcoal/15"
                />
              </div>

              <select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                className="h-9 px-2 rounded-md border border-vana-charcoal/15 bg-white text-xs text-vana-charcoal outline-none max-w-[150px] truncate"
              >
                <option value="ALL">All Projects</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Queue List */}
          <div className="space-y-2.5 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
            {isQueueLoading ? (
              [1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-28 rounded-xl bg-white/70 border border-vana-charcoal/10 animate-pulse p-4 space-y-2"
                >
                  <div className="h-4 bg-vana-charcoal/10 rounded w-1/3" />
                  <div className="h-5 bg-vana-charcoal/10 rounded w-2/3" />
                  <div className="h-3 bg-vana-charcoal/10 rounded w-1/2" />
                </div>
              ))
            ) : filteredQueue.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-xl border border-dashed border-vana-charcoal/20 space-y-2 p-6">
                <ShieldCheck className="w-10 h-10 text-emerald-600 mx-auto" />
                <h4 className="font-heading font-bold text-base text-vana-forest">
                  Triage Queue Clear
                </h4>
                <p className="text-xs text-vana-charcoal/60">
                  All submitted activities have been verified. No pending reviews awaiting sign-off.
                </p>
              </div>
            ) : (
              filteredQueue.map((item) => {
                const isSelected = activeItem?.revision_id === item.revision_id;
                return (
                  <div
                    key={item.revision_id}
                    onClick={() => setSelectedItemId(item.revision_id)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer select-none space-y-2 ${
                      isSelected
                        ? "bg-vana-forest text-white shadow-lifted border-vana-forest"
                        : "bg-white border-vana-charcoal/10 hover:border-vana-forest/40 hover:shadow-subtle"
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span
                        className={`font-mono font-bold tracking-wide uppercase ${
                          isSelected ? "text-vana-sage" : "text-vana-forest"
                        }`}
                      >
                        {item.project_code}
                      </span>
                      <span className={isSelected ? "text-white/70" : "text-vana-charcoal/50"}>
                        {item.activity_date}
                      </span>
                    </div>

                    <div className="flex items-baseline justify-between gap-2">
                      <h4
                        className={`font-heading font-bold text-sm truncate ${
                          isSelected ? "text-white" : "text-vana-charcoal"
                        }`}
                      >
                        {item.metric_code.replace(/_/g, " ")}
                      </h4>
                      <span
                        className={`font-heading font-extrabold text-sm shrink-0 ${
                          isSelected ? "text-white" : "text-vana-forest"
                        }`}
                      >
                        {parseFloat(String(item.quantity)).toLocaleString()} {item.unit}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs pt-1 border-t border-current/10">
                      <span className={isSelected ? "text-white/80" : "text-vana-charcoal/60"}>
                        By: {item.creator_name}
                      </span>

                      <div className="flex items-center gap-1.5">
                        {item.is_amendment && (
                          <span
                            className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                              isSelected
                                ? "bg-amber-400 text-amber-950"
                                : "bg-amber-100 text-amber-900 border border-amber-300"
                            }`}
                          >
                            Amendment (Rev #{item.revision_number})
                          </span>
                        )}

                        {/* Anti-self-verification indicator */}
                        {!item.can_verify && (
                          <span
                            className={`text-[10px] font-bold px-1.5 py-0.5 rounded flex items-center gap-0.5 ${
                              isSelected
                                ? "bg-red-400 text-red-950"
                                : "bg-red-100 text-red-900 border border-red-300"
                            }`}
                          >
                            <Lock className="w-2.5 h-2.5" />
                            Your Submission
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ========================================================================= */}
        {/* Right Pane (60% width): Deep Inspection & Review Actions                */}
        {/* ========================================================================= */}
        <div className="lg:col-span-7">
          {activeItem ? (
            <Card className="border-vana-charcoal/10 shadow-lifted">
              <CardHeader className="pb-4 border-b border-vana-charcoal/10">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-vana-forest uppercase tracking-wider">
                        {activeItem.project_code}
                      </span>
                      <Badge variant="outline" className="text-[10px] uppercase font-bold">
                        Revision #{activeItem.revision_number}
                      </Badge>
                      {activeItem.is_amendment && (
                        <Badge className="bg-amber-100 text-amber-900 border-amber-300 text-[10px]">
                          Amendment
                        </Badge>
                      )}
                    </div>
                    <CardTitle className="text-xl font-heading font-extrabold text-vana-forest mt-1">
                      {activeItem.metric_code.replace(/_/g, " ")}
                    </CardTitle>
                    <CardDescription className="text-xs text-vana-charcoal/70">
                      {activeItem.project_name} · Reported on {activeItem.activity_date}
                    </CardDescription>
                  </div>

                  {/* Submitter Bio Pill */}
                  <div className="text-right">
                    <span className="text-[11px] uppercase tracking-wider text-vana-charcoal/50 font-semibold block">
                      Submitted By
                    </span>
                    <span className="text-sm font-heading font-bold text-vana-charcoal block">
                      {activeItem.creator_name}
                    </span>
                    <span className="text-[10px] text-vana-charcoal/50">
                      {new Date(activeItem.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-5 pt-4">
                {/* Anti-Self-Verification Gate Violation Warning Banner */}
                {!activeItem.can_verify && (
                  <div className="p-4 bg-red-50 border-2 border-red-300 rounded-xl space-y-1.5 text-red-950">
                    <div className="flex items-center gap-2 font-bold text-sm text-red-900">
                      <Lock className="w-4 h-4 text-red-700 shrink-0" />
                      Policy Rule 5 Violation: Anti-Self-Verification Enforced
                    </div>
                    <p className="text-xs text-red-800 leading-relaxed">
                      You are the author of this activity submission (<code className="font-mono">{activeItem.creator_name}</code>). Under permanent engineering boundaries (Rule 5), under no circumstances may a user verify their own activity submission (<code className="font-mono">verifier_id != creator_id</code>).
                    </p>
                    <p className="text-[11px] font-semibold text-red-700">
                      Verification buttons are disabled. Another authorized administrator or assigned project manager must verify this record.
                    </p>
                  </div>
                )}

                {/* Metric Claim & Net Adjustment Breakdown */}
                <div className="bg-vana-ivory/60 rounded-xl p-4 border border-vana-charcoal/10 grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs font-semibold text-vana-charcoal/60 uppercase tracking-wider block">
                      Claimed Quantity
                    </span>
                    <span className="text-2xl font-heading font-extrabold text-vana-forest">
                      {parseFloat(String(activeItem.quantity)).toLocaleString()} {activeItem.unit}
                    </span>
                    <span className="text-[11px] text-vana-charcoal/50 block mt-0.5">
                      Metric Code: {activeItem.metric_code}
                    </span>
                  </div>

                  {activeItem.is_amendment ? (
                    <div>
                      <span className="text-xs font-semibold text-amber-800 uppercase tracking-wider block">
                        Net Adjustment Accounting
                      </span>
                      <div className="flex items-baseline gap-2 mt-0.5">
                        <span className="text-sm font-bold text-vana-charcoal/70 line-through">
                          {activeItem.previously_verified_quantity}
                        </span>
                        <ChevronRight className="w-3.5 h-3.5 text-vana-charcoal/40" />
                        <span className="text-base font-heading font-bold text-vana-forest">
                          {activeItem.quantity} {activeItem.unit}
                        </span>
                      </div>
                      <span className="text-xs font-bold text-amber-900 block mt-1">
                        Ledger Net Impact:{" "}
                        {parseFloat(String(activeItem.net_adjustment)) >= 0
                          ? `+${activeItem.net_adjustment}`
                          : activeItem.net_adjustment}{" "}
                        {activeItem.unit}
                      </span>
                    </div>
                  ) : (
                    <div>
                      <span className="text-xs font-semibold text-vana-charcoal/60 uppercase tracking-wider block">
                        Submission Classification
                      </span>
                      <span className="text-sm font-heading font-bold text-vana-forest mt-1 block">
                        Initial Revision (Rev #1)
                      </span>
                      <span className="text-[11px] text-vana-charcoal/50 block mt-0.5">
                        Previous verified ledger: 0 {activeItem.unit}
                      </span>
                    </div>
                  )}
                </div>

                {/* Location Verification */}
                <div className="bg-white p-3.5 rounded-xl border border-vana-charcoal/10 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-vana-forest shrink-0" />
                    <div>
                      <span className="font-semibold text-vana-charcoal block">
                        GPS Location Verification
                      </span>
                      {activeItem.latitude !== null && activeItem.longitude !== null ? (
                        <span className="font-mono text-vana-charcoal/70">
                          {activeItem.latitude}, {activeItem.longitude}
                        </span>
                      ) : (
                        <span className="text-vana-charcoal/40 italic">
                          No GPS coordinates recorded
                        </span>
                      )}
                    </div>
                  </div>

                  {activeItem.gps_accuracy_meters !== null && (
                    <Badge
                      variant="outline"
                      className={`text-[11px] font-semibold ${
                        activeItem.gps_accuracy_meters <= 25
                          ? "bg-emerald-50 text-emerald-800 border-emerald-300"
                          : "bg-amber-50 text-amber-800 border-amber-300"
                      }`}
                    >
                      Accuracy: ±{activeItem.gps_accuracy_meters}m
                    </Badge>
                  )}
                </div>

                {/* Field Notes */}
                {activeItem.field_notes && (
                  <div>
                    <h4 className="text-xs font-semibold text-vana-charcoal/70 uppercase tracking-wider mb-1">
                      Field Notes & Submitter Observations
                    </h4>
                    <p className="text-xs text-vana-charcoal bg-vana-ivory/40 p-3 rounded-lg border border-vana-charcoal/10 leading-relaxed whitespace-pre-wrap">
                      {activeItem.field_notes}
                    </p>
                  </div>
                )}

                {/* Attached Photo Evidence */}
                <div>
                  <h4 className="text-xs font-semibold text-vana-charcoal/70 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Camera className="w-3.5 h-3.5 text-vana-forest" />
                    Attached Photo Evidence ({activeItem.evidence_files.length})
                  </h4>

                  {activeItem.evidence_files.length === 0 ? (
                    <div className="text-xs text-vana-charcoal/50 italic p-3 bg-vana-ivory/30 rounded border border-dashed border-vana-charcoal/15">
                      No photo evidence files uploaded with this submission.
                    </div>
                  ) : (
                    <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                      {activeItem.evidence_files.map((file) => (
                        <div
                          key={file.id}
                          onClick={() =>
                            setLightboxImageUrl(operationsService.getEvidenceFileUrl(file.id))
                          }
                          className="group relative aspect-square rounded-lg border border-vana-charcoal/20 bg-black/5 overflow-hidden cursor-pointer hover:border-vana-forest shadow-subtle"
                        >
                          <img
                            src={operationsService.getEvidenceFileUrl(file.id)}
                            alt={file.original_filename}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = "none";
                            }}
                          />
                          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <Eye className="w-5 h-5 text-white" />
                          </div>
                          <div className="absolute bottom-0 inset-x-0 bg-black/70 p-1 text-[10px] text-white truncate px-1.5">
                            {file.original_filename}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Review Action Bar */}
                <div className="pt-4 border-t border-vana-charcoal/10 flex items-center justify-end gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    disabled={!activeItem.can_verify || decisionMutation.isPending}
                    onClick={() => {
                      setActionError(null);
                      setIsRejectModalOpen(true);
                    }}
                    className="border-red-300 text-red-700 hover:bg-red-50 hover:text-red-800 gap-1.5 font-semibold"
                  >
                    <XCircle className="w-4 h-4" />
                    Reject Submission
                  </Button>

                  <Button
                    type="button"
                    disabled={!activeItem.can_verify || decisionMutation.isPending}
                    onClick={() => {
                      setActionError(null);
                      setIsApproveModalOpen(true);
                    }}
                    className="bg-vana-forest text-white hover:bg-vana-forest/90 gap-1.5 font-semibold shadow-lifted"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Approve & Verify Activity
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="text-center py-20 bg-white rounded-xl border border-dashed border-vana-charcoal/20 p-8">
              <ShieldCheck className="w-12 h-12 text-vana-sage mx-auto mb-2" />
              <h3 className="font-heading font-bold text-lg text-vana-forest">
                Select a Submission
              </h3>
              <p className="text-xs text-vana-charcoal/60 max-w-sm mx-auto mt-1">
                Choose an item from the pending triage queue on the left to scrutinize evidence and record verification decisions.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 1. Approve Confirmation Modal                                            */}
      {/* ========================================================================= */}
      <Dialog open={isApproveModalOpen} onOpenChange={setIsApproveModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-heading font-extrabold text-vana-forest">
              Confirm Activity Verification
            </DialogTitle>
            <DialogDescription className="text-xs text-vana-charcoal/70">
              Approving this revision will permanently activate it in the official environmental ledger
              and recalculate verified portfolio progress.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="bg-emerald-50/70 p-3 rounded-lg border border-emerald-200 text-xs text-emerald-950 space-y-1">
              <span className="font-bold block">
                Verifying {activeItem?.quantity} {activeItem?.unit} ({activeItem?.metric_code})
              </span>
              <span>Project: {activeItem?.project_name}</span>
            </div>

            <div>
              <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                Verification Review Notes (Optional)
              </label>
              <textarea
                rows={3}
                placeholder="Confirmation of tagged saplings, plot boundary alignment, canopy coverage..."
                value={approveNotes}
                onChange={(e) => setApproveNotes(e.target.value)}
                className="w-full p-2.5 rounded-md border border-vana-charcoal/20 text-xs text-vana-charcoal focus:ring-1 focus:ring-vana-forest outline-none"
              />
            </div>

            <DialogFooter className="gap-2 sm:gap-0 pt-2">
              <Button type="button" variant="outline" onClick={() => setIsApproveModalOpen(false)}>
                Cancel
              </Button>
              <Button
                type="button"
                onClick={handleApprove}
                disabled={decisionMutation.isPending}
                className="bg-vana-forest text-white hover:bg-vana-forest/90"
              >
                {decisionMutation.isPending ? "Recording Sign-off..." : "Confirm & Sign Off"}
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>

      {/* ========================================================================= */}
      {/* 2. Rejection Modal (Mandatory Reason Code & Review Notes)                */}
      {/* ========================================================================= */}
      <Dialog open={isRejectModalOpen} onOpenChange={setIsRejectModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-heading font-extrabold text-red-900">
              Reject Field Submission
            </DialogTitle>
            <DialogDescription className="text-xs text-vana-charcoal/70">
              Rejections require selecting a calibrated reason code and providing constructive feedback
              so the field officer can submit an amended revision.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Reason Code Picker */}
            <div>
              <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                Rejection Reason Code *
              </label>
              <select
                value={rejectionReasonCode}
                onChange={(e) => setRejectionReasonCode(e.target.value as RejectionReasonCode)}
                className="w-full h-10 px-3 rounded-md border border-vana-charcoal/20 bg-white text-xs font-medium text-vana-charcoal focus:ring-1 focus:ring-red-600 outline-none"
              >
                {REJECTION_REASONS.map((r) => (
                  <option key={r.code} value={r.code}>
                    {r.label} ({r.code})
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-vana-charcoal/60 mt-1 italic">
                {REJECTION_REASONS.find((r) => r.code === rejectionReasonCode)?.description}
              </p>
            </div>

            {/* Mandatory Notes */}
            <div>
              <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                Review Notes & Feedback *
              </label>
              <textarea
                required
                rows={3}
                placeholder="Explain the deficiency (e.g. Photo blur prevents sapling count; coordinates 200m outside sector boundary)..."
                value={rejectionNotes}
                onChange={(e) => setRejectionNotes(e.target.value)}
                className="w-full p-2.5 rounded-md border border-vana-charcoal/20 text-xs text-vana-charcoal focus:ring-1 focus:ring-red-600 outline-none"
              />
              <span className="text-[10px] text-vana-charcoal/50 block text-right">
                Mandatory audit record
              </span>
            </div>

            <DialogFooter className="gap-2 sm:gap-0 pt-2">
              <Button type="button" variant="outline" onClick={() => setIsRejectModalOpen(false)}>
                Cancel
              </Button>
              <Button
                type="button"
                variant="destructive"
                onClick={handleReject}
                disabled={decisionMutation.isPending}
                className="bg-red-700 hover:bg-red-800 text-white"
              >
                {decisionMutation.isPending ? "Rejecting..." : "Confirm Rejection"}
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>

      {/* ========================================================================= */}
      {/* 3. Lightbox Image Viewer                                                 */}
      {/* ========================================================================= */}
      {lightboxImageUrl && (
        <div
          className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-4"
          onClick={() => setLightboxImageUrl(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh] bg-white rounded-xl overflow-hidden shadow-2xl p-2">
            <button
              onClick={() => setLightboxImageUrl(null)}
              className="absolute top-4 right-4 bg-black/60 text-white rounded-full p-1.5 hover:bg-black/90"
            >
              <X className="w-5 h-5" />
            </button>
            <img
              src={lightboxImageUrl}
              alt="Evidence Inspection Full"
              className="max-h-[80vh] w-auto mx-auto object-contain rounded"
            />
          </div>
        </div>
      )}
    </div>
  );
};
