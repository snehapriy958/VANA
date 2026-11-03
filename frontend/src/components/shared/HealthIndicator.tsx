import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import { fetchHealthStatus } from "@/services/apiClient";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export const HealthIndicator: React.FC = () => {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["backend-health"],
    queryFn: fetchHealthStatus,
    refetchInterval: 30000, // Poll health every 30 seconds
    retry: 1,
  });

  if (isLoading) {
    return (
      <Badge variant="outline" className="flex items-center gap-1.5 px-3 py-1 bg-white/50 border-vana-charcoal/10">
        <Activity className="h-3 w-3 animate-spin text-vana-charcoal/60" />
        <span className="text-xs text-vana-charcoal/70">Connecting...</span>
      </Badge>
    );
  }

  const isHealthy = data?.status === "healthy" && !isError;

  return (
    <div className="flex items-center gap-2">
      <Badge
        variant={isHealthy ? "verified" : "rejected"}
        className="flex items-center gap-1.5 px-3 py-1 text-xs transition-colors shadow-subtle"
      >
        {isHealthy ? (
          <CheckCircle2 className="h-3.5 w-3.5 text-vana-forest" />
        ) : (
          <AlertCircle className="h-3.5 w-3.5 text-vana-crimson" />
        )}
        <span className="font-medium">
          {isHealthy ? "API Online" : "API Offline"}
        </span>
        {isHealthy && data?.database && (
          <span className="text-[10px] opacity-75 font-normal border-l border-vana-forest/20 pl-1.5">
            DB: {data.database}
          </span>
        )}
      </Badge>

      <Button
        variant="ghost"
        size="icon"
        onClick={() => refetch()}
        disabled={isFetching}
        className="h-7 w-7 text-vana-charcoal/60 hover:text-vana-charcoal"
        title="Refresh Backend Health"
      >
        <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
      </Button>
    </div>
  );
};
