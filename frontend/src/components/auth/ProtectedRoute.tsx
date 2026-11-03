import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { UserRole } from "@/types";
import { ShieldAlert, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Link } from "react-router-dom";

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedRoles,
}) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-vana-ivory/30">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 rounded-full border-3 border-vana-forest border-t-transparent animate-spin" />
          <span className="text-xs font-medium text-vana-charcoal/70">
            Verifying security credentials...
          </span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center p-4">
        <Card className="max-w-md w-full border-vana-crimson/20 shadow-lifted">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto w-12 h-12 rounded-full bg-vana-crimson/10 flex items-center justify-center text-vana-crimson mb-2">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <CardTitle className="text-xl font-heading text-vana-forest">
              Access Restricted (403 Forbidden)
            </CardTitle>
            <CardDescription className="text-xs">
              Role Permission Boundary Enforcement
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center space-y-4 pt-2">
            <p className="text-xs text-vana-charcoal/80 leading-relaxed">
              Your account currently holds the <strong className="text-vana-forest font-mono">{user.role}</strong> role. This view requires one of the following roles:
            </p>
            <div className="flex flex-wrap justify-center gap-1.5">
              {allowedRoles.map((r) => (
                <span
                  key={r}
                  className="px-2 py-0.5 text-[11px] font-mono rounded bg-vana-sage/20 text-vana-forest font-semibold"
                >
                  {r}
                </span>
              ))}
            </div>
            <div className="pt-2">
              <Link to="/dashboard">
                <Button variant="default" size="sm" className="inline-flex items-center gap-1.5">
                  <ArrowLeft className="h-3.5 w-3.5" />
                  <span>Return to Dashboard</span>
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
};
