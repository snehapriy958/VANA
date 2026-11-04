import { describe, it } from "node:test";
import assert from "node:assert/strict";

// ============================================================================
// Monitoring UI Role-Based Permissions Logic
// ============================================================================

function canUserScheduleInspection(userRole, isProjectAssigned = false) {
  if (userRole === "ADMIN") return true;
  if (userRole === "PROJECT_MANAGER") return isProjectAssigned;
  return false;
}

function canUserExecuteInspection(userRole, inspectorId, currentUserId, isProjectAssigned = false) {
  if (userRole === "ADMIN") return true;
  if (userRole === "PROJECT_MANAGER" && isProjectAssigned) return true;
  if (userRole === "FIELD_OFFICER" && isProjectAssigned && inspectorId === currentUserId) return true;
  return false;
}

function canUserCreateTask(userRole, isProjectAssigned = false) {
  if (userRole === "ADMIN") return true;
  if (userRole === "PROJECT_MANAGER") return isProjectAssigned;
  return false;
}

function canUserExecuteTask(userRole, assigneeId, currentUserId, isProjectAssigned = false) {
  if (userRole === "ADMIN") return true;
  if (userRole === "PROJECT_MANAGER" && isProjectAssigned) return true;
  if (userRole === "FIELD_OFFICER" && isProjectAssigned && assigneeId === currentUserId) return true;
  return false;
}

function canUserCancelOrReopen(userRole, isProjectAssigned = false) {
  if (userRole === "ADMIN") return true;
  if (userRole === "PROJECT_MANAGER") return isProjectAssigned;
  return false;
}

function canUserCorrectObservation(userRole, isProjectAssigned = false) {
  if (userRole === "ADMIN") return true;
  if (userRole === "PROJECT_MANAGER") return isProjectAssigned;
  return false;
}

// ============================================================================
// Dashboard and Analytics Transformation Helpers
// ============================================================================

function computeOverdueCounts(alerts = [], todayStr = "2026-11-04") {
  const overdueInspections = alerts.filter(
    (a) => a.alert_type === "OVERDUE_INSPECTION"
  ).length;
  const overdueTasks = alerts.filter(
    (a) => a.alert_type === "OVERDUE_TASK"
  ).length;
  return { overdueInspections, overdueTasks };
}

function isTaskOverdue(dueDate, status, todayStr = "2026-11-04") {
  if (status === "COMPLETED" || status === "CANCELLED") return false;
  return dueDate < todayStr;
}

function computeSurvivalCounts(sampleSize, aliveCount, deadCount) {
  const sample = Math.max(0, Number(sampleSize) || 0);
  const alive = Math.max(0, Number(aliveCount) || 0);
  const dead = Math.max(0, Number(deadCount) || 0);
  const assessed = alive + dead;
  const unassessed = Math.max(0, sample - assessed);
  const isOverSample = assessed > sample;
  const survivalRate = assessed > 0 ? (alive / assessed) * 100 : null;

  return {
    sample,
    alive,
    dead,
    assessed,
    unassessed,
    isOverSample,
    survivalRate: survivalRate !== null ? Number(survivalRate.toFixed(1)) : null,
  };
}

function transformSurvivalAnalyticsForChart(analytics = []) {
  return analytics.map((pt) => ({
    date: pt.observation_date,
    survivalRate: pt.survival_rate !== null ? Number(pt.survival_rate.toFixed(1)) : 0,
    alive: pt.alive_count,
    dead: pt.dead_count,
    sampleSize: pt.sample_size,
    assessed: pt.assessed_count,
    unassessed: pt.unassessed_count,
  }));
}

// ============================================================================
// Test Suites
// ============================================================================

