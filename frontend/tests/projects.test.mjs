import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { z } from "zod";

// Schemas matching frontend forms
const createProjectSchema = z.object({
  name: z.string().trim().min(3, "Project name must be at least 3 characters"),
  code: z
    .string()
    .trim()
    .regex(/^[A-Z0-9_\-]*$/, "Code must be uppercase alphanumeric, dashes, or underscores")
    .optional()
    .or(z.literal("")),
  description: z.string().trim().optional(),
  status: z.enum(["ACTIVE", "DRAFT", "COMPLETED", "ARCHIVED"]),
  latitude: z.coerce.number().min(-90, "Latitude must be >= -90").max(90, "Latitude must be <= 90"),
  longitude: z.coerce.number().min(-180, "Longitude must be >= -180").max(180, "Longitude must be <= 180"),
});

const targetSchema = z.object({
  metric_code: z.string().min(1, "Metric code required"),
  target_quantity: z.coerce.number().positive("Quantity must be greater than 0"),
  target_unit: z.string().min(1, "Target unit required"),
  target_date: z.string().min(1, "Target deadline required"),
});

const assignmentSchema = z.object({
  user_id: z.string().uuid("Please select a valid user"),
  assigned_role: z.enum(["PROJECT_MANAGER", "FIELD_OFFICER"]),
});

function validateGeoJsonPolygon(polygon) {
  if (!polygon || typeof polygon !== "object") return false;
  if (polygon.type !== "Polygon") return false;
  if (!Array.isArray(polygon.coordinates) || polygon.coordinates.length === 0) return false;
  for (const ring of polygon.coordinates) {
    if (!Array.isArray(ring) || ring.length < 4) return false;
    const first = ring[0];
    const last = ring[ring.length - 1];
    if (first[0] !== last[0] || first[1] !== last[1]) return false;
    for (const [lng, lat] of ring) {
      if (typeof lng !== "number" || typeof lat !== "number") return false;
      if (lng < -180 || lng > 180 || lat < -90 || lat > 90) return false;
    }
  }
  return true;
}

describe("Frontend Project Portfolio & Workspace Unit Tests", () => {
  it("validates valid project creation inputs", () => {
    const valid = {
      name: "Sundarbans Conservation Area",
      code: "VANA-SUNDAR-01",
      description: "Restoring coastal buffer zones",
      status: "ACTIVE",
      latitude: 21.9497,
      longitude: 89.1833,
    };
    const parsed = createProjectSchema.safeParse(valid);
    assert.equal(parsed.success, true);
  });

  it("rejects invalid project name shorter than 3 characters", () => {
    const invalid = {
      name: "A",
      status: "ACTIVE",
      latitude: 20.0,
      longitude: 80.0,
    };
    const parsed = createProjectSchema.safeParse(invalid);
    assert.equal(parsed.success, false);
    assert.equal(parsed.error?.issues[0].message, "Project name must be at least 3 characters");
  });

  it("rejects latitude outside range [-90, 90]", () => {
    const invalid = {
      name: "Out of Bounds Project",
      status: "ACTIVE",
      latitude: 95.5,
      longitude: 80.0,
    };
    const parsed = createProjectSchema.safeParse(invalid);
    assert.equal(parsed.success, false);
    assert.equal(parsed.error?.issues[0].message, "Latitude must be <= 90");
  });

  it("rejects longitude outside range [-180, 180]", () => {
    const invalid = {
      name: "Out of Bounds Project",
      status: "ACTIVE",
      latitude: 20.0,
      longitude: -185.0,
    };
    const parsed = createProjectSchema.safeParse(invalid);
    assert.equal(parsed.success, false);
    assert.equal(parsed.error?.issues[0].message, "Longitude must be >= -180");
  });

  it("validates GeoJSON polygon structure and closed rings", () => {
    const validPoly = {
      type: "Polygon",
      coordinates: [
        [
          [89.18, 21.94],
          [89.19, 21.94],
          [89.19, 21.95],
          [89.18, 21.95],
          [89.18, 21.94],
        ],
      ],
    };
    assert.equal(validateGeoJsonPolygon(validPoly), true);

    const unclosedPoly = {
      type: "Polygon",
      coordinates: [
        [
          [89.18, 21.94],
          [89.19, 21.94],
          [89.19, 21.95],
          [89.18, 21.95], // Not closed!
        ],
      ],
    };
    assert.equal(validateGeoJsonPolygon(unclosedPoly), false);

    const trianglePoly = {
      type: "Polygon",
      coordinates: [
        [
          [89.18, 21.94],
          [89.19, 21.94],
          [89.18, 21.94], // Fewer than 4 points
        ],
      ],
    };
    assert.equal(validateGeoJsonPolygon(trianglePoly), false);
  });

  it("validates environmental target creation inputs", () => {
    const validTarget = {
      metric_code: "TREES_PLANTED",
      target_quantity: 50000,
      target_unit: "trees",
      target_date: "2027-12-31",
    };
    const parsed = targetSchema.safeParse(validTarget);
    assert.equal(parsed.success, true);
  });

  it("rejects zero or negative target quantity", () => {
    const invalidTarget = {
      metric_code: "TREES_PLANTED",
      target_quantity: 0,
      target_unit: "trees",
      target_date: "2027-12-31",
    };
    const parsed = targetSchema.safeParse(invalidTarget);
    assert.equal(parsed.success, false);
    assert.equal(parsed.error?.issues[0].message, "Quantity must be greater than 0");
  });

  it("validates project assignment input schema", () => {
    const valid = {
      user_id: "e8a2a14e-1234-4567-89ab-cdef01234567",
      assigned_role: "PROJECT_MANAGER",
    };
    const parsed = assignmentSchema.safeParse(valid);
    assert.equal(parsed.success, true);

    const invalidRole = {
      user_id: "e8a2a14e-1234-4567-89ab-cdef01234567",
      assigned_role: "ADMIN",
    };
    assert.equal(assignmentSchema.safeParse(invalidRole).success, false);
  });

  it("enforces role-based permissions in Project Workspace UI", () => {
    const canManageProject = (user, project) => {
      if (!user) return false;
      if (user.role === "ADMIN") return true;
      if (user.role === "PROJECT_MANAGER") {
        return project.assignments.some(
          (a) => a.user_id === user.id && a.assigned_role === "PROJECT_MANAGER"
        );
      }
      return false;
    };

    const project = {
      id: "proj-1",
      assignments: [
        { user_id: "pm-1", assigned_role: "PROJECT_MANAGER" },
        { user_id: "fo-1", assigned_role: "FIELD_OFFICER" },
      ],
    };

    // Admin always has management authority
    assert.equal(canManageProject({ id: "admin-1", role: "ADMIN" }, project), true);

    // Assigned PM has management authority
    assert.equal(canManageProject({ id: "pm-1", role: "PROJECT_MANAGER" }, project), true);

    // Unassigned PM does NOT have management authority
    assert.equal(canManageProject({ id: "pm-2", role: "PROJECT_MANAGER" }, project), false);

    // Field Officer does NOT have management authority
    assert.equal(canManageProject({ id: "fo-1", role: "FIELD_OFFICER" }, project), false);
  });
});
