import React from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { CheckCircle2, XCircle, FileText, RefreshCw, Activity, ArrowUpRight } from "lucide-react";
import type { RecentActivityItem } from "@/types/analytics";

interface RecentActivityFeedProps {
  activities: RecentActivityItem[];
  className?: string;
}

export const RecentActivityFeed: React.FC<RecentActivityFeedProps> = ({
  activities,
  className,
}) => {
  const getEventIcon = (type: string) => {
    switch (type) {
      case "VERIFICATION":
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />;
      case "REJECTION":
        return <XCircle className="w-3.5 h-3.5 text-rose-600" />;
      case "AMENDMENT":
        return <RefreshCw className="w-3.5 h-3.5 text-amber-600" />;
      case "SUBMISSION":
      default:
        return <FileText className="w-3.5 h-3.5 text-forest" />;
    }
  };

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  return (
    <Card className={className}>
      <CardHeader className="pb-3 border-b border-forest/10">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-manrope text-forest font-bold flex items-center gap-2">
              <Activity className="w-4 h-4 text-forest" />
              Recent Operational Activity
            </CardTitle>
            <CardDescription className="text-xs text-charcoal/70">
              Live audit stream of field submissions, amendments, and verification decisions
            </CardDescription>
          </div>
          <Link
            to="/operations"
            className="text-xs font-semibold text-forest hover:underline flex items-center gap-1"
          >
            Operations <ArrowUpRight className="w-3 h-3" />
          </Link>
        </div>
      </CardHeader>
      <CardContent className="pt-3 px-3">
        {activities.length === 0 ? (
          <div className="py-8 flex flex-col items-center justify-center text-center px-4">
            <p className="text-sm font-semibold font-manrope text-forest">
              No Operational Events Recorded
            </p>
            <p className="text-xs text-charcoal/60 mt-0.5">
              Field activities and verification signatures will stream live here.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-forest/5 max-h-96 overflow-y-auto pr-1">
            {activities.map((item) => (
              <div
                key={item.id}
                className="py-3 px-2 flex items-start gap-3 hover:bg-forest/5 rounded-lg transition-colors"
              >
                <div className="p-1.5 rounded-lg bg-forest/5 shrink-0 mt-0.5">
                  {getEventIcon(item.event_type)}
                </div>
                <div className="space-y-1 min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-semibold text-forest truncate">
                      {item.title}
                    </p>
                    <span className="text-[10px] text-charcoal/50 whitespace-nowrap">
                      {formatTimestamp(item.timestamp)}
                    </span>
                  </div>
                  <p className="text-xs text-charcoal/80 leading-relaxed">
                    {item.description}
                  </p>
                  <div className="flex items-center gap-2 pt-0.5 text-[11px] text-charcoal/60">
                    <Link
                      to={`/projects/${item.project_id}`}
                      className="font-mono text-forest/80 hover:text-forest hover:underline"
                    >
                      {item.project_code}
                    </Link>
                    <span>•</span>
                    <span className="truncate">{item.project_name}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
