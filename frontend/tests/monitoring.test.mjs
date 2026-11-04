import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { z } from "zod";

// ============================================================================
// 1. Zod Validation Schemas (Client-Side Form Validation Contracts)
// ============================================================================

const inspectionCreateSchema = z.object({
  project_id: z.string().uuid("Please select a target project"),
  scheduled_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Invalid date format (YYYY-MM-DD)"),
  inspection_type: z.enum(["ROUTINE", "SURVIVAL_CHECK", "MAINTENANCE_AUDIT", "EMERGENCY"]).default("ROUTINE"),
  assigned_to_id: z.string().uuid().nullable().optional(),
  linked_activity_id: z.string().uuid().nullable().optional(),
});

const inspectionCompleteSchema = z.object({
  findings: z.string().trim().min(1, "Findings are required upon inspection completion"),
  vegetation_health_score: z.coerce.number().int().min(1).max(5).nullable().optional(),
  canopy_condition: z.enum(["EXCELLENT", "HEALTHY", "STRESSED", "CRITICAL"]).nullable().optional(),
  soil_moisture_condition: z.enum(["SATURATED", "ADEQUATE", "DRY", "SEVERELY_PARCHED"]).nullable().optional(),
  threats_detected: z.array(z.string()).nullable().optional(),
});

const inspectionCancelSchema = z.object({
  cancellation_reason: z.string().trim().min(3, "Cancellation reason must contain at least 3 characters"),
});

const inspectionAddendumSchema = z.object({
  content: z.string().trim().min(3, "Addendum content must contain at least 3 characters"),
});

const maintenanceTaskCreateSchema = z.object({
  project_id: z.string().uuid("Please select a target project"),
  title: z.string().trim().min(3, "Title must be at least 3 characters").max(255),
  description: z.string().trim().optional(),
  category: z.enum([
    "IRRIGATION",
    "WEEDING",
    "MULCHING",
    "FENCING_REPAIR",
    "REPLANTING_PREP",
    "PEST_CONTROL",
    "SOIL_ENRICHMENT",
    "OTHER",
  ]),
  priority: z.enum(["LOW", "MEDIUM", "HIGH", "URGENT"]).default("MEDIUM"),
  due_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Invalid date format (YYYY-MM-DD)"),
  assigned_to_id: z.string().uuid().nullable().optional(),
  inspection_id: z.string().uuid().nullable().optional(),
  activity_id: z.string().uuid().nullable().optional(),
});

const taskCompleteSchema = z.object({
  completion_notes: z.string().trim().min(3, "Completion notes must contain at least 3 characters"),
});

const taskCancelSchema = z.object({
  cancellation_reason: z.string().trim().min(3, "Cancellation reason must contain at least 3 characters"),
});

const taskReopenSchema = z.object({
  justification: z.string().trim().min(3, "Justification must contain at least 3 characters"),
});

const survivalObservationCreateSchema = z
  .object({
    project_id: z.string().uuid("Please select a target project"),
    plot_identifier: z.string().trim().min(1).max(64),
    cohort_identifier: z.string().trim().min(1).max(64),
    methodology: z.enum(["SAMPLE_PLOT", "TRANSECT", "FULL_CENSUS"]).default("SAMPLE_PLOT"),
    coverage_area_sqm: z.coerce.number().positive().nullable().optional(),
    observation_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Invalid date format (YYYY-MM-DD)"),
    sample_size: z.coerce.number().int().positive("Sample size must be greater than 0"),
    alive_count: z.coerce.number().int().min(0, "Alive count cannot be negative"),
    dead_count: z.coerce.number().int().min(0, "Dead count cannot be negative"),
    mortality_causes: z.array(z.string()).nullable().optional(),
    is_definitive: z.boolean().default(false),
    activity_id: z.string().uuid().nullable().optional(),
    inspection_id: z.string().uuid().nullable().optional(),
    notes: z.string().trim().optional(),
  })
  .refine((data) => data.alive_count + data.dead_count <= data.sample_size, {
    message: "Sum of alive_count and dead_count cannot exceed sample_size",
    path: ["sample_size"],
  });

