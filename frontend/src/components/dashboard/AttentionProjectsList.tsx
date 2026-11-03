import React from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, CheckCircle2, ChevronRight, Clock } from "lucide-react";
import type { AttentionProjectItem } from "@/types/analytics";

interface AttentionProjectsListProps {
  projects: AttentionProjectItem[];
  className?: string;
}

export const AttentionProjectsList: React.FC<AttentionProjectsListProps> = ({
  projects,
  className,
}) => {
  return (
    <Card className={className}>
      <CardHeader className="pb-3 border-b border-forest/10">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-manrope text-forest font-bold flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600" />
              Projects Requiring Attention
            </CardTitle>
            <CardDescription className="text-xs text-charcoal/70">
              Operational alerts, pending verification queues, and deadline pacing
            </CardDescription>
          </div>
          <Badge variant="outline" className="text-xs bg-forest/5 text-forest border-forest/20">
            {projects.length} {projects.length === 1 ? "Project" : "Projects"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-3 px-3">
        {projects.length === 0 ? (
          <div className="py-8 flex flex-col items-center justify-center text-center px-4">
            <div className="w-10 h-10 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mb-2">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <p className="text-sm font-semibold font-manrope text-forest">
              All Projects on Track
            </p>
            <p className="text-xs text-charcoal/60 mt-0.5">
              No verification backlogs or urgent target deadlines detected across portfolio.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-forest/5">
            {projects.map((item) => (
              <div
                key={item.project_id}
                className="py-3 px-2 flex items-start justify-between gap-3 hover:bg-forest/5 rounded-lg transition-colors"
              >
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-forest font-manrope truncate">
                      {item.project_name}
                    </span>
                    <Badge variant="outline" className="text-[10px] h-4 px-1.5 font-mono text-charcoal/70">
                      {item.project_code}
                    </Badge>
                    <Badge
                      className={`text-[10px] h-4 px-1.5 uppercase font-semibold ${
                        item.severity === "HIGH"
                          ? "bg-rose-100 text-rose-800 border-rose-200"
                          : item.severity === "MEDIUM"
                          ? "bg-amber-100 text-amber-800 border-amber-200"
                          : "bg-emerald-100 text-emerald-800 border-emerald-200"
                      }`}
                    >
                      {item.severity}
                    </Badge>
                  </div>
                  <p className="text-xs text-charcoal/80 leading-relaxed">
                    {item.reason}
                  </p>
                  {item.pending_verifications_count > 0 && (
                    <div className="flex items-center gap-3 pt-0.5 text-[11px] text-charcoal/60">
                      <span className="flex items-center gap-1 text-amber-700 font-medium">
                        <Clock className="w-3 h-3" />
                        {item.pending_verifications_count} pending review
                      </span>
                    </div>
                  )}
                </div>

                <Link
                  to={`/projects/${item.project_id}`}
                  className="p-1.5 text-charcoal/40 hover:text-forest hover:bg-forest/10 rounded-lg shrink-0 transition-colors self-center"
                  title="Open Project Workspace"
                >
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
