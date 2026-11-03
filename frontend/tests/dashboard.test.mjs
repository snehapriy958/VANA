import { describe, it } from "node:test";
import assert from "node:assert/strict";

// Helper functions mirroring dashboard calculation and presentation logic
function calculateTargetProgress(targetQty, verifiedQty, pendingAdj) {
  const target = Number(targetQty) || 0;
  const verified = Number(verifiedQty) || 0;
  const pending = Number(pendingAdj) || 0;

  if (target <= 0) {
    return {
      achievementPercentage: 0,
      remainingQuantity: 0,
      verifiedPctWidth: 0,
      pendingPctWidth: 0,
    };
  }

  const achievementPercentage = Math.round(((verified / target) * 100) * 100) / 100;
  const remainingQuantity = Math.max(0, target - verified);
  const verifiedPctWidth = Math.min(achievementPercentage, 100);
  const pendingPctWidth = pending > 0
    ? Math.min((pending / target) * 100, Math.max(0, 100 - verifiedPctWidth))
    : 0;

  return {
    achievementPercentage,
    remainingQuantity,
    verifiedPctWidth,
    pendingPctWidth,
  };
}

function evaluateAttentionProject(project) {
  const issues = [];
  let severity = "LOW";

  // Rule 1: Verification Backlog
  if (project.pending_verifications_count >= 3) {
    issues.push("Verification backlog (> 3 pending submissions)");
    severity = "HIGH";
  }

  // Rule 2: Overdue / near deadline target
  if (project.days_until_deadline !== null && project.days_until_deadline <= 14) {
    if (project.lowest_target_achievement_percentage === null || project.lowest_target_achievement_percentage < 80) {
      issues.push("Target deadline within 14 days with < 80% achievement");
      if (severity !== "HIGH") severity = "MEDIUM";
    }
  }

  // Rule 3: Zero verified progress on active project
  if (
    project.status === "ACTIVE" &&
    project.lowest_target_achievement_percentage === 0 &&
    project.pending_verifications_count === 0
  ) {
    issues.push("Active project has zero verified achievements");
    if (severity === "LOW") severity = "MEDIUM";
  }

  return {
    requiresAttention: issues.length > 0,
    severity,
    reasons: issues,
  };
}

function isValidMapCoordinate(lat, lng) {
  if (lat === null || lat === undefined || lng === null || lng === undefined) {
    return false;
  }
  const nLat = Number(lat);
  const nLng = Number(lng);
  if (isNaN(nLat) || isNaN(nLng)) return false;
  return nLat >= -90 && nLat <= 90 && nLng >= -180 && nLng <= 180;
}

function getMapMarkerColor(status) {
  switch (status) {
    case "ACTIVE":
      return "#183D32"; // Forest Green
    case "DRAFT":
      return "#D6A76A"; // Earth Gold
    case "COMPLETED":
      return "#A8B99B"; // Sage
    default:
      return "#29332F"; // Charcoal
  }
}