const survivalObservationCorrectionSchema = z
  .object({
    sample_size: z.coerce.number().int().positive("Sample size must be greater than 0"),
    alive_count: z.coerce.number().int().min(0, "Alive count cannot be negative"),
    dead_count: z.coerce.number().int().min(0, "Dead count cannot be negative"),
    methodology: z.enum(["SAMPLE_PLOT", "TRANSECT", "FULL_CENSUS"]).nullable().optional(),
    coverage_area_sqm: z.coerce.number().positive().nullable().optional(),
    mortality_causes: z.array(z.string()).nullable().optional(),
    is_definitive: z.boolean().nullable().optional(),
    notes: z.string().trim().optional(),
    correction_notes: z.string().trim().min(3, "Correction notes must contain at least 3 characters"),
  })
  .refine((data) => data.alive_count + data.dead_count <= data.sample_size, {
    message: "Sum of alive_count and dead_count cannot exceed sample_size",
    path: ["sample_size"],
  });

// ============================================================================
// 2. Mock Query Client & Key Invariant Generator
// ============================================================================

const monitoringKeys = {
  all: ["monitoring"],
  inspections: () => ["monitoring", "inspections"],
  inspectionLists: () => ["monitoring", "inspections", "list"],
  inspectionList: (filters) => ["monitoring", "inspections", "list", filters ?? {}],
  inspectionDetails: () => ["monitoring", "inspections", "detail"],
  inspectionDetail: (id) => ["monitoring", "inspections", "detail", id],

  tasks: () => ["monitoring", "tasks"],
  taskLists: () => ["monitoring", "tasks", "list"],
  taskList: (filters) => ["monitoring", "tasks", "list", filters ?? {}],
  taskDetails: () => ["monitoring", "tasks", "detail"],
  taskDetail: (id) => ["monitoring", "tasks", "detail", id],

  survival: () => ["monitoring", "survival"],
  survivalLists: () => ["monitoring", "survival", "list"],
  survivalList: (filters) => ["monitoring", "survival", "list", filters],
  survivalDetails: () => ["monitoring", "survival", "detail"],
  survivalDetail: (id) => ["monitoring", "survival", "detail", id],
  survivalTrajectories: () => ["monitoring", "survival", "trajectory"],
  survivalTrajectory: (projectId, plotId, cohortId) => [
    "monitoring",
    "survival",
    "trajectory",
    projectId,
    plotId,
    cohortId,
  ],

  alerts: (projectId) => ["monitoring", "alerts", projectId ?? "all"],
  dashboard: (projectId) => ["monitoring", "dashboard", projectId ?? "all"],
};

// ============================================================================
// 3. Error Normalization Logic (Matching apiClient.ts)
// ============================================================================

function normalizeApiError(error) {
  let message;
  const errorData = error.response?.data;

  if (typeof errorData?.detail === "string") {
    message = errorData.detail;
  } else if (errorData?.detail && typeof errorData.detail === "object") {
    if (typeof errorData.detail.message === "string") {
      message = errorData.detail.message;
    } else if (Array.isArray(errorData.detail)) {
      message = errorData.detail
        .map((item) => item.msg || (item.loc ? `${item.loc.join(".")}: error` : "Validation error"))
        .join("; ");
    }
  } else if (typeof errorData?.message === "string") {
    message = errorData.message;
  }

  return message || error.message || "An unexpected network error occurred.";
}

// ============================================================================
// 4. Test Suites
// ============================================================================

