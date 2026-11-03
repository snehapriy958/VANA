import React, { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { MetricProgressSummary, ProjectTrendPoint } from "@/types/analytics";

interface EnvironmentalImpactChartProps {
  metrics: MetricProgressSummary[];
  trends?: ProjectTrendPoint[];
  title?: string;
  description?: string;
  className?: string;
}

export const EnvironmentalImpactChart: React.FC<EnvironmentalImpactChartProps> = ({
  metrics,
  trends = [],
  title = "Environmental Impact Overview",
  description = "Verified operational achievements against defined targets",
  className,
}) => {
  const [activeTab, setActiveTab] = useState<"targets" | "trends">("targets");

  // Transform metrics for Target vs Verified Bar Chart
  const chartData = metrics
    .filter((m) => m.total_target_quantity !== null || Number(m.total_verified_quantity) > 0)
    .map((m) => {
      const verified = Number(m.total_verified_quantity) || 0;
      const target = Number(m.total_target_quantity) || 0;
      const pending = Number(m.total_pending_adjustment) || 0;
      return {
        name: m.display_name,
        code: m.metric_code,
        unit: m.canonical_unit,
        verified,
        target,
        pending,
        achievement: m.overall_achievement_percentage ?? 0,
      };
    });

  return (
    <Card className={className}>
      <CardHeader className="pb-3 border-b border-forest/10">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <CardTitle className="text-lg font-manrope text-forest font-bold">
              {title}
            </CardTitle>
            <CardDescription className="text-xs text-charcoal/70">
              {description}
            </CardDescription>
          </div>
          {trends.length > 0 && (
            <div className="flex items-center gap-1.5 p-1 bg-forest/5 rounded-lg border border-forest/10 self-start sm:self-auto">
              <Button
                variant={activeTab === "targets" ? "default" : "ghost"}
                size="sm"
                className={`text-xs h-7 px-2.5 ${activeTab === "targets" ? "bg-forest text-white shadow-xs" : "text-charcoal/80"}`}
                onClick={() => setActiveTab("targets")}
              >
                Targets vs Verified
              </Button>
              <Button
                variant={activeTab === "trends" ? "default" : "ghost"}
                size="sm"
                className={`text-xs h-7 px-2.5 ${activeTab === "trends" ? "bg-forest text-white shadow-xs" : "text-charcoal/80"}`}
                onClick={() => setActiveTab("trends")}
              >
                Activity Velocity
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        {activeTab === "targets" ? (
          chartData.length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 bg-forest/5 rounded-xl border border-dashed border-forest/20">
              <p className="text-sm font-medium text-forest font-manrope">
                No active targets or verified achievements yet
              </p>
              <p className="text-xs text-charcoal/60 mt-1 max-w-sm">
                As field officers record submissions and project managers verify them, real-time comparisons will render here.
              </p>
            </div>
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  margin={{ top: 20, right: 30, left: 10, bottom: 25 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#183D32" strokeOpacity={0.08} />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: "#29332F", fontSize: 11 }}
                    interval={0}
                    angle={-15}
                    textAnchor="end"
                  />
                  <YAxis tick={{ fill: "#29332F", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#FFFFFF",
                      borderRadius: "8px",
                      border: "1px solid rgba(24, 61, 50, 0.15)",
                      boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                      fontSize: "12px",
                    }}
                    formatter={(value: any, name: any, item: any) => {
                      const unit = item.payload.unit || "";
                      const formatted = Number(value).toLocaleString();
                      if (name === "Verified Official") return [`${formatted} ${unit}`, name];
                      if (name === "Target Plan") return [`${formatted} ${unit}`, name];
                      if (name === "Net Pending") return [`${formatted} ${unit}`, name];
                      return [value, name];
                    }}
                  />
                  <Legend
                    verticalAlign="top"
                    wrapperStyle={{ paddingBottom: 15, fontSize: 12 }}
                  />
                  <Bar
                    dataKey="verified"
                    name="Verified Official"
                    fill="#183D32"
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar
                    dataKey="target"
                    name="Target Plan"
                    fill="#D6A76A"
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar
                    dataKey="pending"
                    name="Net Pending"
                    fill="#A8B99B"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )
        ) : (
          trends.length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 bg-forest/5 rounded-xl border border-dashed border-forest/20">
              <p className="text-sm font-medium text-forest font-manrope">
                No activity trend data available for selected period
              </p>
            </div>
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={trends}
                  margin={{ top: 20, right: 30, left: 10, bottom: 25 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#183D32" strokeOpacity={0.08} />
                  <XAxis dataKey="date" tick={{ fill: "#29332F", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#29332F", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#FFFFFF",
                      borderRadius: "8px",
                      border: "1px solid rgba(24, 61, 50, 0.15)",
                      boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                      fontSize: "12px",
                    }}
                    formatter={(val: any, name: any, item: any) => [
                      `${Number(val).toLocaleString()} ${item.payload.unit || ""}`,
                      name,
                    ]}
                  />
                  <Legend verticalAlign="top" wrapperStyle={{ paddingBottom: 15, fontSize: 12 }} />
                  <Line
                    type="monotone"
                    dataKey="cumulative_quantity"
                    name="Cumulative Verified"
                    stroke="#183D32"
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: "#183D32" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="period_quantity"
                    name="Daily Quantity"
                    stroke="#D6A76A"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    dot={{ r: 3, fill: "#D6A76A" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )
        )}
      </CardContent>
    </Card>
  );
};
