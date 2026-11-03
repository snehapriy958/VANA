import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Plus,
  Search,
  MapPin,
  Camera,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Clock,
  XCircle,
  FileText,
  Trash2,
  Eye,
  RefreshCw,
  X,
  History,
  Sparkles,
} from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { operationsService } from "@/services/operations";
import { listProjects } from "@/services/projects";
import { getMetricsCatalog } from "@/services/metrics";
import { FieldActivity, ActivityStatus } from "@/types/operations";
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

const DRAFT_STORAGE_KEY = "vana_field_activity_draft";

export const FieldOperationsView: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // Search and Filter State
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [selectedProjectId, setSelectedProjectId] = useState<string>("ALL");
  const [selectedMetricCode, setSelectedMetricCode] = useState<string>("ALL");

  // Modals
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [isAmendModalOpen, setIsAmendModalOpen] = useState(false);
  const [selectedActivity, setSelectedActivity] = useState<FieldActivity | null>(null);
  const [lightboxImageUrl, setLightboxImageUrl] = useState<string | null>(null);

  // Form State for New Activity
  const [formProjectId, setFormProjectId] = useState("");
  const [formMetricCode, setFormMetricCode] = useState("");
  const [formUnit, setFormUnit] = useState("");
  const [formQuantity, setFormQuantity] = useState("");
  const [formDate, setFormDate] = useState(new Date().toISOString().split("T")[0]);
  const [formLatitude, setFormLatitude] = useState<number | null>(null);
  const [formLongitude, setFormLongitude] = useState<number | null>(null);
  const [formGpsAccuracy, setFormGpsAccuracy] = useState<number | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [formNotes, setFormNotes] = useState("");
  const [formFiles, setFormFiles] = useState<File[]>([]);
  const [formError, setFormError] = useState<string | null>(null);

  // Form State for Amendment
  const [amendQuantity, setAmendQuantity] = useState("");
  const [amendDate, setAmendDate] = useState(new Date().toISOString().split("T")[0]);
  const [amendReason, setAmendReason] = useState("");
  const [amendNotes, setAmendNotes] = useState("");
  const [amendFiles, setAmendFiles] = useState<File[]>([]);
  const [amendError, setAmendError] = useState<string | null>(null);

  // Queries
  const {
    data: activities = [],
    isLoading: activitiesLoading,
    refetch: refetchActivities,
  } = useQuery({
    queryKey: ["field-activities", selectedProjectId, statusFilter, selectedMetricCode],
    queryFn: () =>
      operationsService.getActivities({
        projectId: selectedProjectId !== "ALL" ? selectedProjectId : undefined,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
        metricCode: selectedMetricCode !== "ALL" ? selectedMetricCode : undefined,
      }),
  });

  const { data: projects = [] } = useQuery({
    queryKey: ["projects-dropdown"],
    queryFn: () => listProjects(),
  });

  const { data: metricCatalog = [] } = useQuery({
    queryKey: ["metric-catalog"],
    queryFn: () => getMetricsCatalog(),
  });

  // Load draft from sessionStorage on mount
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(DRAFT_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.projectId) setFormProjectId(parsed.projectId);
        if (parsed.metricCode) setFormMetricCode(parsed.metricCode);
        if (parsed.unit) setFormUnit(parsed.unit);
        if (parsed.quantity) setFormQuantity(parsed.quantity);
        if (parsed.notes) setFormNotes(parsed.notes);
      }
    } catch {
      // Ignore parse error
    }
  }, []);

  // Save draft to sessionStorage
  const saveDraft = (data: {
    projectId?: string;
    metricCode?: string;
    unit?: string;
    quantity?: string;
    notes?: string;
  }) => {
    try {
      sessionStorage.setItem(
        DRAFT_STORAGE_KEY,
        JSON.stringify({
          projectId: data.projectId ?? formProjectId,
          metricCode: data.metricCode ?? formMetricCode,
          unit: data.unit ?? formUnit,
          quantity: data.quantity ?? formQuantity,
          notes: data.notes ?? formNotes,
        })
      );
    } catch {
      // Ignore storage error
    }
  };

  const clearDraft = () => {
    sessionStorage.removeItem(DRAFT_STORAGE_KEY);
  };

  // GPS Geolocation Handler
  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setFormError("Geolocation is not supported by your browser.");
      return;
    }
    setIsLocating(true);
    setFormError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setFormLatitude(Number(pos.coords.latitude.toFixed(6)));
        setFormLongitude(Number(pos.coords.longitude.toFixed(6)));
        setFormGpsAccuracy(Math.round(pos.coords.accuracy));
        setIsLocating(false);
      },
      (err) => {
        setFormError(`Location capture failed: ${err.message}`);
        setIsLocating(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  };

  // Submit Activity Mutation
  const createActivityMutation = useMutation({
    mutationFn: (formData: FormData) => operationsService.createActivity(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["field-activities"] });
      queryClient.invalidateQueries({ queryKey: ["verification-queue"] });
      clearDraft();
      setIsSubmitModalOpen(false);
      resetSubmitForm();
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.message || "Failed to submit activity";
      setFormError(msg);
    },
  });

  const amendActivityMutation = useMutation({
    mutationFn: ({ activityId, formData }: { activityId: string; formData: FormData }) =>
      operationsService.amendActivity(activityId, formData),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["field-activities"] });
      queryClient.invalidateQueries({ queryKey: ["verification-queue"] });
      setSelectedActivity(updated);
      setIsAmendModalOpen(false);
      resetAmendForm();
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail?.message || err.message || "Failed to amend activity";
      setAmendError(msg);
    },
  });

  const archiveActivityMutation = useMutation({
    mutationFn: (activityId: string) => operationsService.archiveActivity(activityId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["field-activities"] });
      queryClient.invalidateQueries({ queryKey: ["verification-queue"] });
      setSelectedActivity(null);
    },
  });

  const resetSubmitForm = () => {
    setFormProjectId("");
    setFormMetricCode("");
    setFormUnit("");
    setFormQuantity("");
    setFormDate(new Date().toISOString().split("T")[0]);
    setFormLatitude(null);
    setFormLongitude(null);
    setFormGpsAccuracy(null);
    setFormNotes("");
    setFormFiles([]);
    setFormError(null);
  };

  const resetAmendForm = () => {
    setAmendQuantity("");
    setAmendDate(new Date().toISOString().split("T")[0]);
    setAmendReason("");
    setAmendNotes("");
    setAmendFiles([]);
    setAmendError(null);
  };

  const handleSubmitActivity = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!formProjectId) {
      setFormError("Please select a target project.");
      return;
    }
    if (!formMetricCode) {
      setFormError("Please select an environmental metric.");
      return;
    }
    const qtyNum = parseFloat(formQuantity);
    if (isNaN(qtyNum) || qtyNum <= 0) {
      setFormError("Quantity must be a positive number greater than 0.");
      return;
    }

    const formData = new FormData();
    formData.append("project_id", formProjectId);
    formData.append("metric_code", formMetricCode);
    formData.append("quantity", formQuantity);
    formData.append("unit", formUnit);
    formData.append("activity_date", formDate);

    if (formLatitude !== null) formData.append("latitude", String(formLatitude));
    if (formLongitude !== null) formData.append("longitude", String(formLongitude));
    if (formGpsAccuracy !== null) formData.append("gps_accuracy_meters", String(formGpsAccuracy));
    if (formNotes.trim()) formData.append("field_notes", formNotes.trim());

    formFiles.forEach((f) => formData.append("evidence_files", f));

    createActivityMutation.mutate(formData);
  };

  const handleAmendSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedActivity) return;
    setAmendError(null);

    const qtyNum = parseFloat(amendQuantity);
    if (isNaN(qtyNum) || qtyNum <= 0) {
      setAmendError("Amended quantity must be a positive number.");
      return;
    }

    const formData = new FormData();
    formData.append("quantity", amendQuantity);
    formData.append("activity_date", amendDate);
    if (amendReason.trim()) formData.append("amendment_reason", amendReason.trim());
    if (amendNotes.trim()) formData.append("field_notes", amendNotes.trim());

    amendFiles.forEach((f) => formData.append("evidence_files", f));

    amendActivityMutation.mutate({
      activityId: selectedActivity.id,
      formData,
    });
  };

  // When metric code changes in submit form, select default unit
  const handleMetricChange = (code: string) => {
    setFormMetricCode(code);
    saveDraft({ metricCode: code });
    const def = metricCatalog.find((m) => m.metric_code === code);
    if (def && def.supported_units.length > 0) {
      setFormUnit(def.supported_units[0]);
      saveDraft({ unit: def.supported_units[0] });
    }
  };

  // Filter activities by client-side search query
  const filteredActivities = activities.filter((act) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      act.metric_code.toLowerCase().includes(q) ||
      (act.project_name && act.project_name.toLowerCase().includes(q)) ||
      (act.project_code && act.project_code.toLowerCase().includes(q)) ||
      (act.created_by_name && act.created_by_name.toLowerCase().includes(q))
    );
  });

  const getStatusBadge = (status: ActivityStatus) => {
    switch (status) {
      case "VERIFIED":
        return (
          <Badge className="bg-vana-forest/15 text-vana-forest border-vana-forest/20 hover:bg-vana-forest/20 gap-1 font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5 text-vana-forest" />
            Verified
          </Badge>
        );
      case "PENDING":
        return (
          <Badge className="bg-amber-100 text-amber-900 border-amber-300 gap-1 font-semibold">
            <Clock className="w-3.5 h-3.5 text-amber-700" />
            Pending Review
          </Badge>
        );
      case "REJECTED":
        return (
          <Badge className="bg-red-100 text-red-900 border-red-300 gap-1 font-semibold">
            <XCircle className="w-3.5 h-3.5 text-red-700" />
            Rejected
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const selectedMetricDef = metricCatalog.find((m) => m.metric_code === formMetricCode);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-vana-charcoal/10">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-heading font-extrabold text-vana-forest tracking-tight">
              Field Operations & Reporting
            </h1>
            <Badge variant="outline" className="text-xs bg-vana-sage/15 text-vana-forest border-vana-sage/30">
              Mobile-First Ledger
            </Badge>
          </div>
          <p className="text-sm text-vana-charcoal/70 mt-1">
            Capture on-site environmental activities, photo evidence, and manage revision history.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchActivities()}
            className="h-11 border-vana-forest/20 text-vana-forest hover:bg-vana-sage/15 gap-1.5"
          >
            <RefreshCw className="w-4 h-4" />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
          <Button
            onClick={() => {
              resetSubmitForm();
              setIsSubmitModalOpen(true);
            }}
            className="bg-vana-forest text-white hover:bg-vana-forest/90 shadow-lifted gap-2 h-11 px-5"
          >
            <Plus className="w-4 h-4" />
            Report Field Activity
          </Button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-vana-charcoal/10 shadow-subtle space-y-3">
        <div className="flex flex-col md:flex-row gap-3">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-3 text-vana-charcoal/40" />
            <Input
              placeholder="Search by project, metric, or submitter..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 bg-vana-ivory/30 border-vana-charcoal/15 focus-visible:ring-vana-forest"
            />
          </div>

          {/* Project Dropdown */}
          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            className="h-10 px-3 rounded-md border border-vana-charcoal/15 bg-white text-sm text-vana-charcoal focus:ring-1 focus:ring-vana-forest outline-none"
          >
            <option value="ALL">All Assigned Projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.code})
              </option>
            ))}
          </select>

          {/* Metric Dropdown */}
          <select
            value={selectedMetricCode}
            onChange={(e) => setSelectedMetricCode(e.target.value)}
            className="h-10 px-3 rounded-md border border-vana-charcoal/15 bg-white text-sm text-vana-charcoal focus:ring-1 focus:ring-vana-forest outline-none"
          >
            <option value="ALL">All Metrics</option>
            {metricCatalog.map((m) => (
              <option key={m.metric_code} value={m.metric_code}>
                {m.display_name} ({m.metric_code})
              </option>
            ))}
          </select>

          {/* Status Tabs */}
          <div className="inline-flex rounded-lg border border-vana-charcoal/15 p-0.5 bg-vana-ivory/50">
            {["ALL", "PENDING", "VERIFIED", "REJECTED"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                  statusFilter === st
                    ? "bg-vana-forest text-white shadow-subtle"
                    : "text-vana-charcoal/70 hover:text-vana-charcoal"
                }`}
              >
                {st === "ALL" ? "All" : st.charAt(0) + st.slice(1).toLowerCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Activity Records Stream */}
      {activitiesLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="h-48 rounded-xl bg-white/70 border border-vana-charcoal/10 animate-pulse p-5 space-y-3"
            >
              <div className="h-4 bg-vana-charcoal/10 rounded w-1/3" />
              <div className="h-6 bg-vana-charcoal/10 rounded w-2/3" />
              <div className="h-4 bg-vana-charcoal/10 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : filteredActivities.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-dashed border-vana-charcoal/20 space-y-3">
          <div className="w-12 h-12 rounded-full bg-vana-sage/20 text-vana-forest flex items-center justify-center mx-auto">
            <FileText className="w-6 h-6" />
          </div>
          <h3 className="font-heading font-bold text-lg text-vana-forest">No Field Activities Found</h3>
          <p className="text-sm text-vana-charcoal/60 max-w-sm mx-auto">
            {activities.length === 0
              ? "No activities have been recorded yet. Click 'Report Field Activity' to submit on-site restoration data."
              : "No activities match your current filter parameters. Try clearing filters."}
          </p>
          {activities.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchQuery("");
                setStatusFilter("ALL");
                setSelectedProjectId("ALL");
                setSelectedMetricCode("ALL");
              }}
            >
              Reset Filters
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredActivities.map((activity) => {
            const currentRev = activity.current_revision;
            const status = (currentRev?.status || "PENDING") as ActivityStatus;
            const netAdj = activity.net_pending_adjustment;
            const verifiedQty = parseFloat(String(activity.active_verified_quantity || "0"));

            return (
              <Card
                key={activity.id}
                className="hover:shadow-lifted transition-all duration-200 border-vana-charcoal/10 cursor-pointer flex flex-col justify-between"
                onClick={() => setSelectedActivity(activity)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-semibold text-vana-forest tracking-wide uppercase">
                      {activity.project_code || "VANA-PROJECT"}
                    </span>
                    {getStatusBadge(status)}
                  </div>
                  <CardTitle className="text-base font-heading font-bold text-vana-forest line-clamp-1">
                    {activity.metric_code.replace(/_/g, " ")}
                  </CardTitle>
                  <CardDescription className="text-xs line-clamp-1 text-vana-charcoal/60">
                    {activity.project_name || "Assigned Project"}
                  </CardDescription>
                </CardHeader>

                <CardContent className="space-y-4 pt-0">
                  {/* Ledger Figures Display */}
                  <div className="bg-vana-ivory/50 rounded-lg p-3 border border-vana-charcoal/5 flex items-center justify-between">
                    <div>
                      <span className="text-[11px] uppercase tracking-wider text-vana-charcoal/60 font-semibold block">
                        Verified Total
                      </span>
                      <span className="text-lg font-heading font-bold text-vana-forest">
                        {verifiedQty.toLocaleString()} {activity.unit}
                      </span>
                    </div>

                    {/* Net Adjustment Callout if pending */}
                    {status === "PENDING" && netAdj !== null && (
                      <div className="text-right">
                        <span className="text-[11px] uppercase tracking-wider text-amber-800 font-semibold block">
                          Net Pending
                        </span>
                        <span
                          className={`text-sm font-heading font-bold px-2 py-0.5 rounded ${
                            parseFloat(String(netAdj)) >= 0
                              ? "bg-amber-100 text-amber-900 border border-amber-300"
                              : "bg-red-100 text-red-900 border border-red-300"
                          }`}
                        >
                          {parseFloat(String(netAdj)) >= 0 ? `+${netAdj}` : netAdj} {activity.unit}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Submission Metadata */}
                  <div className="text-xs text-vana-charcoal/70 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-vana-charcoal/40" />
                        {currentRev?.activity_date || "Date unspecified"}
                      </span>
                      <span className="text-vana-charcoal/50">
                        Rev #{currentRev?.revision_number || 1}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-vana-charcoal/60 truncate max-w-[180px]">
                        By: {activity.created_by_name || "Field Officer"}
                      </span>
                      {currentRev?.evidence_files && currentRev.evidence_files.length > 0 && (
                        <span className="inline-flex items-center gap-1 text-vana-forest font-medium">
                          <Camera className="w-3.5 h-3.5" />
                          {currentRev.evidence_files.length} Photo{currentRev.evidence_files.length > 1 ? "s" : ""}
                        </span>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 1. Report Field Activity Modal (Screen 06 Mobile-Optimized Form)         */}
      {/* ========================================================================= */}
      <Dialog open={isSubmitModalOpen} onOpenChange={setIsSubmitModalOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-heading font-extrabold text-vana-forest">
              Report Field Activity
            </DialogTitle>
            <DialogDescription className="text-sm text-vana-charcoal/70">
              Submit on-site environmental restoration evidence with GPS coordinates and photos.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmitActivity} className="space-y-4 py-2">
            {formError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <span>{formError}</span>
              </div>
            )}

            {/* Target Project */}
            <div>
              <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                Target Project *
              </label>
              <select
                required
                value={formProjectId}
                onChange={(e) => {
                  setFormProjectId(e.target.value);
                  saveDraft({ projectId: e.target.value });
                }}
                className="w-full h-10 px-3 rounded-md border border-vana-charcoal/20 bg-white text-sm text-vana-charcoal focus:ring-1 focus:ring-vana-forest outline-none"
              >
                <option value="">Select an assigned project...</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.code})
                  </option>
                ))}
              </select>
            </div>

            {/* Metric Code */}
            <div>
              <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                Environmental Metric *
              </label>
              <select
                required
                value={formMetricCode}
                onChange={(e) => handleMetricChange(e.target.value)}
                className="w-full h-10 px-3 rounded-md border border-vana-charcoal/20 bg-white text-sm text-vana-charcoal focus:ring-1 focus:ring-vana-forest outline-none"
              >
                <option value="">Select metric...</option>
                {metricCatalog.map((m) => (
                  <option key={m.metric_code} value={m.metric_code}>
                    {m.display_name} ({m.category})
                  </option>
                ))}
              </select>
              {selectedMetricDef && (
                <p className="text-[11px] text-vana-charcoal/60 mt-1 italic">
                  {selectedMetricDef.methodology_summary}
                </p>
              )}
            </div>

            {/* Quantity and Unit Pill Group */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                  Quantity *
                </label>
                <Input
                  required
                  type="number"
                  step="any"
                  min="0.01"
                  placeholder="e.g. 250"
                  value={formQuantity}
                  onChange={(e) => {
                    setFormQuantity(e.target.value);
                    saveDraft({ quantity: e.target.value });
                  }}
                  className="h-10 text-base font-semibold"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                  Unit
                </label>
                <select
                  value={formUnit}
                  onChange={(e) => {
                    setFormUnit(e.target.value);
                    saveDraft({ unit: e.target.value });
                  }}
                  className="w-full h-10 px-3 rounded-md border border-vana-charcoal/20 bg-white text-sm text-vana-charcoal focus:ring-1 focus:ring-vana-forest outline-none"
                >
                  {selectedMetricDef?.supported_units.map((u) => (
                    <option key={u} value={u}>
                      {u}
                    </option>
                  )) || <option value="units">units</option>}
                </select>
              </div>
            </div>

            {/* Activity Date */}
            <div>
              <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                Date of Execution *
              </label>
              <Input
                required
                type="date"
                value={formDate}
                onChange={(e) => setFormDate(e.target.value)}
                className="h-10"
              />
            </div>

            {/* GPS Location Capture Button */}
            <div className="bg-vana-ivory/50 p-3 rounded-lg border border-vana-charcoal/10 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-vana-charcoal/80 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-vana-forest" />
                  GPS Coordinates
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleGetLocation}
                  disabled={isLocating}
                  className="h-8 text-xs gap-1 border-vana-forest/30 text-vana-forest hover:bg-vana-sage/15"
                >
                  {isLocating ? (
                    <RefreshCw className="w-3 h-3 animate-spin" />
                  ) : (
                    <MapPin className="w-3 h-3" />
                  )}
                  {isLocating ? "Locating..." : "Capture Location"}
                </Button>
              </div>

              {formLatitude !== null && formLongitude !== null ? (
                <div className="text-xs space-y-1">
                  <div className="font-mono text-vana-charcoal/90">
                    Lat: {formLatitude}, Lng: {formLongitude}
                  </div>
                  {formGpsAccuracy !== null && (
                    <div
                      className={`text-[11px] font-medium flex items-center gap-1 ${
                        formGpsAccuracy > 25 ? "text-amber-700" : "text-vana-forest"
                      }`}
                    >
                      <span>Accuracy: ±{formGpsAccuracy} meters</span>
                      {formGpsAccuracy > 25 && (
                        <span>(Warning: low GPS accuracy; move to open sky)</span>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-[11px] text-vana-charcoal/50">
                  Tap 'Capture Location' to verify on-site presence via device GPS.
                </p>
              )}
            </div>

            {/* Photo Evidence Upload */}
            <div>
              <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                Photo Evidence (Max 5 photos, JPEG/PNG/WEBP/PDF, max 10MB each)
              </label>
              <input
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp,application/pdf"
                capture="environment"
                onChange={(e) => {
                  if (e.target.files) {
                    const newFiles = Array.from(e.target.files);
                    setFormFiles((prev) => [...prev, ...newFiles].slice(0, 5));
                  }
                }}
                className="w-full text-xs text-vana-charcoal/70 file:mr-3 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-vana-forest file:text-white hover:file:bg-vana-forest/90"
              />

              {/* Thumbnails */}
              {formFiles.length > 0 && (
                <div className="flex gap-2 mt-2 overflow-x-auto py-1">
                  {formFiles.map((f, idx) => (
                    <div key={idx} className="relative group shrink-0">
                      <div className="w-16 h-16 rounded-md bg-vana-charcoal/10 border border-vana-charcoal/20 overflow-hidden flex items-center justify-center">
                        {f.type.startsWith("image/") ? (
                          <img
                            src={URL.createObjectURL(f)}
                            alt="preview"
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <FileText className="w-6 h-6 text-vana-charcoal/40" />
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => setFormFiles((prev) => prev.filter((_, i) => i !== idx))}
                        className="absolute -top-1 -right-1 bg-red-600 text-white rounded-full p-0.5 opacity-90 hover:opacity-100 shadow"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Field Notes */}
            <div>
              <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                Field Observations & Notes
              </label>
              <textarea
                rows={3}
                placeholder="Details on species planted, soil condition, plot boundaries, tags..."
                value={formNotes}
                onChange={(e) => {
                  setFormNotes(e.target.value);
                  saveDraft({ notes: e.target.value });
                }}
                className="w-full p-3 rounded-md border border-vana-charcoal/20 bg-white text-sm text-vana-charcoal focus:ring-1 focus:ring-vana-forest outline-none"
              />
            </div>

            <DialogFooter className="gap-2 sm:gap-0 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsSubmitModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createActivityMutation.isPending}
                className="bg-vana-forest text-white hover:bg-vana-forest/90 gap-1.5"
              >
                {createActivityMutation.isPending ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Submitting Field Report...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    Submit for Verification
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ========================================================================= */}
      {/* 2. Detailed Activity Inspection & Revision Lineage Drawer                 */}
      {/* ========================================================================= */}
      {selectedActivity && (
        <Dialog open={Boolean(selectedActivity)} onOpenChange={() => setSelectedActivity(null)}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-mono font-bold text-vana-forest uppercase">
                  {selectedActivity.project_code}
                </span>
                {getStatusBadge(
                  (selectedActivity.current_revision?.status || "PENDING") as ActivityStatus
                )}
              </div>
              <DialogTitle className="text-xl font-heading font-extrabold text-vana-forest">
                {selectedActivity.metric_code.replace(/_/g, " ")}
              </DialogTitle>
              <DialogDescription className="text-xs text-vana-charcoal/60">
                {selectedActivity.project_name} · Reported by {selectedActivity.created_by_name}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-5 py-2">
              {/* Ledger Summary Card */}
              <div className="bg-vana-ivory/60 rounded-xl p-4 border border-vana-charcoal/10 grid grid-cols-2 gap-4">
                <div>
                  <span className="text-xs font-semibold text-vana-charcoal/60 uppercase tracking-wider block">
                    Active Verified Quantity
                  </span>
                  <span className="text-2xl font-heading font-extrabold text-vana-forest">
                    {parseFloat(String(selectedActivity.active_verified_quantity || "0")).toLocaleString()}{" "}
                    {selectedActivity.unit}
                  </span>
                  <span className="text-[11px] text-vana-charcoal/50 block mt-0.5">
                    Contributes to official environmental total
                  </span>
                </div>

                <div>
                  <span className="text-xs font-semibold text-vana-charcoal/60 uppercase tracking-wider block">
                    Current Pending Claim
                  </span>
                  {selectedActivity.current_revision?.status === "PENDING" ? (
                    <div>
                      <span className="text-2xl font-heading font-extrabold text-amber-900">
                        {parseFloat(
                          String(selectedActivity.current_revision.quantity)
                        ).toLocaleString()}{" "}
                        {selectedActivity.unit}
                      </span>
                      {selectedActivity.net_pending_adjustment !== null && (
                        <span className="text-xs font-bold text-amber-800 block">
                          Net Adjustment:{" "}
                          {parseFloat(String(selectedActivity.net_pending_adjustment)) >= 0
                            ? `+${selectedActivity.net_pending_adjustment}`
                            : selectedActivity.net_pending_adjustment}{" "}
                          {selectedActivity.unit}
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-sm text-vana-charcoal/50 italic">
                      No pending revisions under review
                    </span>
                  )}
                </div>
              </div>

              {/* Revision History Lineage */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-heading font-bold text-vana-forest flex items-center gap-1.5">
                    <History className="w-4 h-4 text-vana-sage" />
                    Immutable Revision History ({selectedActivity.revisions?.length || 1})
                  </h4>

                  {/* Submit Amendment Button */}
                  {selectedActivity.current_revision?.status !== "PENDING" && !selectedActivity.is_archived && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        resetAmendForm();
                        setAmendQuantity(String(selectedActivity.current_revision?.quantity || ""));
                        setIsAmendModalOpen(true);
                      }}
                      className="text-xs gap-1 border-vana-forest/30 text-vana-forest hover:bg-vana-sage/15"
                    >
                      <Sparkles className="w-3 h-3" />
                      Submit Amendment
                    </Button>
                  )}
                </div>

                <div className="space-y-3 border-l-2 border-vana-sage/30 pl-4 ml-2">
                  {selectedActivity.revisions?.map((rev) => {
                    const revStatus = rev.status as ActivityStatus;
                    return (
                      <div
                        key={rev.id}
                        className={`p-3 rounded-lg border text-xs space-y-2 ${
                          rev.is_active_ledger_entry
                            ? "bg-emerald-50/50 border-emerald-200"
                            : revStatus === "REJECTED"
                            ? "bg-red-50/40 border-red-200"
                            : "bg-white border-vana-charcoal/10"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-heading font-bold text-vana-charcoal">
                            Revision #{rev.revision_number} — {rev.quantity} {selectedActivity.unit}
                          </span>
                          <div className="flex items-center gap-2">
                            {rev.is_active_ledger_entry && (
                              <Badge className="bg-emerald-600 text-white text-[10px] py-0">
                                Active in Ledger
                              </Badge>
                            )}
                            {getStatusBadge(revStatus)}
                          </div>
                        </div>

                        <div className="text-[11px] text-vana-charcoal/70 flex flex-wrap gap-x-4 gap-y-1">
                          <span>Date: {rev.activity_date}</span>
                          {rev.latitude !== null && rev.longitude !== null && (
                            <span>
                              GPS: {rev.latitude}, {rev.longitude} (±{rev.gps_accuracy_meters}m)
                            </span>
                          )}
                          {rev.verifier_name && (
                            <span>
                              Reviewer: {rev.verifier_name} ({new Date(rev.verified_at!).toLocaleDateString()})
                            </span>
                          )}
                        </div>

                        {rev.field_notes && (
                          <p className="text-xs text-vana-charcoal/80 bg-vana-ivory/40 p-2 rounded border border-vana-charcoal/5 italic">
                            "{rev.field_notes}"
                          </p>
                        )}

                        {/* Rejection notice if rejected */}
                        {revStatus === "REJECTED" && (
                          <div className="p-2.5 bg-red-100/60 rounded border border-red-200 text-red-900 space-y-1">
                            <span className="font-bold flex items-center gap-1">
                              <AlertTriangle className="w-3.5 h-3.5 text-red-700" />
                              Rejection Reason: {rev.rejection_reason_code}
                            </span>
                            <p className="italic text-[11px]">{rev.review_notes}</p>
                          </div>
                        )}

                        {/* Revision Evidence Files */}
                        {rev.evidence_files && rev.evidence_files.length > 0 && (
                          <div className="pt-1">
                            <span className="text-[11px] font-semibold text-vana-charcoal/70 block mb-1">
                              Attached Evidence:
                            </span>
                            <div className="flex gap-2 overflow-x-auto">
                              {rev.evidence_files.map((file) => (
                                <div
                                  key={file.id}
                                  onClick={() =>
                                    setLightboxImageUrl(
                                      operationsService.getEvidenceFileUrl(file.id)
                                    )
                                  }
                                  className="w-14 h-14 rounded-md border border-vana-charcoal/20 bg-white overflow-hidden cursor-pointer hover:border-vana-forest relative group"
                                >
                                  <img
                                    src={operationsService.getEvidenceFileUrl(file.id)}
                                    alt={file.original_filename}
                                    className="w-full h-full object-cover"
                                    onError={(e) => {
                                      // Fallback icon if preview fails
                                      (e.target as HTMLElement).style.display = "none";
                                    }}
                                  />
                                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                                    <Eye className="w-4 h-4 text-white" />
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Actions Footer */}
              <div className="flex items-center justify-between pt-4 border-t border-vana-charcoal/10">
                {(user?.role === "ADMIN" || user?.role === "PROJECT_MANAGER") &&
                  !selectedActivity.is_archived && (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => {
                        if (
                          window.confirm(
                            "Are you sure you want to archive this activity? This will remove its active ledger contribution."
                          )
                        ) {
                          archiveActivityMutation.mutate(selectedActivity.id);
                        }
                      }}
                      disabled={archiveActivityMutation.isPending}
                      className="text-xs gap-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Archive Activity
                    </Button>
                  )}

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedActivity(null)}
                  className="ml-auto text-xs"
                >
                  Close Inspection
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* ========================================================================= */}
      {/* 3. Submit Amendment Modal                                                */}
      {/* ========================================================================= */}
      <Dialog open={isAmendModalOpen} onOpenChange={setIsAmendModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-heading font-extrabold text-vana-forest">
              Amend Activity #{selectedActivity?.project_code}
            </DialogTitle>
            <DialogDescription className="text-xs text-vana-charcoal/70">
              Submit an updated revision with net adjustment calculation. The existing verified quantity
              remains official until this amendment is verified.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleAmendSubmit} className="space-y-4 py-2">
            {amendError && (
              <div className="p-2.5 bg-red-50 border border-red-200 rounded text-xs text-red-800">
                {amendError}
              </div>
            )}

            <div>
              <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                Amended Quantity ({selectedActivity?.unit}) *
              </label>
              <Input
                required
                type="number"
                step="any"
                min="0.01"
                placeholder="Amended quantity"
                value={amendQuantity}
                onChange={(e) => setAmendQuantity(e.target.value)}
                className="h-10 text-base font-semibold"
              />
              {selectedActivity?.active_verified_quantity && (
                <div className="text-[11px] text-vana-charcoal/60 mt-1 flex justify-between">
                  <span>Currently Verified: {selectedActivity.active_verified_quantity} {selectedActivity.unit}</span>
                  {amendQuantity && !isNaN(parseFloat(amendQuantity)) && (
                    <span className="font-bold text-vana-forest">
                      Net: {parseFloat(amendQuantity) - parseFloat(String(selectedActivity.active_verified_quantity))} {selectedActivity.unit}
                    </span>
                  )}
                </div>
              )}
            </div>

            <div>
              <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                Execution / Survey Date *
              </label>
              <Input
                required
                type="date"
                value={amendDate}
                onChange={(e) => setAmendDate(e.target.value)}
                className="h-10"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                Amendment Reason *
              </label>
              <Input
                required
                placeholder="e.g. Additional saplings planted in furrow; survival recount..."
                value={amendReason}
                onChange={(e) => setAmendReason(e.target.value)}
                className="h-10 text-sm"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                Field Notes
              </label>
              <textarea
                rows={2}
                placeholder="Additional survey notes..."
                value={amendNotes}
                onChange={(e) => setAmendNotes(e.target.value)}
                className="w-full p-2.5 rounded-md border border-vana-charcoal/20 text-xs text-vana-charcoal focus:ring-1 focus:ring-vana-forest outline-none"
              />
            </div>

            {/* Additional Evidence Photos */}
            <div>
              <label className="text-xs font-semibold text-vana-charcoal/80 uppercase tracking-wide block mb-1">
                Additional Photos (Optional)
              </label>
              <input
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp,application/pdf"
                onChange={(e) => {
                  if (e.target.files) {
                    setAmendFiles(Array.from(e.target.files));
                  }
                }}
                className="w-full text-xs text-vana-charcoal/70 file:mr-2 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-vana-forest file:text-white"
              />
            </div>

            <DialogFooter className="gap-2 sm:gap-0 pt-2">
              <Button type="button" variant="outline" onClick={() => setIsAmendModalOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={amendActivityMutation.isPending}
                className="bg-vana-forest text-white hover:bg-vana-forest/90"
              >
                {amendActivityMutation.isPending ? "Submitting..." : "Submit Revision"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ========================================================================= */}
      {/* 4. Lightbox Image Viewer                                                 */}
      {/* ========================================================================= */}
      {lightboxImageUrl && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
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
              alt="Evidence Full View"
              className="max-h-[80vh] w-auto mx-auto object-contain rounded"
            />
          </div>
        </div>
      )}
    </div>
  );
};