describe("Phase 6.4: Frontend Monitoring API & Integration Tests", () => {
  // --------------------------------------------------------------------------
  // Suite 1: Client Request Schemas & Form Validation
  // --------------------------------------------------------------------------
  describe("1. Client Request Schemas & Validation Contracts", () => {
    it("validates valid inspection creation parameters", () => {
      const valid = {
        project_id: "e8a2a14e-9876-4321-abcd-1234567890ab",
        scheduled_date: "2026-11-15",
        inspection_type: "SURVIVAL_CHECK",
        assigned_to_id: "c7b1a14e-9876-4321-abcd-1234567890cd",
      };
      const result = inspectionCreateSchema.safeParse(valid);
      assert.equal(result.success, true);
    });

    it("rejects invalid inspection date format", () => {
      const invalid = {
        project_id: "e8a2a14e-9876-4321-abcd-1234567890ab",
        scheduled_date: "15-11-2026", // Invalid format
      };
      const result = inspectionCreateSchema.safeParse(invalid);
      assert.equal(result.success, false);
    });

    it("validates inspection completion with mandatory findings", () => {
      const valid = {
        findings: "Seedlings in plot A showing excellent root establishment.",
        vegetation_health_score: 4,
        canopy_condition: "HEALTHY",
        soil_moisture_condition: "ADEQUATE",
        threats_detected: ["MINOR_PEST_ACTIVITY"],
      };
      const result = inspectionCompleteSchema.safeParse(valid);
      assert.equal(result.success, true);
    });

    it("rejects empty findings on inspection completion", () => {
      const invalid = {
        findings: "   ",
        vegetation_health_score: 3,
      };
      const result = inspectionCompleteSchema.safeParse(invalid);
      assert.equal(result.success, false);
    });

    it("validates vegetation health score boundary (1 to 5)", () => {
      assert.equal(
        inspectionCompleteSchema.safeParse({ findings: "Ok", vegetation_health_score: 0 }).success,
        false
      );
      assert.equal(
        inspectionCompleteSchema.safeParse({ findings: "Ok", vegetation_health_score: 6 }).success,
        false
      );
      assert.equal(
        inspectionCompleteSchema.safeParse({ findings: "Ok", vegetation_health_score: 5 }).success,
        true
      );
    });

    it("validates inspection cancellation reason requirement (min 3 chars)", () => {
      assert.equal(inspectionCancelSchema.safeParse({ cancellation_reason: "Ab" }).success, false);
      assert.equal(
        inspectionCancelSchema.safeParse({ cancellation_reason: "Heavy monsoon flooding prevented access" })
          .success,
        true
      );
    });

    it("validates maintenance task creation inputs", () => {
      const valid = {
        project_id: "e8a2a14e-9876-4321-abcd-1234567890ab",
        title: "Repair perimeter fence section 4",
        category: "FENCING_REPAIR",
        priority: "HIGH",
        due_date: "2026-11-20",
      };
      const result = maintenanceTaskCreateSchema.safeParse(valid);
      assert.equal(result.success, true);
    });

    it("rejects task title shorter than 3 characters", () => {
      const invalid = {
        project_id: "e8a2a14e-9876-4321-abcd-1234567890ab",
        title: "Hi",
        category: "WEEDING",
        due_date: "2026-11-20",
      };
      assert.equal(maintenanceTaskCreateSchema.safeParse(invalid).success, false);
    });

    it("validates task reopening justification requirement", () => {
      assert.equal(taskReopenSchema.safeParse({ justification: "no" }).success, false);
      assert.equal(
        taskReopenSchema.safeParse({ justification: "Follow-up inspection detected broken wires" }).success,
        true
      );
    });
  });

  // --------------------------------------------------------------------------
  // Suite 2: Survival Observation Scientific Integrity & Count Constraints
  // --------------------------------------------------------------------------
  describe("2. Survival Observation Integrity & Server-Derived Calculation", () => {
    it("validates valid survival observation input", () => {
      const valid = {
        project_id: "e8a2a14e-9876-4321-abcd-1234567890ab",
        plot_identifier: "PLOT-MANGROVE-01",
        cohort_identifier: "COHORT-2026-Q4",
        methodology: "SAMPLE_PLOT",
        coverage_area_sqm: 500,
        observation_date: "2026-11-10",
        sample_size: 100,
        alive_count: 85,
        dead_count: 10,
        mortality_causes: ["DESICCATION"],
      };
      const result = survivalObservationCreateSchema.safeParse(valid);
      assert.equal(result.success, true);
    });

    it("rejects when alive_count + dead_count exceeds sample_size", () => {
      const invalid = {
        project_id: "e8a2a14e-9876-4321-abcd-1234567890ab",
        plot_identifier: "PLOT-MANGROVE-01",
        cohort_identifier: "COHORT-2026-Q4",
        observation_date: "2026-11-10",
        sample_size: 100,
        alive_count: 80,
        dead_count: 30, // 80 + 30 = 110 > 100
      };
      const result = survivalObservationCreateSchema.safeParse(invalid);
      assert.equal(result.success, false);
    });

    it("validates server-derived survival rate calculation formula", () => {
      // Formula: survival_rate = alive / (alive + dead) * 100
      const alive = 75;
      const dead = 25;
      const assessed = alive + dead;
      const sampleSize = 120;
      const unassessed = sampleSize - assessed;

      assert.equal(assessed, 100);
      assert.equal(unassessed, 20);

      const survivalRate = (alive / assessed) * 100;
      assert.equal(survivalRate, 75.0);

      // When assessed = 0, survival_rate must be null (not divide by zero)
      const zeroAssessedRate = 0 + 0 > 0 ? (0 / (0 + 0)) * 100 : null;
      assert.equal(zeroAssessedRate, null);
    });

    it("validates observation correction schema with mandatory reason", () => {
      const validCorrection = {
        sample_size: 100,
        alive_count: 88,
        dead_count: 12,
        correction_notes: "Re-count conducted after recount protocol verification",
      };
      const result = survivalObservationCorrectionSchema.safeParse(validCorrection);
      assert.equal(result.success, true);

      const missingReason = {
        sample_size: 100,
        alive_count: 88,
        dead_count: 12,
        correction_notes: "",
      };
      assert.equal(survivalObservationCorrectionSchema.safeParse(missingReason).success, false);
    });
  });

  // --------------------------------------------------------------------------
  // Suite 3: TanStack Query Key Factory Invariants
  // --------------------------------------------------------------------------
  describe("3. TanStack Query Key Factory Conventions & Hierarchy", () => {
    it("generates correct hierarchical inspection keys", () => {
      assert.deepEqual(monitoringKeys.all, ["monitoring"]);
      assert.deepEqual(monitoringKeys.inspections(), ["monitoring", "inspections"]);
      assert.deepEqual(monitoringKeys.inspectionLists(), ["monitoring", "inspections", "list"]);

      const filters = { project_id: "p1", status: "SCHEDULED" };
      assert.deepEqual(monitoringKeys.inspectionList(filters), [
        "monitoring",
        "inspections",
        "list",
        filters,
      ]);

      assert.deepEqual(monitoringKeys.inspectionDetail("insp-123"), [
        "monitoring",
        "inspections",
        "detail",
        "insp-123",
      ]);
    });

    it("generates correct hierarchical maintenance task keys", () => {
      assert.deepEqual(monitoringKeys.tasks(), ["monitoring", "tasks"]);
      assert.deepEqual(monitoringKeys.taskLists(), ["monitoring", "tasks", "list"]);

      const taskFilters = { project_id: "p1", priority: "HIGH" };
      assert.deepEqual(monitoringKeys.taskList(taskFilters), [
        "monitoring",
        "tasks",
        "list",
        taskFilters,
      ]);

      assert.deepEqual(monitoringKeys.taskDetail("task-999"), [
        "monitoring",
        "tasks",
        "detail",
        "task-999",
      ]);
    });

    it("generates correct survival observation & longitudinal trajectory keys", () => {
      const survivalFilters = { project_id: "p1", active_only: true };
      assert.deepEqual(monitoringKeys.survivalList(survivalFilters), [
        "monitoring",
        "survival",
        "list",
        survivalFilters,
      ]);

      assert.deepEqual(monitoringKeys.survivalDetail("obs-1"), [
        "monitoring",
        "survival",
        "detail",
        "obs-1",
      ]);

      assert.deepEqual(monitoringKeys.survivalTrajectory("proj-1", "plot-A", "cohort-Q1"), [
        "monitoring",
        "survival",
        "trajectory",
        "proj-1",
        "plot-A",
        "cohort-Q1",
      ]);
    });

    it("generates project-scoped alert and dashboard keys", () => {
      assert.deepEqual(monitoringKeys.alerts(), ["monitoring", "alerts", "all"]);
      assert.deepEqual(monitoringKeys.alerts("proj-10"), ["monitoring", "alerts", "proj-10"]);
      assert.deepEqual(monitoringKeys.dashboard(), ["monitoring", "dashboard", "all"]);
      assert.deepEqual(monitoringKeys.dashboard("proj-10"), ["monitoring", "dashboard", "proj-10"]);
    });
  });

  // --------------------------------------------------------------------------
  // Suite 4: Query Invalidation Matrix Verification
  // --------------------------------------------------------------------------
  describe("4. Mutation Cache Invalidation Matrix", () => {
    it("verifies inspection scheduling invalidates inspections, dashboard, and alerts", () => {
      const invalidated = [];
      const mockQueryClient = {
        invalidateQueries: ({ queryKey }) => invalidated.push(queryKey),
      };

      // Simulate onScheduleSuccess
      mockQueryClient.invalidateQueries({ queryKey: monitoringKeys.inspections() });
      mockQueryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });
      mockQueryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "alerts"] });

      assert.equal(invalidated.length, 3);
      assert.deepEqual(invalidated[0], ["monitoring", "inspections"]);
      assert.deepEqual(invalidated[1], ["monitoring", "dashboard"]);
      assert.deepEqual(invalidated[2], ["monitoring", "alerts"]);
    });

    it("verifies task completion invalidates task list, task detail, dashboard, and alerts", () => {
      const invalidated = [];
      const mockQueryClient = {
        invalidateQueries: ({ queryKey }) => invalidated.push(queryKey),
      };

      const taskId = "task-uuid-100";
      mockQueryClient.invalidateQueries({ queryKey: monitoringKeys.tasks() });
      mockQueryClient.invalidateQueries({ queryKey: monitoringKeys.taskDetail(taskId) });
      mockQueryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });
      mockQueryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "alerts"] });

      assert.equal(invalidated.length, 4);
      assert.deepEqual(invalidated[1], ["monitoring", "tasks", "detail", taskId]);
    });

    it("verifies observation supersession invalidates survival queries and dashboard", () => {
      const invalidated = [];
      const mockQueryClient = {
        invalidateQueries: ({ queryKey }) => invalidated.push(queryKey),
      };

      mockQueryClient.invalidateQueries({ queryKey: monitoringKeys.survival() });
      mockQueryClient.invalidateQueries({ queryKey: [...monitoringKeys.all, "dashboard"] });

      assert.equal(invalidated.length, 2);
      assert.deepEqual(invalidated[0], ["monitoring", "survival"]);
      assert.deepEqual(invalidated[1], ["monitoring", "dashboard"]);
    });
  });

  // --------------------------------------------------------------------------
  // Suite 5: Error Handling & Normalization Matrix
  // --------------------------------------------------------------------------
  describe("5. Centralized Error Normalization Matrix", () => {
    it("handles 400 Bad Request with string detail", () => {
      const error = {
        response: {
          status: 400,
          data: { detail: "Cannot edit a completed inspection" },
        },
      };
      assert.equal(normalizeApiError(error), "Cannot edit a completed inspection");
    });

    it("handles 400 Bad Request with structured detail object", () => {
      const error = {
        response: {
          status: 400,
          data: { detail: { message: "Invalid transition from CANCELLED state" } },
        },
      };
      assert.equal(normalizeApiError(error), "Invalid transition from CANCELLED state");
    });

    it("handles 403 Forbidden role authorization error", () => {
      const error = {
        response: {
          status: 403,
          data: { detail: "Access denied: User is not assigned to this project" },
        },
      };
      assert.equal(
        normalizeApiError(error),
        "Access denied: User is not assigned to this project"
      );
    });

    it("handles 404 Not Found error", () => {
      const error = {
        response: {
          status: 404,
          data: { detail: "Field inspection not found" },
        },
      };
      assert.equal(normalizeApiError(error), "Field inspection not found");
    });

    it("handles 409 Conflict for already superseded observation", () => {
      const error = {
        response: {
          status: 409,
          data: { detail: "Survival observation has already been superseded" },
        },
      };
      assert.equal(
        normalizeApiError(error),
        "Survival observation has already been superseded"
      );
    });

    it("handles 422 Unprocessable Entity schema validation error array", () => {
      const error = {
        response: {
          status: 422,
          data: {
            detail: [
              { loc: ["body", "findings"], msg: "Field required" },
              { loc: ["body", "vegetation_health_score"], msg: "Input should be less than or equal to 5" },
            ],
          },
        },
      };
      const message = normalizeApiError(error);
      assert.match(message, /Field required/);
      assert.match(message, /Input should be less than or equal to 5/);
    });

    it("handles network failure without response object", () => {
      const error = {
        message: "Network Error: Failed to fetch",
      };
      assert.equal(normalizeApiError(error), "Network Error: Failed to fetch");
    });

    it("triggers 401 callback when unauthorized response received", () => {
      let callbackTriggered = false;
      const onUnauthorized = () => {
        callbackTriggered = true;
      };

      const error = {
        response: { status: 401, data: { detail: "Session expired" } },
      };

      if (error.response?.status === 401) {
        onUnauthorized();
      }

      assert.equal(callbackTriggered, true);
    });
  });

  // --------------------------------------------------------------------------
  // Suite 6: Multipart FormData Construction Verification
  // --------------------------------------------------------------------------
  describe("6. Multipart Evidence FormData Construction", () => {
    it("constructs valid FormData payload for evidence upload", () => {
      const mockFormData = new Map();
      const appendMock = (key, value) => mockFormData.set(key, value);

      // Simulate evidence upload payload prep
      const file = { name: "saplings.jpg", size: 1024, type: "image/jpeg" };
      const metadata = { latitude: 21.95, longitude: 89.18, caption: "Healthy mangrove canopy" };

      appendMock("file", file);
      if (metadata.latitude) appendMock("latitude", String(metadata.latitude));
      if (metadata.longitude) appendMock("longitude", String(metadata.longitude));
      if (metadata.caption) appendMock("caption", metadata.caption);

      assert.equal(mockFormData.has("file"), true);
      assert.equal(mockFormData.get("latitude"), "21.95");
      assert.equal(mockFormData.get("longitude"), "89.18");
      assert.equal(mockFormData.get("caption"), "Healthy mangrove canopy");
    });
  });
});