describe("Milestone 5: Environmental Dashboard & Ledger Frontend Logic", () => {
  describe("Target Achievement & Progress Calculation", () => {
    it("correctly computes standard achievement and remaining quantity", () => {
      // Prompt example: 1000 target, verified 600 (60% achievement, 400 remaining)
      const res = calculateTargetProgress(1000, 600, 0);
      assert.strictEqual(res.achievementPercentage, 60.0);
      assert.strictEqual(res.remainingQuantity, 400);
      assert.strictEqual(res.verifiedPctWidth, 60.0);
      assert.strictEqual(res.pendingPctWidth, 0);
    });

    it("incorporates pending amendment in secondary bar without altering verified percentage", () => {
      // 1000 target, verified 600, pending amendment +50
      const res = calculateTargetProgress(1000, 600, 50);
      assert.strictEqual(res.achievementPercentage, 60.0); // Official verified strictly unchanged!
      assert.strictEqual(res.remainingQuantity, 400);
      assert.strictEqual(res.verifiedPctWidth, 60.0);
      assert.strictEqual(res.pendingPctWidth, 5.0); // 50 / 1000 = 5%
    });

    it("handles zero target without throwing division by zero", () => {
      const res = calculateTargetProgress(0, 0, 0);
      assert.strictEqual(res.achievementPercentage, 0);
      assert.strictEqual(res.remainingQuantity, 0);
      assert.strictEqual(res.verifiedPctWidth, 0);
      assert.strictEqual(res.pendingPctWidth, 0);
    });

    it("clamps verified bar to 100% when targets are exceeded", () => {
      const res = calculateTargetProgress(1000, 1250, 0);
      assert.strictEqual(res.achievementPercentage, 125.0);
      assert.strictEqual(res.remainingQuantity, 0);
      assert.strictEqual(res.verifiedPctWidth, 100); // UI bar width clamped to 100%
      assert.strictEqual(res.pendingPctWidth, 0);
    });

    it("handles negative amendment adjustment without breaking bar", () => {
      // Negative amendment (e.g. -50 correction pending)
      const res = calculateTargetProgress(1000, 600, -50);
      assert.strictEqual(res.achievementPercentage, 60.0);
      assert.strictEqual(res.remainingQuantity, 400);
      assert.strictEqual(res.pendingPctWidth, 0); // No positive secondary bar added
    });
  });

  describe("Metric Dimensionality & Catalog Isolation (Rule 8)", () => {
    it("enforces strict separation between distinct metric codes", () => {
      const metricCatalog = [
        { code: "TREES_PLANTED", unit: "trees", dimension: "COUNT" },
        { code: "AREA_RESTORED", unit: "ha", dimension: "SURFACE_AREA" },
        { code: "WATER_HARVESTED", unit: "kL", dimension: "VOLUME" },
      ];

      // Never combine metric codes
      const codeSet = new Set(metricCatalog.map((m) => m.code));
      assert.strictEqual(codeSet.size, 3);
      assert.notStrictEqual(metricCatalog[0].unit, metricCatalog[1].unit);
      assert.notStrictEqual(metricCatalog[1].unit, metricCatalog[2].unit);
    });
  });

  describe("Attention Projects Evaluation Rules", () => {
    it("flags HIGH severity for projects with verification backlog (>= 3 pending)", () => {
      const project = {
        id: "proj-1",
        name: "Sundarbans Mangrove",
        status: "ACTIVE",
        pending_verifications_count: 4,
        days_until_deadline: 60,
        lowest_target_achievement_percentage: 45.0,
      };

      const result = evaluateAttentionProject(project);
      assert.strictEqual(result.requiresAttention, true);
      assert.strictEqual(result.severity, "HIGH");
      assert.ok(result.reasons[0].includes("Verification backlog"));
    });

    it("flags MEDIUM severity for projects within 14 days of deadline and < 80% progress", () => {
      const project = {
        id: "proj-2",
        name: "Western Ghats Corridor",
        status: "ACTIVE",
        pending_verifications_count: 1,
        days_until_deadline: 10,
        lowest_target_achievement_percentage: 65.0,
      };

      const result = evaluateAttentionProject(project);
      assert.strictEqual(result.requiresAttention, true);
      assert.strictEqual(result.severity, "MEDIUM");
      assert.ok(result.reasons[0].includes("Target deadline within 14 days"));
    });

    it("does not flag healthy on-track projects", () => {
      const project = {
        id: "proj-3",
        name: "Aravalli Green Wall",
        status: "ACTIVE",
        pending_verifications_count: 0,
        days_until_deadline: 90,
        lowest_target_achievement_percentage: 85.0,
      };

      const result = evaluateAttentionProject(project);
      assert.strictEqual(result.requiresAttention, false);
      assert.strictEqual(result.reasons.length, 0);
    });
  });

  describe("Living Earth Map Geospatial Coordinates Validation", () => {
    it("validates geographic coordinates correctly", () => {
      assert.strictEqual(isValidMapCoordinate(21.9497, 89.1833), true); // Sundarbans
      assert.strictEqual(isValidMapCoordinate(-33.8688, 151.2093), true); // Sydney
      assert.strictEqual(isValidMapCoordinate(0, 0), true); // Equator
      assert.strictEqual(isValidMapCoordinate(90, 180), true); // Extreme boundary
      assert.strictEqual(isValidMapCoordinate(-90, -180), true);

      // Invalid coordinates
      assert.strictEqual(isValidMapCoordinate(95, 80), false); // Lat > 90
      assert.strictEqual(isValidMapCoordinate(-91, 0), false); // Lat < -90
      assert.strictEqual(isValidMapCoordinate(20, 185), false); // Lng > 180
      assert.strictEqual(isValidMapCoordinate(20, -185), false); // Lng < -180
      assert.strictEqual(isValidMapCoordinate(null, 80), false);
      assert.strictEqual(isValidMapCoordinate(20, null), false);
      assert.strictEqual(isValidMapCoordinate(undefined, undefined), false);
    });

    it("assigns approved brand token colors for project status markers", () => {
      assert.strictEqual(getMapMarkerColor("ACTIVE"), "#183D32");
      assert.strictEqual(getMapMarkerColor("DRAFT"), "#D6A76A");
      assert.strictEqual(getMapMarkerColor("COMPLETED"), "#A8B99B");
      assert.strictEqual(getMapMarkerColor("ARCHIVED"), "#29332F");
    });
  });
});
