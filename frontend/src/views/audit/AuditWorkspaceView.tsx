import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ShieldCheck,
  History,
  LayoutDashboard,
  FileCheck,
  Cpu,
  Layers,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { listProjects } from "@/services/projects";
import { auditService } from "@/services/auditService";
import {
  useAuditEvent,
  useAuditEvents,
  useEntityAuditTrail,
  useVerificationHistory,
  useVerifyAuditChain,
} from "@/hooks/useAudit";
import type {
  AuditChainVerificationResponse,
  AuditEntityCategory,
  AuditEventFilterParams,
  AuditLog,
  AuditVerificationFilterParams,
  AuditVerifyChainRequest,
} from "@/types/audit";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import { AuditOverviewTab } from "./components/AuditOverviewTab";
import { AuditTimelineTab } from "./components/AuditTimelineTab";
import { VerificationHistoryTab } from "./components/VerificationHistoryTab";
import { IntegrityConsoleTab } from "./components/IntegrityConsoleTab";
import { EntityHistoryTab } from "./components/EntityHistoryTab";
import { EventDetailDrawer } from "./components/EventDetailDrawer";

export const AuditWorkspaceView: React.FC = () => {
  const { user } = useAuth();

  // Active Workspace Tab
  const [activeTab, setActiveTab] = useState<
    "overview" | "timeline" | "verification" | "integrity" | "entity"
  >("overview");

  // Selected event for detail drawer
  const [selectedEvent, setSelectedEvent] = useState<AuditLog | null>(null);
  const [inspectEventId, setInspectEventId] = useState<string | null>(null);

  // Verification report state (persisted across tab switches in session)
  const [verificationReport, setVerificationReport] =
    useState<AuditChainVerificationResponse | null>(null);

  // Timeline Filters
  const [timelineFilters, setTimelineFilters] = useState<AuditEventFilterParams>({
    page: 1,
    page_size: 20,
  });

  // Verification History Filters
  const [verificationFilters, setVerificationFilters] = useState<AuditVerificationFilterParams>({
    page: 1,
    page_size: 20,
  });

  // Entity History Query
  const [entityQuery, setEntityQuery] = useState<{
    type: AuditEntityCategory;
    id: string;
  }>({
    type: "project",
    id: "",
  });

  // Fetch Projects for Filter Dropdowns
  const { data: projects = [] } = useQuery({
    queryKey: ["projects", "list"],
    queryFn: () => listProjects(),
    staleTime: 5 * 60 * 1000,
  });

  // Overview Queries
  const {
    data: overviewEventsData,
    refetch: refetchOverview,
  } = useAuditEvents({ page: 1, page_size: 5 });

  const { data: overviewVerificationsData } = useVerificationHistory({
    page: 1,
    page_size: 1,
  });

  // Timeline Query
  const {
    data: timelineData,
    isLoading: isTimelineLoading,
    refetch: refetchTimeline,
  } = useAuditEvents(timelineFilters, { enabled: activeTab === "timeline" });

  // Verification History Query
  const {
    data: verificationData,
    isLoading: isVerificationLoading,
    refetch: refetchVerification,
  } = useVerificationHistory(verificationFilters, {
    enabled: activeTab === "verification",
  });

  // Entity History Query
  const { data: entityData, isLoading: isEntityLoading } = useEntityAuditTrail(
    entityQuery.id ? entityQuery.type : undefined,
    entityQuery.id || undefined,
    1,
    { enabled: activeTab === "entity" && Boolean(entityQuery.id) }
  );

  // Detail event query (when inspected by ID)
  useAuditEvent(inspectEventId || undefined, {
    enabled: Boolean(inspectEventId),
  });

  // Integrity Verification Mutation
  const verifyChainMutation = useVerifyAuditChain();

  const handleRunVerification = async (request?: AuditVerifyChainRequest) => {
    try {
      const result = await verifyChainMutation.mutateAsync(request);
      setVerificationReport(result);
    } catch (err) {
      console.error("Cryptographic verification failed to execute:", err);
    }
  };

  const handleInspectEventById = async (eventId: string) => {
    setInspectEventId(eventId);
    // Find in currently loaded timeline or verification items
    const fromTimeline = timelineData?.items.find((i) => i.id === eventId);
    if (fromTimeline) {
      setSelectedEvent(fromTimeline);
      return;
    }
    // Otherwise open drawer with partial or trigger fetch
    try {
      const fetched = await auditService.getEvent(eventId);
      setSelectedEvent(fetched);
    } catch (err) {
      console.error("Failed to load audit event details:", err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="bg-white p-6 rounded-2xl border border-vana-charcoal/10 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="p-2 rounded-xl bg-vana-forest/10 text-vana-forest border border-vana-forest/20">
              <ShieldCheck className="w-6 h-6" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold font-serif text-vana-forest">
                  Audit History & Immutability Ledger
                </h1>
                <Badge variant="sage">Milestone 8</Badge>
                {user?.role === "ADMIN" ? (
                  <Badge variant="verified">Global Organization Scope</Badge>
                ) : (
                  <Badge variant="pending">Assigned Projects Scope</Badge>
                )}
              </div>
              <p className="text-xs text-vana-charcoal/70 mt-1">
                Zero-gap monotonic sequence chaining, SHA-256 digital digests, and immutable verification history in PostgreSQL.
              </p>
            </div>
          </div>
        </div>

        {/* Global Action / Status Badge */}
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              refetchOverview();
              refetchTimeline();
              refetchVerification();
            }}
            className="text-xs border-vana-charcoal/20"
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            Sync Ledger
          </Button>
          <Button
            size="sm"
            onClick={() => {
              setActiveTab("integrity");
              handleRunVerification();
            }}
            disabled={verifyChainMutation.isPending}
            className="bg-vana-forest hover:bg-vana-forest/90 text-white text-xs font-semibold"
          >
            <Cpu className="w-3.5 h-3.5 mr-1.5" />
            Verify Chain
          </Button>
        </div>
      </div>

      {/* Navigation Tab Bar */}
      <div className="flex border-b border-vana-charcoal/15 space-x-1 overflow-x-auto select-none">
        <button
          onClick={() => setActiveTab("overview")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            activeTab === "overview"
              ? "border-vana-forest text-vana-forest bg-vana-forest/5 rounded-t-lg"
              : "border-transparent text-vana-charcoal/60 hover:text-vana-charcoal hover:border-vana-charcoal/20"
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          Overview
        </button>

        <button
          onClick={() => setActiveTab("timeline")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            activeTab === "timeline"
              ? "border-vana-forest text-vana-forest bg-vana-forest/5 rounded-t-lg"
              : "border-transparent text-vana-charcoal/60 hover:text-vana-charcoal hover:border-vana-charcoal/20"
          }`}
        >
          <History className="w-4 h-4" />
          Audit Timeline
          {overviewEventsData && (
            <span className="text-[10px] font-mono px-1.5 py-0.2 bg-vana-charcoal/10 rounded-full">
              {overviewEventsData.total.toLocaleString()}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("verification")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            activeTab === "verification"
              ? "border-vana-forest text-vana-forest bg-vana-forest/5 rounded-t-lg"
              : "border-transparent text-vana-charcoal/60 hover:text-vana-charcoal hover:border-vana-charcoal/20"
          }`}
        >
          <FileCheck className="w-4 h-4" />
          Verification History
          {overviewVerificationsData && (
            <span className="text-[10px] font-mono px-1.5 py-0.2 bg-vana-charcoal/10 rounded-full">
              {overviewVerificationsData.total.toLocaleString()}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("integrity")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            activeTab === "integrity"
              ? "border-vana-forest text-vana-forest bg-vana-forest/5 rounded-t-lg"
              : "border-transparent text-vana-charcoal/60 hover:text-vana-charcoal hover:border-vana-charcoal/20"
          }`}
        >
          <Cpu className="w-4 h-4" />
          Integrity Console
          {verificationReport && (
            <span
              className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full ${
                verificationReport.is_valid && verificationReport.status === "VALID"
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-rose-100 text-rose-800"
              }`}
            >
              {verificationReport.status}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("entity")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            activeTab === "entity"
              ? "border-vana-forest text-vana-forest bg-vana-forest/5 rounded-t-lg"
              : "border-transparent text-vana-charcoal/60 hover:text-vana-charcoal hover:border-vana-charcoal/20"
          }`}
        >
          <Layers className="w-4 h-4" />
          Entity History
        </button>
      </div>

      {/* Workspace Tab Content */}
      <div className="pt-2">
        {activeTab === "overview" && (
          <AuditOverviewTab
            totalEvents={overviewEventsData?.total || 0}
            totalVerifications={overviewVerificationsData?.total || 0}
            recentEvents={overviewEventsData?.items || []}
            verificationReport={verificationReport}
            onNavigateTab={(tab) => setActiveTab(tab)}
            onSelectEvent={(event) => setSelectedEvent(event)}
          />
        )}

        {activeTab === "timeline" && (
          <AuditTimelineTab
            data={timelineData}
            isLoading={isTimelineLoading}
            projects={projects}
            filters={timelineFilters}
            onFilterChange={(f) => setTimelineFilters(f)}
            onSelectEvent={(event) => setSelectedEvent(event)}
            onRefresh={() => refetchTimeline()}
          />
        )}

        {activeTab === "verification" && (
          <VerificationHistoryTab
            data={verificationData}
            isLoading={isVerificationLoading}
            projects={projects}
            filters={verificationFilters}
            onFilterChange={(f) => setVerificationFilters(f)}
            onInspectEventId={(id) => handleInspectEventById(id)}
            onRefresh={() => refetchVerification()}
          />
        )}

        {activeTab === "integrity" && (
          <IntegrityConsoleTab
            report={verificationReport}
            isVerifying={verifyChainMutation.isPending}
            onRunVerification={(req) => handleRunVerification(req)}
          />
        )}

        {activeTab === "entity" && (
          <EntityHistoryTab
            data={entityData}
            isLoading={isEntityLoading}
            projects={projects}
            selectedType={entityQuery.type}
            selectedId={entityQuery.id}
            onSearch={(t, id) => setEntityQuery({ type: t, id })}
            onSelectEvent={(event) => setSelectedEvent(event)}
          />
        )}
      </div>

      {/* Slide-out Event Detail Inspector Drawer */}
      <EventDetailDrawer
        event={selectedEvent}
        onClose={() => {
          setSelectedEvent(null);
          setInspectEventId(null);
        }}
      />
    </div>
  );
};
