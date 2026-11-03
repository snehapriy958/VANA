import React from "react";
import { cn } from "@/lib/utils";

interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  description?: string;
  action?: React.ReactNode;
}

export const PageContainer: React.FC<PageContainerProps> = ({
  children,
  className,
  title,
  description,
  action,
}) => {
  return (
    <div className={cn("flex flex-col gap-6 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full", className)}>
      {(title || action) && (
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-vana-charcoal/10">
          <div>
            {title && (
              <h1 className="text-2xl sm:text-3xl font-extrabold text-vana-forest font-heading tracking-tight">
                {title}
              </h1>
            )}
            {description && (
              <p className="text-sm text-vana-charcoal/70 mt-1">
                {description}
              </p>
            )}
          </div>
          {action && <div className="mt-4 sm:mt-0 flex items-center gap-3">{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
};
