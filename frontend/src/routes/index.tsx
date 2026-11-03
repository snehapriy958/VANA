import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { LoginView } from "@/views/auth/LoginView";
import { UserManagementView } from "@/views/team/UserManagementView";
import { ProjectPortfolioView } from "@/views/projects/ProjectPortfolioView";
import { ProjectWorkspaceView } from "@/views/projects/ProjectWorkspaceView";
import { FieldOperationsView } from "@/views/operations/FieldOperationsView";
import { VerificationCentreView } from "@/views/verification/VerificationCentreView";
import { OrganizationDashboardView } from "@/views/dashboard/OrganizationDashboardView";
import { LivingEarthMapView } from "@/views/map/LivingEarthMapView";
import { ModulePlaceholder } from "@/views/ModulePlaceholder";

export const AppRoutes: React.FC = () => {
  return (
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

        {/* Audit History — Restricted to ADMIN */}
        <Route
          path="audit"
          element={
            <ProtectedRoute allowedRoles={["ADMIN"]}>
              <ModulePlaceholder
                moduleName="Audit History & Immutability Ledger"
                milestone="Milestone 8"
                description="Cryptographic hash integrity, immutable verification log, and change history."
              />
            </ProtectedRoute>
          }
        />

        {/* Projects Module */}
        <Route path="projects" element={<ProjectPortfolioView />} />
        <Route path="projects/:projectId" element={<ProjectWorkspaceView />} />
        <Route path="map" element={<LivingEarthMapView />} />
        <Route path="operations" element={<FieldOperationsView />} />
        <Route path="analytics" element={<OrganizationDashboardView />} />

        {/* Catch-all route */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
};
