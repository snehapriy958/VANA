import React, { useState } from "react";
import {
  Calendar,
  Search,
  Plus,
  Play,
  CheckCircle,
  Camera,
  Star,
  AlertCircle,
  UserCheck,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import type {
  CanopyCondition,
  FieldInspection,
  InspectionAddendumCreate,
  InspectionCancelRequest,
  InspectionCompleteRequest,
  InspectionCreateRequest,
  InspectionEvidence,
  InspectionStatus,
  InspectionType,
  SoilMoistureCondition,
} from "@/types/monitoring";
import type { Project } from "@/types/projects";
import type { UserProfile } from "@/types/auth";

interface InspectionsTabProps {
  inspections: FieldInspection[];
  projects: Project[];
  users: UserProfile[];
  currentUserId?: string;
  currentUserRole?: string;
  selectedProjectId?: string;
  onScheduleInspection: (data: InspectionCreateRequest) => Promise<any>;
  onStartInspection: (id: string) => Promise<any>;
  onCompleteInspection: (id: string, data: InspectionCompleteRequest) => Promise<any>;
  onCancelInspection: (id: string, data: InspectionCancelRequest) => Promise<any>;
  onAddAddendum: (id: string, data: InspectionAddendumCreate) => Promise<any>;
  onUploadEvidence: (id: string, file: File, metadata?: any) => Promise<any>;
  onViewEvidence: (evidence: InspectionEvidence) => void;
}

export const InspectionsTab: React.FC<InspectionsTabProps> = ({
  inspections,
  projects,
  users,
  currentUserId,
  currentUserRole,
  selectedProjectId,
  onScheduleInspection,
  onStartInspection,
  onCompleteInspection,
  onCancelInspection,
  onAddAddendum,
  onUploadEvidence,
  onViewEvidence,
}) => {
  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [typeFilter, setTypeFilter] = useState<string>("ALL");
  const [inspectorFilter, setInspectorFilter] = useState<string>("ALL");

  // Selected for detail view
  const [selectedInspection, setSelectedInspection] = useState<FieldInspection | null>(null);

  // Modals
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false);
  const [isCompleteModalOpen, setIsCompleteModalOpen] = useState(false);
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);
  const [isAddendumModalOpen, setIsAddendumModalOpen] = useState(false);
  const [activeActionInspection, setActiveActionInspection] = useState<FieldInspection | null>(null);

  // Form states: Schedule
  const [scheduleProjectId, setScheduleProjectId] = useState(selectedProjectId || "");
  const [scheduleDate, setScheduleDate] = useState(
    new Date(Date.now() + 86400000).toISOString().split("T")[0]
  );
  const [scheduleType, setScheduleType] = useState<InspectionType>("ROUTINE");
  const [scheduleAssigneeId, setScheduleAssigneeId] = useState("");
  const [scheduleActivityId, setScheduleActivityId] = useState("");
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [isSubmittingSchedule, setIsSubmittingSchedule] = useState(false);

  // Form states: Complete Inspection
  const [findings, setFindings] = useState("");
  const [vegetationHealthScore, setVegetationHealthScore] = useState<number>(4);
  const [canopyCondition, setCanopyCondition] = useState<CanopyCondition>("HEALTHY");
  const [soilMoisture, setSoilMoisture] = useState<SoilMoistureCondition>("ADEQUATE");
  const [threatsList, setThreatsList] = useState<string[]>([]);
  const [threatInput, setThreatInput] = useState("");
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [evidenceCaption, setEvidenceCaption] = useState("");
  const [completeError, setCompleteError] = useState<string | null>(null);
  const [isSubmittingComplete, setIsSubmittingComplete] = useState(false);

  // Form states: Cancel
  const [cancellationReason, setCancellationReason] = useState("");
  const [cancelError, setCancelError] = useState<string | null>(null);

  // Form states: Addendum
  const [addendumContent, setAddendumContent] = useState("");
  const [addendumError, setAddendumError] = useState<string | null>(null);

  const canManage = currentUserRole === "ADMIN" || currentUserRole === "PROJECT_MANAGER";

  // Filter inspections
  const filteredInspections = inspections.filter((insp) => {
    if (statusFilter !== "ALL" && insp.status !== statusFilter) return false;
    if (typeFilter !== "ALL" && insp.inspection_type !== typeFilter) return false;
    if (inspectorFilter !== "ALL" && insp.assigned_to_id !== inspectorFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchFindings = insp.findings?.toLowerCase().includes(q);
      const matchType = insp.inspection_type.toLowerCase().includes(q);
      const matchStatus = insp.status.toLowerCase().includes(q);
      if (!matchFindings && !matchType && !matchStatus) return false;
    }
    return true;
  });

  const getProjectName = (projId: string) => {
    return projects.find((p) => p.id === projId)?.name || "Assigned Project";
  };

  const getUserName = (userId?: string | null) => {
    if (!userId) return "Unassigned";
    const u = users.find((usr) => usr.id === userId);
    return u?.full_name || "Field Officer";
  };

  const handleOpenScheduleModal = () => {
    setScheduleProjectId(selectedProjectId || projects[0]?.id || "");
    setScheduleDate(new Date(Date.now() + 86400000).toISOString().split("T")[0]);
    setScheduleType("ROUTINE");
    setScheduleAssigneeId("");
    setScheduleActivityId("");
    setScheduleError(null);
    setIsScheduleModalOpen(true);
  };

  const handleSubmitSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scheduleProjectId) {
      setScheduleError("Please select a target project.");
      return;
    }
    if (!scheduleDate) {
      setScheduleError("Scheduled date is required.");
      return;
    }

    try {
      setIsSubmittingSchedule(true);
      setScheduleError(null);
      await onScheduleInspection({
        project_id: scheduleProjectId,
        scheduled_date: scheduleDate,
        inspection_type: scheduleType,
        assigned_to_id: scheduleAssigneeId || null,
        linked_activity_id: scheduleActivityId || null,
      });
      setIsScheduleModalOpen(false);
    } catch (err: any) {
      setScheduleError(err?.message || "Failed to schedule inspection.");
    } finally {
      setIsSubmittingSchedule(false);
    }
  };

  const handleOpenCompleteModal = (insp: FieldInspection) => {
    setActiveActionInspection(insp);
    setFindings("");
    setVegetationHealthScore(4);
    setCanopyCondition("HEALTHY");
    setSoilMoisture("ADEQUATE");
    setThreatsList([]);
    setThreatInput("");
    setEvidenceFile(null);
    setEvidenceCaption("");
    setCompleteError(null);
    setIsCompleteModalOpen(true);
  };

  const handleSubmitComplete = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeActionInspection) return;
    if (!findings.trim()) {
      setCompleteError("Findings are mandatory upon inspection completion.");
      return;
    }

    try {
      setIsSubmittingComplete(true);
      setCompleteError(null);

      // 1. Complete inspection
      await onCompleteInspection(activeActionInspection.id, {
        findings: findings.trim(),
        vegetation_health_score: vegetationHealthScore,
        canopy_condition: canopyCondition,
        soil_moisture_condition: soilMoisture,
        threats_detected: threatsList.length > 0 ? threatsList : undefined,
      });

      // 2. Upload evidence if selected
      if (evidenceFile) {
        await onUploadEvidence(activeActionInspection.id, evidenceFile, {
          caption: evidenceCaption.trim() || undefined,
        });
      }

      setIsCompleteModalOpen(false);
      setActiveActionInspection(null);
    } catch (err: any) {
      setCompleteError(err?.message || "Failed to complete inspection.");
    } finally {
      setIsSubmittingComplete(false);
    }
  };

  const handleOpenCancelModal = (insp: FieldInspection) => {
    setActiveActionInspection(insp);
    setCancellationReason("");
    setCancelError(null);
    setIsCancelModalOpen(true);
  };

  const handleSubmitCancel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeActionInspection) return;
    if (cancellationReason.trim().length < 3) {
      setCancelError("Cancellation reason must contain at least 3 characters.");
      return;
    }

    try {
      await onCancelInspection(activeActionInspection.id, {
        cancellation_reason: cancellationReason.trim(),
      });
      setIsCancelModalOpen(false);
      setActiveActionInspection(null);
    } catch (err: any) {
      setCancelError(err?.message || "Failed to cancel inspection.");
    }
  };

  const handleOpenAddendumModal = (insp: FieldInspection) => {
    setActiveActionInspection(insp);
    setAddendumContent("");
    setAddendumError(null);
    setIsAddendumModalOpen(true);
  };

  const handleSubmitAddendum = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeActionInspection) return;
    if (addendumContent.trim().length < 3) {
      setAddendumError("Addendum notes must contain at least 3 characters.");
      return;
    }

    try {
      await onAddAddendum(activeActionInspection.id, {
        content: addendumContent.trim(),
      });
      setIsAddendumModalOpen(false);
      // update selected inspection view if open
      if (selectedInspection?.id === activeActionInspection.id) {
        setSelectedInspection({
          ...selectedInspection,
          addenda: [
            ...(selectedInspection.addenda || []),
            {
              type: "CORRECTION_ADDENDUM",
              author_id: currentUserId || "",
              author_name: "You",
              created_at: new Date().toISOString(),
              content: addendumContent.trim(),
            },
          ],
        });
      }
      setActiveActionInspection(null);
    } catch (err: any) {
      setAddendumError(err?.message || "Failed to add addendum.");
    }
  };

  const getStatusBadge = (status: InspectionStatus) => {
    switch (status) {
      case "COMPLETED":
        return <Badge variant="verified">COMPLETED</Badge>;
      case "IN_PROGRESS":
        return <Badge variant="pending">IN PROGRESS</Badge>;
      case "SCHEDULED":
        return <Badge variant="sage">SCHEDULED</Badge>;
      case "CANCELLED":
        return <Badge variant="rejected">CANCELLED</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Filter and Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-vana-forest/10 shadow-xs">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          <div className="relative w-full sm:w-64">
            <Search className="h-4 w-4 absolute left-3 top-2.5 text-vana-charcoal/40" />
            <Input
              placeholder="Search findings, type..."
              className="pl-9 h-9 text-xs"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 px-3 rounded-md border border-vana-charcoal/20 bg-white text-xs text-vana-charcoal focus:ring-1 focus:ring-vana-forest"
          >
            <option value="ALL">All Statuses</option>
            <option value="SCHEDULED">Scheduled</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="h-9 px-3 rounded-md border border-vana-charcoal/20 bg-white text-xs text-vana-charcoal focus:ring-1 focus:ring-vana-forest"
          >
            <option value="ALL">All Types</option>
            <option value="ROUTINE">Routine</option>
            <option value="SURVIVAL_CHECK">Survival Check</option>
            <option value="MAINTENANCE_AUDIT">Maintenance Audit</option>
            <option value="EMERGENCY">Emergency</option>
          </select>

          {users.length > 0 && (
            <select
              value={inspectorFilter}
              onChange={(e) => setInspectorFilter(e.target.value)}
              className="h-9 px-3 rounded-md border border-vana-charcoal/20 bg-white text-xs text-vana-charcoal focus:ring-1 focus:ring-vana-forest"
            >
              <option value="ALL">All Inspectors</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name} ({u.role})
                </option>
              ))}
            </select>
          )}
        </div>

        {canManage && (
          <Button
            size="sm"
            onClick={handleOpenScheduleModal}
            className="bg-vana-forest text-white gap-1.5 shrink-0"
          >
            <Plus className="h-4 w-4" /> Schedule Inspection
          </Button>
        )}
      </div>

      {/* Inspections Table */}
      <Card className="border border-vana-forest/15 bg-white shadow-subtle overflow-hidden">
        <CardContent className="p-0">
          {filteredInspections.length === 0 ? (
            <div className="text-center py-12 px-4 text-vana-charcoal/60 space-y-2">
              <Calendar className="h-8 w-8 text-vana-forest/30 mx-auto" />
              <p className="text-sm font-semibold font-manrope text-vana-forest">
                No field inspections match the criteria
              </p>
              <p className="text-xs max-w-sm mx-auto">
                {canManage
                  ? "Schedule a routine or survival monitoring inspection to track restoration activities."
                  : "Assigned inspections will display here once scheduled by project management."}
              </p>
              {canManage && (
                <Button
                  size="sm"
                  onClick={handleOpenScheduleModal}
                  className="mt-3 bg-vana-forest text-white text-xs"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" /> Schedule First Inspection
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-vana-forest/5 text-vana-charcoal/80 uppercase text-[10px] font-semibold border-b border-vana-forest/10">
                  <tr>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Project</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Assigned Inspector</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Health / Findings</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-vana-forest/10">
                  {filteredInspections.map((insp) => {
                    const isAssignee = insp.assigned_to_id === currentUserId;
                    const canExecute = isAssignee || canManage;

                    return (
                      <tr
                        key={insp.id}
                        className="hover:bg-vana-forest/5 transition-colors cursor-pointer"
                        onClick={() => setSelectedInspection(insp)}
                      >
                        <td className="py-3 px-4 font-medium text-vana-charcoal whitespace-nowrap">
                          {insp.scheduled_date}
                        </td>
                        <td className="py-3 px-4 font-semibold text-vana-forest">
                          {getProjectName(insp.project_id)}
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-medium text-vana-charcoal/90">
                            {insp.inspection_type.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-vana-charcoal/80 flex items-center gap-1.5">
                          <UserCheck className="h-3.5 w-3.5 text-vana-forest/50" />
                          <span>{getUserName(insp.assigned_to_id)}</span>
                        </td>
                        <td className="py-3 px-4">{getStatusBadge(insp.status)}</td>
                        <td className="py-3 px-4 max-w-xs truncate text-vana-charcoal/70">
                          {insp.vegetation_health_score ? (
                            <span className="flex items-center gap-1 font-semibold text-vana-forest">
                              <Star className="h-3 w-3 fill-vana-gold text-vana-gold" />
                              {insp.vegetation_health_score}/5 • {insp.findings || "Findings recorded"}
                            </span>
                          ) : (
                            <span className="italic text-vana-charcoal/40">Pending execution</span>
                          )}
                        </td>
                        <td
                          className="py-3 px-4 text-right space-x-1 whitespace-nowrap"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {/* Start action */}
                          {insp.status === "SCHEDULED" && canExecute && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs border-vana-forest/30 text-vana-forest hover:bg-vana-forest/10"
                              onClick={() => onStartInspection(insp.id)}
                            >
                              <Play className="h-3 w-3 mr-1" /> Start
                            </Button>
                          )}

                          {/* Complete action */}
                          {insp.status === "IN_PROGRESS" && canExecute && (
                            <Button
                              size="sm"
                              className="h-7 text-xs bg-emerald-800 text-white hover:bg-emerald-700"
                              onClick={() => handleOpenCompleteModal(insp)}
                            >
                              <CheckCircle className="h-3 w-3 mr-1" /> Complete
                            </Button>
                          )}

                          {/* Cancel action */}
                          {(insp.status === "SCHEDULED" || insp.status === "IN_PROGRESS") &&
                            canManage && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 text-xs text-vana-crimson hover:bg-vana-crimson/10"
                                onClick={() => handleOpenCancelModal(insp)}
                              >
                                Cancel
                              </Button>
                            )}

                          {/* Add Addendum on Completed */}
                          {insp.status === "COMPLETED" && canManage && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs border-vana-forest/20 text-vana-forest"
                              onClick={() => handleOpenAddendumModal(insp)}
                            >
                              Addendum
                            </Button>
                          )}

                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 text-xs text-vana-charcoal/70"
                            onClick={() => setSelectedInspection(insp)}
                          >
                            Details
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ===================================================================== */}
      {/* 1. Schedule Inspection Modal */}
      {/* ===================================================================== */}
      <Dialog open={isScheduleModalOpen} onOpenChange={setIsScheduleModalOpen}>
        <DialogContent className="max-w-md bg-white p-6 rounded-xl border border-vana-forest/15">
          <form onSubmit={handleSubmitSchedule} className="space-y-4">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold font-manrope text-vana-forest">
                Schedule Field Inspection
              </DialogTitle>
              <DialogDescription className="text-xs text-vana-charcoal/70">
                Plan routine or emergency post-planting field evaluations.
              </DialogDescription>
            </DialogHeader>

            {scheduleError && (
              <div className="p-3 bg-vana-crimson/10 text-vana-crimson rounded-lg text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{scheduleError}</span>
              </div>
            )}

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-vana-charcoal block mb-1">
                  Target Project *
                </label>
                <select
                  value={scheduleProjectId}
                  onChange={(e) => setScheduleProjectId(e.target.value)}
                  className="w-full h-9 px-3 rounded-md border border-vana-charcoal/20 bg-white"
                  required
                >
                  <option value="">Select Project...</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.code || "VANA"})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="font-semibold text-vana-charcoal block mb-1">
                  Scheduled Date *
                </label>
                <Input
                  type="date"
                  value={scheduleDate}
                  onChange={(e) => setScheduleDate(e.target.value)}
                  className="h-9 text-xs"
                  required
                />
              </div>

              <div>
                <label className="font-semibold text-vana-charcoal block mb-1">
                  Inspection Type *
                </label>
                <select
                  value={scheduleType}
                  onChange={(e) => setScheduleType(e.target.value as InspectionType)}
                  className="w-full h-9 px-3 rounded-md border border-vana-charcoal/20 bg-white"
                >
                  <option value="ROUTINE">Routine Monitoring</option>
                  <option value="SURVIVAL_CHECK">Survival Check</option>
                  <option value="MAINTENANCE_AUDIT">Maintenance Audit</option>
                  <option value="EMERGENCY">Emergency Assessment</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-vana-charcoal block mb-1">
                  Assign Inspector (Field Officer)
                </label>
                <select
                  value={scheduleAssigneeId}
                  onChange={(e) => setScheduleAssigneeId(e.target.value)}
                  className="w-full h-9 px-3 rounded-md border border-vana-charcoal/20 bg-white"
                >
                  <option value="">Unassigned (Any assigned officer)</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.role})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsScheduleModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isSubmittingSchedule}
                className="bg-vana-forest text-white"
              >
                {isSubmittingSchedule ? "Scheduling..." : "Schedule Inspection"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ===================================================================== */}
      {/* 2. Execute & Complete Inspection Modal */}
      {/* ===================================================================== */}
      <Dialog open={isCompleteModalOpen} onOpenChange={setIsCompleteModalOpen}>
        <DialogContent className="max-w-lg bg-white p-6 rounded-xl border border-vana-forest/15 max-h-[90vh] overflow-y-auto">
          <form onSubmit={handleSubmitComplete} className="space-y-4">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold font-manrope text-vana-forest">
                Complete Field Inspection
              </DialogTitle>
              <DialogDescription className="text-xs text-vana-charcoal/70">
                Record mandatory field findings, health scores, and supporting photo evidence.
              </DialogDescription>
            </DialogHeader>

            {completeError && (
              <div className="p-3 bg-vana-crimson/10 text-vana-crimson rounded-lg text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{completeError}</span>
              </div>
            )}

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-vana-charcoal block mb-1">
                  Field Findings &amp; Observations *
                </label>
                <textarea
                  value={findings}
                  onChange={(e) => setFindings(e.target.value)}
                  rows={3}
                  className="w-full p-2.5 rounded-md border border-vana-charcoal/20 text-xs focus:ring-1 focus:ring-vana-forest"
                  placeholder="Describe seedling vigor, root stability, irrigation sufficiency, or pest pressures..."
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-vana-charcoal block mb-1">
                    Vegetation Health (1 to 5)
                  </label>
                  <div className="flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map((score) => (
                      <button
                        key={score}
                        type="button"
                        onClick={() => setVegetationHealthScore(score)}
                        className={`p-1.5 rounded border transition-colors ${
                          vegetationHealthScore >= score
                            ? "bg-vana-gold text-white border-vana-gold"
                            : "bg-white text-vana-charcoal/40 border-vana-charcoal/20"
                        }`}
                      >
                        <Star className="h-4 w-4 fill-current" />
                      </button>
                    ))}
                    <span className="ml-2 font-bold text-vana-forest">
                      {vegetationHealthScore}/5
                    </span>
                  </div>
                </div>

                <div>
                  <label className="font-semibold text-vana-charcoal block mb-1">
                    Canopy Condition
                  </label>
                  <select
                    value={canopyCondition}
                    onChange={(e) => setCanopyCondition(e.target.value as CanopyCondition)}
                    className="w-full h-9 px-2.5 rounded-md border border-vana-charcoal/20 bg-white"
                  >
                    <option value="EXCELLENT">Excellent</option>
                    <option value="HEALTHY">Healthy</option>
                    <option value="STRESSED">Stressed</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="font-semibold text-vana-charcoal block mb-1">
                  Soil Moisture Condition
                </label>
                <select
                  value={soilMoisture}
                  onChange={(e) => setSoilMoisture(e.target.value as SoilMoistureCondition)}
                  className="w-full h-9 px-2.5 rounded-md border border-vana-charcoal/20 bg-white"
                >
                  <option value="ADEQUATE">Adequate</option>
                  <option value="SATURATED">Saturated / Flooded</option>
                  <option value="DRY">Dry</option>
                  <option value="SEVERELY_PARCHED">Severely Parched</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-vana-charcoal block mb-1">
                  Threats Detected (Optional)
                </label>
                <div className="flex gap-2">
                  <Input
                    placeholder="e.g. Stray Cattle, Weed Infestation..."
                    value={threatInput}
                    onChange={(e) => setThreatInput(e.target.value)}
                    className="h-8 text-xs"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        if (threatInput.trim() && !threatsList.includes(threatInput.trim())) {
                          setThreatsList([...threatsList, threatInput.trim()]);
                          setThreatInput("");
                        }
                      }
                    }}
                  />
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-8 text-xs"
                    onClick={() => {
                      if (threatInput.trim() && !threatsList.includes(threatInput.trim())) {
                        setThreatsList([...threatsList, threatInput.trim()]);
                        setThreatInput("");
                      }
                    }}
                  >
                    Add
                  </Button>
                </div>
                {threatsList.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {threatsList.map((t, idx) => (
                      <Badge
                        key={idx}
                        variant="rejected"
                        className="text-[10px] px-2 py-0.5 flex items-center gap-1 cursor-pointer"
                        onClick={() => setThreatsList(threatsList.filter((_, i) => i !== idx))}
                      >
                        {t} ✕
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              {/* Photo Evidence Upload Attachment */}
              <div className="p-3 bg-vana-forest/5 rounded-lg border border-dashed border-vana-forest/20 space-y-2">
                <label className="font-semibold text-vana-forest flex items-center gap-1.5">
                  <Camera className="h-4 w-4" /> Attach Photo Evidence (Optional)
                </label>
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  onChange={(e) => setEvidenceFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-vana-charcoal"
                />
                {evidenceFile && (
                  <Input
                    placeholder="Evidence caption (e.g. Transect A canopy photo)"
                    value={evidenceCaption}
                    onChange={(e) => setEvidenceCaption(e.target.value)}
                    className="h-8 text-xs bg-white"
                  />
                )}
              </div>
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsCompleteModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isSubmittingComplete}
                className="bg-emerald-800 text-white hover:bg-emerald-700"
              >
                {isSubmittingComplete ? "Completing..." : "Complete & Lock Inspection"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ===================================================================== */}
      {/* 3. Cancel Inspection Dialog */}
      {/* ===================================================================== */}
      <Dialog open={isCancelModalOpen} onOpenChange={setIsCancelModalOpen}>
        <DialogContent className="max-w-md bg-white p-6 rounded-xl border border-vana-crimson/25">
          <form onSubmit={handleSubmitCancel} className="space-y-4">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold font-manrope text-vana-crimson">
                Cancel Inspection
              </DialogTitle>
              <DialogDescription className="text-xs text-vana-charcoal/70">
                Provide an audit-logged reason for cancelling this field inspection.
              </DialogDescription>
            </DialogHeader>

            {cancelError && (
              <div className="p-3 bg-vana-crimson/10 text-vana-crimson rounded-lg text-xs">
                {cancelError}
              </div>
            )}

            <div>
              <label className="font-semibold text-vana-charcoal text-xs block mb-1">
                Cancellation Reason *
              </label>
              <textarea
                value={cancellationReason}
                onChange={(e) => setCancellationReason(e.target.value)}
                rows={3}
                placeholder="e.g. Inaccessible terrain due to cyclone; rescheduled for next month..."
                className="w-full p-2.5 rounded-md border border-vana-charcoal/20 text-xs"
                required
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsCancelModalOpen(false)}
              >
                Back
              </Button>
              <Button type="submit" size="sm" variant="destructive">
                Confirm Cancellation
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ===================================================================== */}
      {/* 4. Post-Completion Addendum Dialog */}
      {/* ===================================================================== */}
      <Dialog open={isAddendumModalOpen} onOpenChange={setIsAddendumModalOpen}>
        <DialogContent className="max-w-md bg-white p-6 rounded-xl border border-vana-forest/15">
          <form onSubmit={handleSubmitAddendum} className="space-y-4">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold font-manrope text-vana-forest">
                Record Post-Completion Addendum
              </DialogTitle>
              <DialogDescription className="text-xs text-vana-charcoal/70">
                Completed inspections are locked from direct editing. Record an immutable addendum to add context or corrections.
              </DialogDescription>
            </DialogHeader>

            {addendumError && (
              <div className="p-3 bg-vana-crimson/10 text-vana-crimson rounded-lg text-xs">
                {addendumError}
              </div>
            )}

            <div>
              <label className="font-semibold text-vana-charcoal text-xs block mb-1">
                Addendum Content *
              </label>
              <textarea
                value={addendumContent}
                onChange={(e) => setAddendumContent(e.target.value)}
                rows={4}
                placeholder="e.g. Laboratory soil salinity analysis received: 1.2 dS/m (normal range)."
                className="w-full p-2.5 rounded-md border border-vana-charcoal/20 text-xs"
                required
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsAddendumModalOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" className="bg-vana-forest text-white">
                Save Immutable Addendum
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ===================================================================== */}
      {/* 5. Detailed Inspection Inspector Modal / Drawer */}
      {/* ===================================================================== */}
      {selectedInspection && (
        <Dialog open={!!selectedInspection} onOpenChange={() => setSelectedInspection(null)}>
          <DialogContent className="max-w-2xl bg-white p-6 rounded-xl border border-vana-forest/15 max-h-[85vh] overflow-y-auto">
            <DialogHeader className="border-b border-vana-forest/10 pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <DialogTitle className="text-lg font-bold font-manrope text-vana-forest">
                    {selectedInspection.inspection_type.replace(/_/g, " ")} Details
                  </DialogTitle>
                  <DialogDescription className="text-xs text-vana-charcoal/70">
                    Project: {getProjectName(selectedInspection.project_id)} • Scheduled:{" "}
                    {selectedInspection.scheduled_date}
                  </DialogDescription>
                </div>
                {getStatusBadge(selectedInspection.status)}
              </div>
            </DialogHeader>

            <div className="space-y-4 text-xs py-2">
              {/* Status & Personnel info */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 bg-vana-ivory/40 p-3 rounded-lg border border-vana-forest/10">
                <div>
                  <span className="text-[10px] uppercase font-semibold text-vana-charcoal/60 block">
                    Assigned Inspector
                  </span>
                  <span className="font-medium text-vana-forest">
                    {getUserName(selectedInspection.assigned_to_id)}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-semibold text-vana-charcoal/60 block">
                    Completed At
                  </span>
                  <span className="font-medium text-vana-charcoal">
                    {selectedInspection.completed_at
                      ? new Date(selectedInspection.completed_at).toLocaleString()
                      : "Not completed"}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-semibold text-vana-charcoal/60 block">
                    Vegetation Health
                  </span>
                  <span className="font-semibold text-vana-gold">
                    {selectedInspection.vegetation_health_score
                      ? `${selectedInspection.vegetation_health_score}/5`
                      : "N/A"}
                  </span>
                </div>
              </div>

              {/* Conditions */}
              {(selectedInspection.canopy_condition ||
                selectedInspection.soil_moisture_condition) && (
                <div className="flex items-center gap-3">
                  {selectedInspection.canopy_condition && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-vana-charcoal/60">Canopy:</span>
                      <Badge variant="sage" className="text-[10px]">
                        {selectedInspection.canopy_condition}
                      </Badge>
                    </div>
                  )}
                  {selectedInspection.soil_moisture_condition && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-vana-charcoal/60">Soil Moisture:</span>
                      <Badge variant="neutral" className="text-[10px]">
                        {selectedInspection.soil_moisture_condition}
                      </Badge>
                    </div>
                  )}
                </div>
              )}

              {/* Threats */}
              {selectedInspection.threats_detected &&
                selectedInspection.threats_detected.length > 0 && (
                  <div>
                    <span className="font-semibold text-vana-crimson block mb-1">
                      Threats Detected:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedInspection.threats_detected.map((t, idx) => (
                        <Badge key={idx} variant="rejected" className="text-[10px]">
                          {t}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

              {/* Findings */}
              <div>
                <span className="font-semibold text-vana-forest uppercase tracking-wider text-[10px] block mb-1">
                  Findings &amp; Field Notes
                </span>
                <div className="p-3 bg-white rounded-lg border border-vana-forest/10 text-vana-charcoal whitespace-pre-wrap leading-relaxed">
                  {selectedInspection.findings || (
                    <span className="italic text-vana-charcoal/50">
                      No findings recorded yet.
                    </span>
                  )}
                </div>
              </div>

              {/* Addenda Log */}
              {selectedInspection.addenda && selectedInspection.addenda.length > 0 && (
                <div>
                  <span className="font-semibold text-vana-forest uppercase tracking-wider text-[10px] block mb-1">
                    Immutable Addenda Log ({selectedInspection.addenda.length})
                  </span>
                  <div className="space-y-2">
                    {selectedInspection.addenda.map((add, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-lg border border-vana-forest/15 bg-vana-forest/5 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between text-[10px] text-vana-charcoal/60">
                          <span className="font-semibold text-vana-forest">
                            {add.author_name || "Project Officer"}
                          </span>
                          <span>{new Date(add.created_at).toLocaleString()}</span>
                        </div>
                        <p className="text-vana-charcoal">{add.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {/* Evidence Section */}
              <div className="pt-2 border-t border-vana-forest/10">
                <span className="font-semibold text-vana-forest uppercase tracking-wider text-[10px] block mb-2">
                  Photo &amp; Document Evidence
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  className="text-xs border-vana-forest/20 text-vana-forest gap-1.5"
                  onClick={() => {
                    onViewEvidence({
                      id: selectedInspection.id,
                      inspection_id: selectedInspection.id,
                      original_filename: `inspection_${selectedInspection.scheduled_date}_evidence.jpg`,
                      mime_type: "image/jpeg",
                      file_size_bytes: 524288,
                      download_url: `/api/v1/operations/evidence/${selectedInspection.id}`,
                      caption: selectedInspection.findings || "Field inspection evidence",
                      uploaded_at: selectedInspection.updated_at,
                    });
                  }}
                >
                  <Camera className="h-3.5 w-3.5" /> View Attached Media
                </Button>
              </div>
            </div>

            <DialogFooter className="border-t border-vana-forest/10 pt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedInspection(null)}
              >
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};
