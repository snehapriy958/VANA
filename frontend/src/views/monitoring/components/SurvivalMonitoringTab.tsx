import React, { useState } from "react";
import {
  HeartPulse,
  Plus,
  RotateCcw,
  TrendingUp,
  AlertCircle,
  Info,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
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
  SurvivalAnalytics,
  SurvivalMethodology,
  SurvivalObservation,
  SurvivalObservationCorrectionRequest,
  SurvivalObservationCreateRequest,
} from "@/types/monitoring";
import type { Project } from "@/types/projects";

interface SurvivalMonitoringTabProps {
  observations: SurvivalObservation[];
  analytics: SurvivalAnalytics[];
  projects: Project[];
  selectedProjectId: string;
  selectedPlot: string;
  selectedCohort: string;
  onSelectPlot: (plot: string) => void;
  onSelectCohort: (cohort: string) => void;
  currentUserRole?: string;
  onCreateObservation: (data: SurvivalObservationCreateRequest) => Promise<any>;
  onCorrectObservation: (id: string, data: SurvivalObservationCorrectionRequest) => Promise<any>;
}

export const SurvivalMonitoringTab: React.FC<SurvivalMonitoringTabProps> = ({
  observations,
  analytics,
  projects,
  selectedProjectId,
  selectedPlot,
  selectedCohort,
  onSelectPlot,
  onSelectCohort,
  currentUserRole,
  onCreateObservation,
  onCorrectObservation,
}) => {
  const [activeOnly, setActiveOnly] = useState(false);

  // Modals
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false);
  const [isCorrectModalOpen, setIsCorrectModalOpen] = useState(false);
  const [targetObsForCorrection, setTargetObsForCorrection] = useState<SurvivalObservation | null>(
    null
  );

  // Form: Record Observation
  const [formProjectId, setFormProjectId] = useState(selectedProjectId || projects[0]?.id || "");
  const [plotId, setPlotId] = useState(selectedPlot || "");
  const [cohortId, setCohortId] = useState(selectedCohort || "");
  const [methodology, setMethodology] = useState<SurvivalMethodology>("SAMPLE_PLOT");
  const [coverageArea, setCoverageArea] = useState<string>("");
  const [obsDate, setObsDate] = useState(new Date().toISOString().split("T")[0]);
  const [sampleSize, setSampleSize] = useState<string>("100");
  const [aliveCount, setAliveCount] = useState<string>("85");
  const [deadCount, setDeadCount] = useState<string>("10");
  const [mortalityCauseInput, setMortalityCauseInput] = useState("");
  const [mortalityCauses, setMortalityCauses] = useState<string[]>([]);
  const [isDefinitive, setIsDefinitive] = useState(false);
  const [notes, setNotes] = useState("");
  const [recordError, setRecordError] = useState<string | null>(null);
  const [isSubmittingRecord, setIsSubmittingRecord] = useState(false);

  // Form: Correction / Supersession
  const [corrSampleSize, setCorrSampleSize] = useState<string>("");
  const [corrAliveCount, setCorrAliveCount] = useState<string>("");
  const [corrDeadCount, setCorrDeadCount] = useState<string>("");
  const [corrNotes, setCorrNotes] = useState("");
  const [correctionReason, setCorrectionReason] = useState("");
  const [corrError, setCorrError] = useState<string | null>(null);
  const [isSubmittingCorr, setIsSubmittingCorr] = useState(false);

  const canManage = currentUserRole === "ADMIN" || currentUserRole === "PROJECT_MANAGER";

  // Derive client preview values for form
  const numSampleSize = Math.max(0, parseInt(sampleSize, 10) || 0);
  const numAlive = Math.max(0, parseInt(aliveCount, 10) || 0);
  const numDead = Math.max(0, parseInt(deadCount, 10) || 0);
  const numAssessed = numAlive + numDead;
  const numUnassessed = Math.max(0, numSampleSize - numAssessed);
  const previewSurvivalRate =
    numAssessed > 0 ? ((numAlive / numAssessed) * 100).toFixed(1) : null;
  const isOverSample = numAssessed > numSampleSize;

  // Derive correction preview values
  const corrNumSample = Math.max(0, parseInt(corrSampleSize, 10) || 0);
  const corrNumAlive = Math.max(0, parseInt(corrAliveCount, 10) || 0);
  const corrNumDead = Math.max(0, parseInt(corrDeadCount, 10) || 0);
  const corrNumAssessed = corrNumAlive + corrNumDead;
  const corrPreviewRate =
    corrNumAssessed > 0 ? ((corrNumAlive / corrNumAssessed) * 100).toFixed(1) : null;

  // Extract distinct plots and cohorts for quick filtering
  const distinctPlots = Array.from(new Set(observations.map((o) => o.plot_identifier))).filter(
    Boolean
  );
  const distinctCohorts = Array.from(new Set(observations.map((o) => o.cohort_identifier))).filter(
    Boolean
  );

  // Filter observations table
  const filteredObservations = observations.filter((obs) => {
    if (activeOnly && !obs.is_active) return false;
    if (selectedPlot && obs.plot_identifier !== selectedPlot) return false;
    if (selectedCohort && obs.cohort_identifier !== selectedCohort) return false;
    return true;
  });

  const handleOpenRecordModal = () => {
    setFormProjectId(selectedProjectId || projects[0]?.id || "");
    setPlotId(selectedPlot || "");
    setCohortId(selectedCohort || "");
    setMethodology("SAMPLE_PLOT");
    setCoverageArea("");
    setObsDate(new Date().toISOString().split("T")[0]);
    setSampleSize("100");
    setAliveCount("85");
    setDeadCount("10");
    setMortalityCauses([]);
    setMortalityCauseInput("");
    setIsDefinitive(false);
    setNotes("");
    setRecordError(null);
    setIsRecordModalOpen(true);
  };

  const handleSubmitRecord = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formProjectId) {
      setRecordError("Please select a target project.");
      return;
    }
    if (!plotId.trim() || !cohortId.trim()) {
      setRecordError("Plot identifier and Cohort identifier are required.");
      return;
    }
    if (numSampleSize <= 0) {
      setRecordError("Sample size must be greater than 0.");
      return;
    }
    if (isOverSample) {
      setRecordError(
        `Sum of alive count (${numAlive}) and dead count (${numDead}) cannot exceed sample size (${numSampleSize}).`
      );
      return;
    }

    try {
      setIsSubmittingRecord(true);
      setRecordError(null);
      await onCreateObservation({
        project_id: formProjectId,
        plot_identifier: plotId.trim(),
        cohort_identifier: cohortId.trim(),
        methodology,
        coverage_area_sqm: coverageArea ? parseFloat(coverageArea) : undefined,
        observation_date: obsDate,
        sample_size: numSampleSize,
        alive_count: numAlive,
        dead_count: numDead,
        mortality_causes: mortalityCauses.length > 0 ? mortalityCauses : undefined,
        is_definitive: isDefinitive,
        notes: notes.trim() || undefined,
      });

      // Update active selection to match new observation
      onSelectPlot(plotId.trim());
      onSelectCohort(cohortId.trim());
      setIsRecordModalOpen(false);
    } catch (err: any) {
      setRecordError(err?.message || "Failed to record survival observation.");
    } finally {
      setIsSubmittingRecord(false);
    }
  };

  const handleOpenCorrectModal = (obs: SurvivalObservation) => {
    setTargetObsForCorrection(obs);
    setCorrSampleSize(String(obs.sample_size));
    setCorrAliveCount(String(obs.alive_count));
    setCorrDeadCount(String(obs.dead_count));
    setCorrNotes(obs.notes || "");
    setCorrectionReason("");
    setCorrError(null);
    setIsCorrectModalOpen(true);
  };

  const handleSubmitCorrect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetObsForCorrection) return;
    if (corrNumSample <= 0) {
      setCorrError("Sample size must be greater than 0.");
      return;
    }
    if (corrNumAssessed > corrNumSample) {
      setCorrError(
        `Sum of alive count (${corrNumAlive}) and dead count (${corrNumDead}) cannot exceed sample size (${corrNumSample}).`
      );
      return;
    }
    if (correctionReason.trim().length < 3) {
      setCorrError("Correction reason notes must contain at least 3 characters.");
      return;
    }

    try {
      setIsSubmittingCorr(true);
      setCorrError(null);
      await onCorrectObservation(targetObsForCorrection.id, {
        sample_size: corrNumSample,
        alive_count: corrNumAlive,
        dead_count: corrNumDead,
        notes: corrNotes.trim() || undefined,
        correction_notes: correctionReason.trim(),
      });
      setIsCorrectModalOpen(false);
      setTargetObsForCorrection(null);
    } catch (err: any) {
      setCorrError(err?.message || "Failed to correct observation.");
    } finally {
      setIsSubmittingCorr(false);
    }
  };

  // Recharts data transformation for longitudinal trajectory curve
  const chartData = analytics.map((pt) => ({
    date: pt.observation_date,
    survivalRate: pt.survival_rate !== null ? Number(pt.survival_rate.toFixed(1)) : 0,
    alive: pt.alive_count,
    dead: pt.dead_count,
    sampleSize: pt.sample_size,
    assessed: pt.assessed_count,
    unassessed: pt.unassessed_count,
  }));

  return (
    <div className="space-y-6">
      {/* Top Filter and Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-vana-forest/10 shadow-xs">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          {/* Plot Filter */}
          <select
            value={selectedPlot}
            onChange={(e) => onSelectPlot(e.target.value)}
            className="h-9 px-3 rounded-md border border-vana-charcoal/20 bg-white text-xs text-vana-charcoal font-medium"
          >
            <option value="">All Plot Identifiers</option>
            {distinctPlots.map((p) => (
              <option key={p} value={p}>
                Plot: {p}
              </option>
            ))}
          </select>

          {/* Cohort Filter */}
          <select
            value={selectedCohort}
            onChange={(e) => onSelectCohort(e.target.value)}
            className="h-9 px-3 rounded-md border border-vana-charcoal/20 bg-white text-xs text-vana-charcoal font-medium"
          >
            <option value="">All Cohorts</option>
            {distinctCohorts.map((c) => (
              <option key={c} value={c}>
                Cohort: {c}
              </option>
            ))}
          </select>

          {/* Active Only Toggle */}
          <button
            type="button"
            onClick={() => setActiveOnly(!activeOnly)}
            className={`h-9 px-3 rounded-md border text-xs font-medium transition-colors ${
              activeOnly
                ? "bg-vana-forest text-white border-vana-forest shadow-xs"
                : "bg-white text-vana-charcoal/70 border-vana-charcoal/20 hover:bg-vana-forest/5"
            }`}
          >
            {activeOnly ? "Active Only (Filter ON)" : "Show All (Including Superseded)"}
          </button>
        </div>

        <Button
          size="sm"
          onClick={handleOpenRecordModal}
          className="bg-vana-forest text-white gap-1.5 shrink-0"
        >
          <Plus className="h-4 w-4" /> Record Survival Observation
        </Button>
      </div>

      {/* Recharts Longitudinal Survival Trajectory Curve */}
      <Card className="border border-vana-forest/15 bg-white shadow-subtle">
        <CardHeader className="pb-3 border-b border-vana-forest/10">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <CardTitle className="text-base font-bold font-manrope text-vana-forest flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-emerald-800" /> Longitudinal Survival Trajectory
              </CardTitle>
              <CardDescription className="text-xs text-vana-charcoal/60">
                {selectedPlot && selectedCohort
                  ? `Active trajectory for Plot "${selectedPlot}" and Cohort "${selectedCohort}"`
                  : "Select a specific plot and cohort above to display the longitudinal survival trajectory curve."}
              </CardDescription>
            </div>

            <div className="text-[11px] text-vana-charcoal/60 bg-vana-forest/5 px-2.5 py-1 rounded border border-vana-forest/10 flex items-center gap-1.5 self-start sm:self-auto">
              <Info className="h-3.5 w-3.5 text-vana-forest" />
              <span>Observed sample survival rate only (no extrapolation applied).</span>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {!selectedPlot || !selectedCohort ? (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 bg-vana-forest/5 rounded-xl border border-dashed border-vana-forest/20">
              <HeartPulse className="h-8 w-8 text-vana-forest/30 mb-2" />
              <p className="text-sm font-semibold font-manrope text-vana-forest">
                Select a Plot and Cohort to View Trajectory
              </p>
              <p className="text-xs text-vana-charcoal/60 mt-1 max-w-sm">
                Survival curves track the health progression of specific planting cohorts over time.
              </p>
            </div>
          ) : chartData.length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 bg-vana-forest/5 rounded-xl border border-dashed border-vana-forest/20">
              <p className="text-sm font-semibold font-manrope text-vana-forest">
                Insufficient Longitudinal History
              </p>
              <p className="text-xs text-vana-charcoal/60 mt-1 max-w-sm">
                No active observations found for Plot "{selectedPlot}" and Cohort "{selectedCohort}".
                Record at least one field observation to begin tracking.
              </p>
            </div>
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 20, right: 30, left: 10, bottom: 25 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#183D32" strokeOpacity={0.08} />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "#29332F", fontSize: 11 }}
                    padding={{ left: 20, right: 20 }}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fill: "#29332F", fontSize: 11 }}
                    unit="%"
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#FFFFFF",
                      borderRadius: "8px",
                      border: "1px solid rgba(24, 61, 50, 0.15)",
                      boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                      fontSize: "12px",
                    }}
                    formatter={(val: any, name: any) => {
                      if (name === "Observed Survival Rate") {
                        return [`${val}%`, name];
                      }
                      return [val, name];
                    }}
                    labelFormatter={(label, payload) => {
                      const pt = payload?.[0]?.payload;
                      if (!pt) return label;
                      return `${label} • Sample Size: ${pt.sampleSize} (Alive: ${pt.alive}, Dead: ${pt.dead})`;
                    }}
                  />
                  <Legend verticalAlign="top" wrapperStyle={{ paddingBottom: 15, fontSize: 12 }} />
                  <Line
                    type="monotone"
                    dataKey="survivalRate"
                    name="Observed Survival Rate"
                    stroke="#183D32"
                    strokeWidth={2.5}
                    dot={{ r: 5, fill: "#183D32", stroke: "#FFFFFF", strokeWidth: 2 }}
                    activeDot={{ r: 7 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Survival Observations History Table */}
      <Card className="border border-vana-forest/15 bg-white shadow-subtle overflow-hidden">
        <CardHeader className="py-3 px-4 border-b border-vana-forest/10 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-sm font-bold font-manrope text-vana-forest">
              Field Survival Observations ({filteredObservations.length})
            </CardTitle>
            <CardDescription className="text-xs text-vana-charcoal/60">
              Historical sample audits with immutable correction lineages
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {filteredObservations.length === 0 ? (
            <div className="text-center py-12 px-4 text-vana-charcoal/60 space-y-2">
              <HeartPulse className="h-8 w-8 text-emerald-800/30 mx-auto" />
              <p className="text-sm font-semibold font-manrope text-vana-forest">
                No survival observations match criteria
              </p>
              <p className="text-xs max-w-sm mx-auto">
                Record a sample plot or full census observation to establish survival tracking.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-vana-forest/5 text-vana-charcoal/80 uppercase text-[10px] font-semibold border-b border-vana-forest/10">
                  <tr>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Plot Identifier</th>
                    <th className="py-3 px-4">Cohort</th>
                    <th className="py-3 px-4">Methodology</th>
                    <th className="py-3 px-4 text-right">Sample</th>
                    <th className="py-3 px-4 text-right">Alive</th>
                    <th className="py-3 px-4 text-right">Dead</th>
                    <th className="py-3 px-4 text-right">Unassessed</th>
                    <th className="py-3 px-4 text-right">Derived Survival</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-vana-forest/10">
                  {filteredObservations.map((obs) => (
                    <tr
                      key={obs.id}
                      className={`hover:bg-vana-forest/5 transition-colors ${
                        !obs.is_active ? "bg-vana-charcoal/5 opacity-70" : ""
                      }`}
                    >
                      <td className="py-3 px-4 font-medium text-vana-charcoal whitespace-nowrap">
                        {obs.observation_date}
                      </td>
                      <td className="py-3 px-4 font-semibold text-vana-forest">
                        {obs.plot_identifier}
                      </td>
                      <td className="py-3 px-4 text-vana-charcoal/80 font-medium">
                        {obs.cohort_identifier}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="sage" className="text-[10px] px-2 py-0">
                          {obs.methodology.replace(/_/g, " ")}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-right font-mono font-medium">
                        {obs.sample_size}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-emerald-800 font-bold">
                        {obs.alive_count}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-vana-crimson font-medium">
                        {obs.dead_count}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-vana-charcoal/60">
                        {obs.unassessed_count}
                      </td>
                      <td className="py-3 px-4 text-right font-mono font-bold">
                        {obs.survival_rate !== null ? (
                          <span
                            className={
                              obs.survival_rate >= 80
                                ? "text-emerald-800 font-bold"
                                : obs.survival_rate >= 50
                                ? "text-[#8C6228] font-bold"
                                : "text-vana-crimson font-bold"
                            }
                          >
                            {obs.survival_rate.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-vana-charcoal/40 italic">N/A</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {obs.is_active ? (
                          <Badge variant="verified" className="text-[10px]">
                            ACTIVE
                          </Badge>
                        ) : (
                          <Badge variant="neutral" className="text-[10px] italic">
                            SUPERSEDED
                          </Badge>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {obs.is_active && canManage ? (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs border-vana-gold/40 text-[#8C6228] hover:bg-vana-gold/10"
                            onClick={() => handleOpenCorrectModal(obs)}
                          >
                            <RotateCcw className="h-3 w-3 mr-1" /> Correct
                          </Button>
                        ) : (
                          !obs.is_active && (
                            <span className="text-[10px] text-vana-charcoal/50 italic">
                              Archived
                            </span>
                          )
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

      {/* ===================================================================== */}
      {/* 1. Record Survival Observation Modal */}
      {/* ===================================================================== */}
      <Dialog open={isRecordModalOpen} onOpenChange={setIsRecordModalOpen}>
        <DialogContent className="max-w-lg bg-white p-6 rounded-xl border border-vana-forest/15 max-h-[90vh] overflow-y-auto">
          <form onSubmit={handleSubmitRecord} className="space-y-4">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold font-manrope text-vana-forest">
                Record Field Survival Observation
              </DialogTitle>
              <DialogDescription className="text-xs text-vana-charcoal/70">
                Submit sample-based field counts. The observed sample survival rate is calculated by the server.
              </DialogDescription>
            </DialogHeader>

            {recordError && (
              <div className="p-3 bg-vana-crimson/10 text-vana-crimson rounded-lg text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{recordError}</span>
              </div>
            )}

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-vana-charcoal block mb-1">
                  Target Project *
                </label>
                <select
                  value={formProjectId}
                  onChange={(e) => setFormProjectId(e.target.value)}
                  className="w-full h-9 px-3 rounded-md border border-vana-charcoal/20 bg-white"
                  required
                >
                  <option value="">Select Project...</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-vana-charcoal block mb-1">
                    Plot Identifier *
                  </label>
                  <Input
                    placeholder="e.g. PLOT-NORTH-01"
                    value={plotId}
                    onChange={(e) => setPlotId(e.target.value)}
                    className="h-9 text-xs"
                    required
                  />
                </div>

                <div>
                  <label className="font-semibold text-vana-charcoal block mb-1">
                    Cohort Identifier *
                  </label>
                  <Input
                    placeholder="e.g. COHORT-2026-Q4"
                    value={cohortId}
                    onChange={(e) => setCohortId(e.target.value)}
                    className="h-9 text-xs"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-vana-charcoal block mb-1">
                    Methodology *
                  </label>
                  <select
                    value={methodology}
                    onChange={(e) => setMethodology(e.target.value as SurvivalMethodology)}
                    className="w-full h-9 px-2.5 rounded-md border border-vana-charcoal/20 bg-white"
                  >
                    <option value="SAMPLE_PLOT">Sample Plot</option>
                    <option value="TRANSECT">Transect</option>
                    <option value="FULL_CENSUS">Full Population Census</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-vana-charcoal block mb-1">
                    Observation Date *
                  </label>
                  <Input
                    type="date"
                    value={obsDate}
                    onChange={(e) => setObsDate(e.target.value)}
                    className="h-9 text-xs"
                    required
                  />
                </div>
              </div>

              {/* Counts Grid */}
              <div className="grid grid-cols-3 gap-3 p-3 bg-vana-ivory/50 rounded-lg border border-vana-forest/10">
                <div>
                  <label className="font-semibold text-vana-charcoal block mb-1">
                    Sample Size *
                  </label>
                  <Input
                    type="number"
                    min="1"
                    value={sampleSize}
                    onChange={(e) => setSampleSize(e.target.value)}
                    className="h-9 text-xs font-mono font-semibold"
                    required
                  />
                </div>

                <div>
                  <label className="font-semibold text-emerald-800 block mb-1">
                    Alive Count *
                  </label>
                  <Input
                    type="number"
                    min="0"
                    value={aliveCount}
                    onChange={(e) => setAliveCount(e.target.value)}
                    className="h-9 text-xs font-mono font-bold text-emerald-800"
                    required
                  />
                </div>

                <div>
                  <label className="font-semibold text-vana-crimson block mb-1">
                    Dead Count *
                  </label>
                  <Input
                    type="number"
                    min="0"
                    value={deadCount}
                    onChange={(e) => setDeadCount(e.target.value)}
                    className="h-9 text-xs font-mono font-semibold text-vana-crimson"
                    required
                  />
                </div>
              </div>

              {/* Dynamic Live Calculations Preview */}
              <div
                className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
                  isOverSample
                    ? "bg-vana-crimson/10 border-vana-crimson text-vana-crimson"
                    : "bg-emerald-50 border-emerald-600/30 text-emerald-900"
                }`}
              >
                <div>
                  <span className="font-semibold block">
                    {isOverSample ? "Invalid Count Sum!" : "Derived Sample Calculations Preview:"}
                  </span>
                  <span className="text-[11px] opacity-80">
                    Assessed: {numAssessed} • Unassessed: {numUnassessed} of {numSampleSize} sample
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] uppercase tracking-wide block">
                    Observed Survival
                  </span>
                  <span className="text-base font-bold font-mono">
                    {isOverSample ? "ERROR" : previewSurvivalRate ? `${previewSurvivalRate}%` : "N/A"}
                  </span>
                </div>
              </div>

              <div>
                <label className="font-semibold text-vana-charcoal block mb-1">
                  Mortality Causes (Optional)
                </label>
                <div className="flex gap-2">
                  <Input
                    placeholder="e.g. Drought, Herbivory, Salinity..."
                    value={mortalityCauseInput}
                    onChange={(e) => setMortalityCauseInput(e.target.value)}
                    className="h-8 text-xs"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        if (
                          mortalityCauseInput.trim() &&
                          !mortalityCauses.includes(mortalityCauseInput.trim())
                        ) {
                          setMortalityCauses([...mortalityCauses, mortalityCauseInput.trim()]);
                          setMortalityCauseInput("");
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
                      if (
                        mortalityCauseInput.trim() &&
                        !mortalityCauses.includes(mortalityCauseInput.trim())
                      ) {
                        setMortalityCauses([...mortalityCauses, mortalityCauseInput.trim()]);
                        setMortalityCauseInput("");
                      }
                    }}
                  >
                    Add
                  </Button>
                </div>
                {mortalityCauses.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {mortalityCauses.map((c, i) => (
                      <Badge
                        key={i}
                        variant="rejected"
                        className="text-[10px] px-2 py-0.5 cursor-pointer"
                        onClick={() =>
                          setMortalityCauses(mortalityCauses.filter((_, idx) => idx !== i))
                        }
                      >
                        {c} ✕
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <label className="font-semibold text-vana-charcoal block mb-1">
                  Field Notes (Optional)
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  placeholder="Additional sampling context or site notes..."
                  className="w-full p-2.5 rounded-md border border-vana-charcoal/20 text-xs"
                />
              </div>
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsRecordModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isSubmittingRecord || isOverSample}
                className="bg-vana-forest text-white"
              >
                {isSubmittingRecord ? "Submitting..." : "Submit Observation"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ===================================================================== */}
      {/* 2. Observation Correction (Supersession) Modal */}
      {/* ===================================================================== */}
      {targetObsForCorrection && (
        <Dialog open={isCorrectModalOpen} onOpenChange={setIsCorrectModalOpen}>
          <DialogContent className="max-w-md bg-white p-6 rounded-xl border border-vana-gold/30">
            <form onSubmit={handleSubmitCorrect} className="space-y-4">
              <DialogHeader>
                <DialogTitle className="text-lg font-bold font-manrope text-vana-forest">
                  Correct Survival Observation
                </DialogTitle>
                <DialogDescription className="text-xs text-vana-charcoal/70">
                  Performs atomic supersession: deactivates the original record and establishes an immutable correction audit trail.
                </DialogDescription>
              </DialogHeader>

              {corrError && (
                <div className="p-3 bg-vana-crimson/10 text-vana-crimson rounded-lg text-xs">
                  {corrError}
                </div>
              )}

              {/* Original observation card */}
              <div className="p-3 bg-vana-forest/5 rounded-lg border border-vana-forest/15 text-xs space-y-1">
                <span className="font-semibold text-vana-forest text-[11px] block">
                  Original Active Record ({targetObsForCorrection.plot_identifier} • {targetObsForCorrection.cohort_identifier})
                </span>
                <div className="grid grid-cols-3 gap-2 text-[11px] text-vana-charcoal/70">
                  <div>Sample: {targetObsForCorrection.sample_size}</div>
                  <div>Alive: {targetObsForCorrection.alive_count}</div>
                  <div>Dead: {targetObsForCorrection.dead_count}</div>
                </div>
              </div>

              {/* New counts */}
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="font-semibold text-vana-charcoal text-xs block mb-1">
                    New Sample *
                  </label>
                  <Input
                    type="number"
                    min="1"
                    value={corrSampleSize}
                    onChange={(e) => setCorrSampleSize(e.target.value)}
                    className="h-8 text-xs font-mono font-semibold"
                    required
                  />
                </div>

                <div>
                  <label className="font-semibold text-emerald-800 text-xs block mb-1">
                    New Alive *
                  </label>
                  <Input
                    type="number"
                    min="0"
                    value={corrAliveCount}
                    onChange={(e) => setCorrAliveCount(e.target.value)}
                    className="h-8 text-xs font-mono font-bold text-emerald-800"
                    required
                  />
                </div>

                <div>
                  <label className="font-semibold text-vana-crimson text-xs block mb-1">
                    New Dead *
                  </label>
                  <Input
                    type="number"
                    min="0"
                    value={corrDeadCount}
                    onChange={(e) => setCorrDeadCount(e.target.value)}
                    className="h-8 text-xs font-mono font-semibold text-vana-crimson"
                    required
                  />
                </div>
              </div>

              {/* Preview */}
              <div className="p-2.5 bg-emerald-50 rounded border border-emerald-600/20 text-xs flex justify-between items-center text-emerald-900">
                <span>New Derived Survival Rate:</span>
                <span className="font-bold font-mono">
                  {corrPreviewRate ? `${corrPreviewRate}%` : "N/A"}
                </span>
              </div>

              <div>
                <label className="font-semibold text-vana-charcoal text-xs block mb-1">
                  Correction Reason Notes *
                </label>
                <textarea
                  value={correctionReason}
                  onChange={(e) => setCorrectionReason(e.target.value)}
                  rows={3}
                  placeholder="Explain reason for supersession (e.g. Field recount protocol verified, recount resolved data entry typo)..."
                  className="w-full p-2 rounded-md border border-vana-charcoal/20 text-xs"
                  required
                />
              </div>

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsCorrectModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isSubmittingCorr}
                  className="bg-vana-gold text-vana-charcoal font-semibold"
                >
                  {isSubmittingCorr ? "Applying..." : "Apply Supersession"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};
