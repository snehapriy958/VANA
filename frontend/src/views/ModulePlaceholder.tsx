import React from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { Construction, ArrowLeft } from "lucide-react";

interface ModulePlaceholderProps {
  moduleName: string;
  milestone: string;
  description: string;
}

export const ModulePlaceholder: React.FC<ModulePlaceholderProps> = ({
  moduleName,
  milestone,
  description,
}) => {
  return (
    <PageContainer
      title={moduleName}
      description={`Module scheduled for activation in ${milestone}`}
    >
      <Card className="border-dashed border-vana-charcoal/20 bg-white/70">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto w-12 h-12 rounded-full bg-vana-ivory flex items-center justify-center text-vana-forest mb-2">
            <Construction className="h-6 w-6 text-vana-forest" />
          </div>
          <CardTitle className="text-xl font-heading text-vana-forest">
            {moduleName} Module
          </CardTitle>
          <CardDescription className="text-xs max-w-md mx-auto">
            {description}
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center py-6 space-y-4">
          <div>
            <Badge variant="pending">Scheduled for {milestone}</Badge>
          </div>
          <p className="text-xs text-vana-charcoal/70 max-w-lg mx-auto leading-relaxed">
            Per the VANA Architectural Invariant and Milestone-by-Milestone execution policy, this module interface will be activated once the preceding foundational milestones and backend APIs are validated.
          </p>
          <div className="pt-2">
            <Link to="/dashboard">
              <Button variant="outline" size="sm" className="inline-flex items-center gap-1.5">
                <ArrowLeft className="h-3.5 w-3.5" />
                <span>Return to Design System Showcase</span>
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  );
};