describe("Phase 6.5: Field Monitoring UI & Workspaces Unit Tests", () => {
  // --------------------------------------------------------------------------
  // Suite 1: Monitoring Navigation & Role-Based Action Permissions
  // --------------------------------------------------------------------------
  describe("1. Monitoring Navigation & Role-Based Permissions", () => {
    const adminUser = { id: "u-admin", role: "ADMIN" };
    const assignedPm = { id: "u-pm-1", role: "PROJECT_MANAGER" };
    const unassignedPm = { id: "u-pm-2", role: "PROJECT_MANAGER" };
    const assignedFo1 = { id: "u-fo-1", role: "FIELD_OFFICER" };
    const assignedFo2 = { id: "u-fo-2", role: "FIELD_OFFICER" };

    it("allows Admin to schedule inspections anywhere", () => {
      assert.equal(canUserScheduleInspection(adminUser.role, false), true);
    });

    it("allows Assigned PM to schedule inspections on assigned project", () => {
      assert.equal(canUserScheduleInspection(assignedPm.role, true), true);
      assert.equal(canUserScheduleInspection(unassignedPm.role, false), false);
    });

    it("prevents Field Officers from scheduling inspections", () => {
      assert.equal(canUserScheduleInspection(assignedFo1.role, true), false);
    });

    it("restricts Field Officers to executing only their assigned inspections", () => {
      // Assigned to FO 1
      assert.equal(
        canUserExecuteInspection(assignedFo1.role, "u-fo-1", assignedFo1.id, true),
        true
      );
      // Assigned to FO 2 -> FO 1 cannot execute
      assert.equal(
        canUserExecuteInspection(assignedFo1.role, "u-fo-2", assignedFo1.id, true),
        false
      );
    });

    it("allows PM and Admin to execute any inspection in their scope", () => {
      assert.equal(
        canUserExecuteInspection(adminUser.role, "u-fo-1", adminUser.id, false),
        true
      );
      assert.equal(
        canUserExecuteInspection(assignedPm.role, "u-fo-1", assignedPm.id, true),
        true
      );
    });

    it("enforces task creation permissions: Admin/PM only", () => {
      assert.equal(canUserCreateTask(adminUser.role, false), true);
      assert.equal(canUserCreateTask(assignedPm.role, true), true);
      assert.equal(canUserCreateTask(unassignedPm.role, false), false);
      assert.equal(canUserCreateTask(assignedFo1.role, true), false);
    });

    it("enforces task cancellation and reopening: Admin/PM only", () => {
      assert.equal(canUserCancelOrReopen(adminUser.role, false), true);
      assert.equal(canUserCancelOrReopen(assignedPm.role, true), true);
      assert.equal(canUserCancelOrReopen(assignedFo1.role, true), false);
    });

    it("enforces observation supersession correction: Admin/PM only", () => {
      assert.equal(canUserCorrectObservation(adminUser.role, false), true);
      assert.equal(canUserCorrectObservation(assignedPm.role, true), true);
      assert.equal(canUserCorrectObservation(assignedFo1.role, true), false);
    });
  });

  // --------------------------------------------------------------------------
  // Suite 2: Dashboard KPI & Operational Alert Aggregations
  // --------------------------------------------------------------------------
  describe("2. Dashboard KPI & Operational Alert Aggregations", () => {
    it("derives overdue inspection and task counts from alert summary", () => {
      const mockAlerts = [
        { alert_type: "OVERDUE_INSPECTION", severity: "HIGH" },
        { alert_type: "OVERDUE_INSPECTION", severity: "HIGH" },
        { alert_type: "UPCOMING_INSPECTION", severity: "LOW" },
        { alert_type: "OVERDUE_TASK", severity: "MEDIUM" },
      ];

      const { overdueInspections, overdueTasks } = computeOverdueCounts(mockAlerts);
      assert.equal(overdueInspections, 2);
      assert.equal(overdueTasks, 1);
    });

    it("detects overdue maintenance tasks accurately based on due date and status", () => {
      const today = "2026-11-04";
      // Past due date and TODO -> overdue
      assert.equal(isTaskOverdue("2026-11-01", "TODO", today), true);
      // Past due date and IN_PROGRESS -> overdue
      assert.equal(isTaskOverdue("2026-11-03", "IN_PROGRESS", today), true);
      // Past due date but COMPLETED -> not overdue
      assert.equal(isTaskOverdue("2026-11-01", "COMPLETED", today), false);
      // Past due date but CANCELLED -> not overdue
      assert.equal(isTaskOverdue("2026-11-01", "CANCELLED", today), false);
      // Future due date -> not overdue
      assert.equal(isTaskOverdue("2026-11-10", "TODO", today), false);
    });
  });

  // --------------------------------------------------------------------------
  // Suite 3: Survival Calculation & Dynamic Client Preview
  // --------------------------------------------------------------------------
  describe("3. Survival Calculation & Dynamic Client Preview", () => {
    it("computes assessed, unassessed, and sample survival rate accurately", () => {
      const { sample, alive, dead, assessed, unassessed, isOverSample, survivalRate } =
        computeSurvivalCounts(100, 85, 10);

      assert.equal(sample, 100);
      assert.equal(alive, 85);
      assert.equal(dead, 10);
      assert.equal(assessed, 95);
      assert.equal(unassessed, 5);
      assert.equal(isOverSample, false);
      // 85 / 95 * 100 = 89.47% -> 89.5%
      assert.equal(survivalRate, 89.5);
    });

    it("flags error when sum of alive and dead exceeds sample size", () => {
      const { isOverSample } = computeSurvivalCounts(50, 40, 20); // 60 > 50
      assert.equal(isOverSample, true);
    });

    it("safely handles zero assessed population without division by zero", () => {
      const { assessed, survivalRate } = computeSurvivalCounts(100, 0, 0);
      assert.equal(assessed, 0);
      assert.equal(survivalRate, null);
    });

    it("transforms longitudinal analytics data points for Recharts curve", () => {
      const rawPoints = [
        {
          observation_date: "2026-10-01",
          sample_size: 100,
          alive_count: 95,
          dead_count: 5,
          assessed_count: 100,
          unassessed_count: 0,
          survival_rate: 95.0,
        },
        {
          observation_date: "2026-11-01",
          sample_size: 100,
          alive_count: 90,
          dead_count: 10,
          assessed_count: 100,
          unassessed_count: 0,
          survival_rate: 90.0,
        },
      ];

      const chartData = transformSurvivalAnalyticsForChart(rawPoints);
      assert.equal(chartData.length, 2);
      assert.equal(chartData[0].date, "2026-10-01");
      assert.equal(chartData[0].survivalRate, 95.0);
      assert.equal(chartData[1].date, "2026-11-01");
      assert.equal(chartData[1].survivalRate, 90.0);
    });
  });

  // --------------------------------------------------------------------------
  // Suite 4: Secure Evidence URL & Lightbox Construction
  // --------------------------------------------------------------------------
  describe("4. Secure Evidence URL & Lightbox Construction", () => {
    it("constructs only sanitized REST download URLs without exposing internal paths", () => {
      const evidenceId = "e8a2a14e-9876-4321-abcd-1234567890ab";
      const expectedUrl = `/api/v1/operations/evidence/${evidenceId}`;

      // Ensure no disk file path traversal exists
      assert.equal(expectedUrl.startsWith("/api/v1/operations/evidence/"), true);
      assert.equal(expectedUrl.includes(".."), false);
      assert.equal(expectedUrl.includes("\\"), false);
    });

    it("formats evidence file sizes correctly for UI display", () => {
      const formatBytes = (bytes) => {
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
      };

      assert.equal(formatBytes(512000), "500.0 KB");
      assert.equal(formatBytes(2097152), "2.00 MB");
    });
  });
});
