import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  badge?: {
    text: string;
    variant?: "default" | "success" | "warning" | "destructive" | "outline";
  };
  className?: string;
  onClick?: () => void;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  icon,
  badge,
  className,
  onClick,
}) => {
  return (
    <Card
      className={cn(
        "relative overflow-hidden transition-all duration-200 border-forest/10 hover:border-forest/20 shadow-sm",
        onClick && "cursor-pointer hover:shadow-md hover:-translate-y-0.5",
        className
      )}
      onClick={onClick}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-charcoal/60">
              {title}
            </p>
            <div className="text-2xl font-bold font-manrope text-forest tracking-tight">
              {value}
            </div>
            {subtitle && (
              <p className="text-xs text-charcoal/70 line-clamp-1">
                {subtitle}
              </p>
            )}
          </div>
          {icon && (
            <div className="p-2.5 rounded-xl bg-forest/5 text-forest shrink-0">
              {icon}
            </div>
          )}
        </div>
        {badge && (
          <div className="mt-3 pt-3 border-t border-forest/5 flex items-center justify-between">
            <span
              className={cn(
                "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
                badge.variant === "warning" && "bg-amber-100 text-amber-900 border border-amber-200",
                badge.variant === "success" && "bg-emerald-100 text-emerald-900 border border-emerald-200",
                badge.variant === "destructive" && "bg-rose-100 text-rose-900 border border-rose-200",
                (!badge.variant || badge.variant === "default") && "bg-forest/10 text-forest border border-forest/20"
              )}
            >
              {badge.text}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
