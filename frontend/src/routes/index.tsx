import React, { Suspense, lazy } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { LoginView } from "@/views/auth/LoginView";

// Lazy-loaded workspace views for optimal bundle splitting
const UserManagementView = lazy(() =>
  import("@/views/team/UserManagementView").then((m) => ({ default: m.UserManagementView }))
);
const ProjectPortfolioView = lazy(() =>
  import("@/views/projects/ProjectPortfolioView").then((m) => ({ default: m.ProjectPortfolioView }))
);
const ProjectWorkspaceView = lazy(() =>
  import("@/views/projects/ProjectWorkspaceView").then((m) => ({ default: m.ProjectWorkspaceView }))
);
const FieldOperationsView = lazy(() =>
  import("@/views/operations/FieldOperationsView").then((m) => ({ default: m.FieldOperationsView }))
);
const FieldMonitoringView = lazy(() =>
  import("@/views/monitoring/FieldMonitoringView").then((m) => ({ default: m.FieldMonitoringView }))
);
const VerificationCentreView = lazy(() =>
  import("@/views/verification/VerificationCentreView").then((m) => ({ default: m.VerificationCentreView }))
);
const OrganizationDashboardView = lazy(() =>
  import("@/views/dashboard/OrganizationDashboardView").then((m) => ({ default: m.OrganizationDashboardView }))
);
const LivingEarthMapView = lazy(() =>
  import("@/views/map/LivingEarthMapView").then((m) => ({ default: m.LivingEarthMapView }))
);
const AuditWorkspaceView = lazy(() =>
  import("@/views/audit/AuditWorkspaceView").then((m) => ({ default: m.AuditWorkspaceView }))
);

const RouteLoadingFallback: React.FC = () => (
  <div className="flex h-64 items-center justify-center">
    <div className="flex items-center gap-3 text-vana-forest">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-vana-forest border-t-transparent" />
      <span className="text-xs font-semibold text-vana-charcoal/70 uppercase tracking-wider">
        Loading workspace...
      </span>
    </div>
  </div>
);

export const AppRoutes: React.FC = () => {
  return (
    <Suspense fallback={<RouteLoadingFallback />}>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<LoginView />} />

        {/* Protected Routes inside AppShell */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          {/* Index redirects to Dashboard */}
          <Route index element={<Navigate to="/dashboard" replace />} />

          {/* Organization Dashboard accessible to all authenticated roles */}
          <Route path="dashboard" element={<OrganizationDashboardView />} />

          {/* Team Management — Restricted to ADMIN and PROJECT_MANAGER */}
          <Route
            path="team"
            element={
              <ProtectedRoute allowedRoles={["ADMIN", "PROJECT_MANAGER"]}>
                <UserManagementView />
              </ProtectedRoute>
            }
          />

          {/* Verification Centre — Restricted to ADMIN and PROJECT_MANAGER */}
          <Route
            path="verification"
            element={
              <ProtectedRoute allowedRoles={["ADMIN", "PROJECT_MANAGER"]}>
                <VerificationCentreView />
              </ProtectedRoute>
            }
          />

          {/* Audit History & Immutability Ledger — Restricted to ADMIN and PROJECT_MANAGER */}
          <Route
            path="audit"
            element={
              <ProtectedRoute allowedRoles={["ADMIN", "PROJECT_MANAGER"]}>
                <AuditWorkspaceView />
              </ProtectedRoute>
            }
          />

          {/* Projects Module */}
          <Route path="projects" element={<ProjectPortfolioView />} />
          <Route path="projects/:projectId" element={<ProjectWorkspaceView />} />
          <Route path="map" element={<LivingEarthMapView />} />
          <Route path="operations" element={<FieldOperationsView />} />
          <Route path="monitoring" element={<FieldMonitoringView />} />
          <Route path="analytics" element={<OrganizationDashboardView />} />

          {/* Catch-all route */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
};
