import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { rootClient, BACKEND_URL } from "@/services/apiClient";
import { HealthStatus } from "@/types";
import { PageContainer } from "@/components/layout/PageContainer";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Trees,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Database,
  Server,
  Sparkles,
  Layers,
  ArrowUpRight,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";

export const DesignSystemShowcase: React.FC = () => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [testInput, setTestInput] = useState("Kaveri Delta Agroforestry");

  // Live Backend Health Query
  const {
    data: health,
    isLoading: isHealthLoading,
    isError: isHealthError,
    error: healthError,
    refetch: refetchHealth,
    isFetching: isHealthFetching,
  } = useQuery<HealthStatus>({
    queryKey: ["backend-health-detailed"],
    queryFn: async () => {
      const res = await rootClient.get<HealthStatus>("/health");
      return res.data;
    },
    refetchInterval: 10000,
  });

  return (
    <PageContainer
      title="Design System & Component Foundation"
      description="Akshaya Vana Platform — Milestone 1B Foundation, Design Tokens, & System Readiness"
      action={
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchHealth()}
            disabled={isHealthFetching}
            className="flex items-center gap-1.5"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${isHealthFetching ? "animate-spin text-vana-forest" : ""}`}
            />
            <span>Refresh Health</span>
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={() => setDialogOpen(true)}
          >
            Launch Dialog
          </Button>
        </div>
      }
    >
      {/* SECTION 1: Backend Connection Status Banner */}
      <section className="space-y-3">
        <div className="flex items-center gap-2 text-vana-forest font-heading font-bold text-lg">
          <Server className="h-5 w-5 text-vana-forest" />
          <h2>Backend Live Connectivity</h2>
        </div>
        <Card className="border-vana-forest/20 bg-linear-to-r from-vana-ivory/80 via-white to-vana-sage/10">
          <CardHeader className="pb-3">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div className="flex items-center gap-3">
                <div
                  className={`h-3.5 w-3.5 rounded-full ${
                    isHealthLoading
                      ? "bg-amber-400 animate-pulse"
                      : isHealthError
                      ? "bg-vana-crimson"
                      : health?.database === "connected"
                      ? "bg-emerald-600 ring-4 ring-emerald-100"
                      : "bg-amber-500"
                  }`}
                />
                <div>
                  <CardTitle className="text-base text-vana-forest font-heading">
                    FastAPI REST Core & PostgreSQL Connection
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Target: {BACKEND_URL}/health
                  </CardDescription>
                </div>
              </div>

              <div>
                {isHealthLoading ? (
                  <Badge variant="pending">Checking...</Badge>
                ) : isHealthError ? (
                  <Badge variant="rejected">Offline / Unreachable</Badge>
                ) : health?.database === "connected" ? (
                  <Badge variant="verified" className="flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    <span>Database Healthy</span>
                  </Badge>
                ) : (
                  <Badge variant="pending">DB Degraded</Badge>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2 border-t border-vana-charcoal/10 text-xs">
              <div>
                <span className="text-vana-charcoal/60 block">Status:</span>
                <span className="font-semibold text-vana-charcoal uppercase tracking-wider font-mono">
                  {health?.status || "UNKNOWN"}
                </span>
              </div>
              <div>
                <span className="text-vana-charcoal/60 block">Database:</span>
                <span className="font-semibold text-vana-forest flex items-center gap-1 font-mono">
                  <Database className="h-3 w-3" />
                  {health?.database || "DISCONNECTED"}
                </span>
              </div>
              <div>
                <span className="text-vana-charcoal/60 block">Environment:</span>
                <span className="font-semibold text-vana-charcoal font-mono">
                  {health?.environment || "development"}
                </span>
              </div>
              <div>
                <span className="text-vana-charcoal/60 block">Version:</span>
                <span className="font-semibold text-vana-charcoal font-mono">
                  v{health?.version || "0.1.0"}
                </span>
              </div>
            </div>
            {isHealthError && (
              <div className="mt-3 p-3 bg-vana-crimson/10 border border-vana-crimson/30 rounded-md text-xs text-vana-crimson">
                <strong>Probe Error:</strong> {String(healthError?.message || "Failed to reach backend")}
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* SECTION 2: Design Tokens & Palette */}
      <section className="space-y-4">
        <div className="flex items-center gap-2 text-vana-forest font-heading font-bold text-lg">
          <Sparkles className="h-5 w-5 text-vana-gold" />
          <h2>Approved Design Tokens</h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-vana-forest text-white p-4 rounded-lg shadow-subtle border border-black/10 flex flex-col justify-between h-28">
            <span className="text-xs font-semibold uppercase tracking-wider opacity-80">Forest</span>
            <div>
              <div className="font-heading font-bold text-base">#183D32</div>
              <div className="text-[11px] opacity-75">Primary / Headings</div>
            </div>
          </div>
          <div className="bg-vana-ivory text-vana-charcoal p-4 rounded-lg shadow-subtle border border-vana-charcoal/15 flex flex-col justify-between h-28">
            <span className="text-xs font-semibold uppercase tracking-wider opacity-80">Ivory</span>
            <div>
              <div className="font-heading font-bold text-base">#F5F3EA</div>
              <div className="text-[11px] opacity-75">Canvas / Surfaces</div>
            </div>
          </div>
          <div className="bg-vana-sage text-vana-charcoal p-4 rounded-lg shadow-subtle border border-vana-forest/20 flex flex-col justify-between h-28">
            <span className="text-xs font-semibold uppercase tracking-wider opacity-80">Sage</span>
            <div>
              <div className="font-heading font-bold text-base">#A8B99B</div>
              <div className="text-[11px] opacity-75">Accents / Muted</div>
            </div>
          </div>
          <div className="bg-vana-gold text-vana-charcoal p-4 rounded-lg shadow-subtle border border-amber-600/20 flex flex-col justify-between h-28">
            <span className="text-xs font-semibold uppercase tracking-wider opacity-80">Gold</span>
            <div>
              <div className="font-heading font-bold text-base">#D6A76A</div>
              <div className="text-[11px] opacity-75">Highlights / Warmth</div>
            </div>
          </div>
          <div className="bg-vana-charcoal text-white p-4 rounded-lg shadow-subtle border border-black/20 flex flex-col justify-between h-28">
            <span className="text-xs font-semibold uppercase tracking-wider opacity-80">Charcoal</span>
            <div>
              <div className="font-heading font-bold text-base">#29332F</div>
              <div className="text-[11px] opacity-75">Body Text / Lines</div>
            </div>
          </div>
          <div className="bg-white text-vana-charcoal p-4 rounded-lg shadow-subtle border border-vana-charcoal/20 flex flex-col justify-between h-28">
            <span className="text-xs font-semibold uppercase tracking-wider opacity-80">White</span>
            <div>
              <div className="font-heading font-bold text-base">#FFFFFF</div>
              <div className="text-[11px] opacity-75">Cards / Elevated</div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 3: Sample Environmental Cards */}
      <section className="space-y-4">
        <div className="flex items-center gap-2 text-vana-forest font-heading font-bold text-lg">
          <Layers className="h-5 w-5 text-vana-forest" />
          <h2>Sample Environmental Metric Cards</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Card 1: Trees Planted */}
          <Card className="hover:shadow-card transition-shadow">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <Badge variant="verified">Verified Ledger</Badge>
                <Trees className="h-4 w-4 text-vana-forest" />
              </div>
              <CardTitle className="text-base text-vana-forest font-heading mt-2">
                Trees Planted (TREES_PLANTED)
              </CardTitle>
              <CardDescription className="text-xs">
                Kaveri River Riparian Buffer Project
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-extrabold text-vana-forest font-heading tabular-nums">
                24,500 <span className="text-sm font-sans font-medium text-vana-charcoal/70">trees</span>
              </div>
              <p className="text-xs text-vana-charcoal/70 mt-2 leading-relaxed">
                Active verified quantity from approved field submissions. Anti-self-verification enforced.
              </p>
            </CardContent>
            <CardFooter className="pt-2 border-t border-vana-charcoal/10 flex items-center justify-between text-xs text-vana-charcoal/70">
              <span>Target: 30,000 trees</span>
              <span className="font-semibold text-vana-forest tabular-nums">81.6% Achieved</span>
            </CardFooter>
          </Card>

          {/* Card 2: Restored Area */}
          <Card className="hover:shadow-card transition-shadow">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <Badge variant="pending">Revision Under Review</Badge>
                <Clock className="h-4 w-4 text-amber-600" />
              </div>
              <CardTitle className="text-base text-vana-forest font-heading mt-2">
                Area Restored (AREA_RESTORED)
              </CardTitle>
              <CardDescription className="text-xs">
                Western Ghats Corridor Restoration
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-extrabold text-vana-forest font-heading tabular-nums">
                142.5 <span className="text-sm font-sans font-medium text-vana-charcoal/70">hectares</span>
              </div>
              <p className="text-xs text-vana-charcoal/70 mt-2 leading-relaxed">
                Current pending amendment. Quantities strictly segregated from official ledger until verified.
              </p>
            </CardContent>
            <CardFooter className="pt-2 border-t border-vana-charcoal/10 flex items-center justify-between text-xs text-vana-charcoal/70">
              <span>Submitted: 2 hrs ago</span>
              <span className="font-semibold text-amber-700">Pending PM Review</span>
            </CardFooter>
          </Card>

          {/* Card 3: Rejected / Audit Correction */}
          <Card className="hover:shadow-card transition-shadow">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <Badge variant="rejected">Revision Rejected</Badge>
                <AlertTriangle className="h-4 w-4 text-vana-crimson" />
              </div>
              <CardTitle className="text-base text-vana-forest font-heading mt-2">
                Water Harvested (RAINWATER)
              </CardTitle>
              <CardDescription className="text-xs">
                Deccan Plateau Catchment Initiative
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-extrabold text-vana-charcoal/50 font-heading tabular-nums">
                500,000 <span className="text-sm font-sans font-medium">liters</span>
              </div>
              <p className="text-xs text-vana-crimson mt-2 leading-relaxed">
                Rejection reason required: GPS tag outside project polygon boundary. Historical record preserved.
              </p>
            </CardContent>
            <CardFooter className="pt-2 border-t border-vana-charcoal/10 flex items-center justify-between text-xs text-vana-charcoal/70">
              <span>Action: Resubmission open</span>
              <span className="font-semibold text-vana-crimson">Audit ID #REV-094</span>
            </CardFooter>
          </Card>
        </div>
      </section>

      {/* SECTION 4: Component Primitives Showcase */}
      <section className="space-y-4">
        <div className="flex items-center gap-2 text-vana-forest font-heading font-bold text-lg">
          <ShieldCheck className="h-5 w-5 text-vana-forest" />
          <h2>UI Primitives: Buttons, Badges & Inputs</h2>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base font-heading text-vana-forest">
              Button Variants & Status Badges
            </CardTitle>
            <CardDescription className="text-xs">
              Interactive states including focus rings, hover, disabled and active transitions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Buttons Row */}
            <div>
              <div className="text-xs font-semibold text-vana-charcoal/70 uppercase tracking-wider mb-2">
                Button Styles
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Button variant="default">Primary Forest</Button>
                <Button variant="secondary">Secondary Ivory</Button>
                <Button variant="gold">Earth Gold Action</Button>
                <Button variant="outline">Outline Border</Button>
                <Button variant="ghost">Ghost Plain</Button>
                <Button variant="destructive">Destructive / Reject</Button>
                <Button variant="default" disabled>
                  Disabled
                </Button>
              </div>
            </div>

            {/* Sizes Row */}
            <div>
              <div className="text-xs font-semibold text-vana-charcoal/70 uppercase tracking-wider mb-2">
                Button Sizes
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Button size="sm">Small (sm)</Button>
                <Button size="default">Default</Button>
                <Button size="lg">Large (lg)</Button>
                <Button size="icon" aria-label="Icon sample">
                  <ArrowUpRight className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Badges Row */}
            <div>
              <div className="text-xs font-semibold text-vana-charcoal/70 uppercase tracking-wider mb-2">
                Status Badges
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Badge variant="verified">Verified (Official)</Badge>
                <Badge variant="pending">Pending Verification</Badge>
                <Badge variant="rejected">Rejected / Needs Review</Badge>
                <Badge variant="active">Active Project</Badge>
                <Badge variant="neutral">Draft / Neutral</Badge>
              </div>
            </div>

            {/* Input Row */}
            <div>
              <div className="text-xs font-semibold text-vana-charcoal/70 uppercase tracking-wider mb-2">
                Input Fields & Validation Styling
              </div>
              <div className="max-w-md space-y-2">
                <label className="text-xs font-medium text-vana-charcoal">
                  Sample Project Identifier:
                </label>
                <Input
                  value={testInput}
                  onChange={(e) => setTestInput(e.target.value)}
                  placeholder="Enter project name..."
                />
                <span className="text-[11px] text-vana-charcoal/60">
                  Real-time bound value: &ldquo;{testInput}&rdquo;
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* SECTION 5: Interactive Dialog Modal */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogTrigger asChild>
          <div className="hidden" />
        </DialogTrigger>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Verification State Machine</DialogTitle>
            <DialogDescription>
              Demonstrating the VANA modal dialog primitive adhering to accessible focus traps, overlay blurs, and typography invariants.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2 text-xs text-vana-charcoal/80">
            <p>
              In Milestone 2 &amp; 3, this modal foundation will power Activity Submission, Amendment Reviews, and Verification Signatures with cryptographic hash audit logging.
            </p>
            <div className="p-3 bg-vana-sage/20 rounded-md border border-vana-forest/15">
              <span className="font-semibold text-vana-forest block">Invariant Enforcement:</span>
              Verifier ID cannot equal Creator ID (HTTP 403 Anti-Self-Verification rule).
            </div>
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="default"
              onClick={() => {
                alert("Dialog action confirmed!");
                setDialogOpen(false);
              }}
            >
              Confirm Action
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
};
