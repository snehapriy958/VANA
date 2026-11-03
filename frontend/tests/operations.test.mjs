import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { z } from "zod";

// Schemas matching frontend forms
const activitySubmissionSchema = z.object({
  project_id: z.string().uuid("Please select a target project"),
  metric_code: z.string().min(1, "Metric code is required"),
  quantity: z.coerce.number().positive("Quantity must be greater than 0"),
  unit: z.string().min(1, "Unit is required"),
  activity_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Invalid date format (YYYY-MM-DD)"),
  latitude: z.coerce.number().min(-90).max(90).nullable().optional(),
  longitude: z.coerce.number().min(-180).max(180).nullable().optional(),
  gps_accuracy_meters: z.coerce.number().nonnegative().nullable().optional(),
  field_notes: z.string().optional(),
});

const amendmentSchema = z.object({
  quantity: z.coerce.number().positive("Amended quantity must be greater than 0"),
  activity_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Invalid date format"),
  amendment_reason: z.string().min(1, "Amendment reason is required"),
  field_notes: z.string().optional(),
});

const rejectionSchema = z.object({
  decision: z.literal("REJECTED"),
  rejection_reason_code: z.enum([
    "INSUFFICIENT_EVIDENCE",
    "COORDINATES_MISMATCH",
    "INCORRECT_UNIT_OR_QUANTITY",
    "DUPLICATE_SUBMISSION",
    "DATA_ENTRY_ERROR",
  ]),
  review_notes: z.string().trim().min(3, "Review notes must contain at least 3 characters"),
});

// Anti-Self-Verification logic helper (matching frontend guards and backend Rule 5)
function canUserVerifyActivity(user, activity, userAssignedProjectIds = []) {
  if (!user || !activity) return false;
  // Rule 5: Verifier cannot be the author
  if (user.id === activity.created_by_id) return false;
  // Field officers cannot verify
  if (user.role === "FIELD_OFFICER") return false;
  // Admins can verify all
  if (user.role === "ADMIN") return true;
  // PMs must be assigned to the project
  if (user.role === "PROJECT_MANAGER") {
    return userAssignedProjectIds.includes(activity.project_id);
  }
  return false;
}

// Net adjustment calculation helper
function calculateNetPendingAdjustment(currentQuantity, activeVerifiedQuantity) {
  const current = Number(currentQuantity);
  const active = activeVerifiedQuantity !== null && activeVerifiedQuantity !== undefined
    ? Number(activeVerifiedQuantity)
    : 0;
  return current - active;
}

describe("Frontend Field Operations & Verification Unit Tests", () => {
  it("validates valid field activity submission inputs", () => {
    const valid = {
      project_id: "e8a2a14e-9876-4321-abcd-1234567890ab",
      metric_code: "TREES_PLANTED",
      quantity: 250,
      unit: "trees",
      activity_date: "2026-11-02",
      latitude: 21.9512,
      longitude: 89.184,
      gps_accuracy_meters: 4.2,
      field_notes: "Planted Rhizophora mucronata seedlings.",
    };
    const parsed = activitySubmissionSchema.safeParse(valid);
    assert.equal(parsed.success, true);
  });

  it("rejects zero or negative quantities in activity submission", () => {
    const zeroQty = {
      project_id: "e8a2a14e-9876-4321-abcd-1234567890ab",
      metric_code: "TREES_PLANTED",
      quantity: 0,
      unit: "trees",
      activity_date: "2026-11-02",
    };
    assert.equal(activitySubmissionSchema.safeParse(zeroQty).success, false);

    const negQty = {
      ...zeroQty,
      quantity: -50,
    };
    assert.equal(activitySubmissionSchema.safeParse(negQty).success, false);
  });

  it("rejects invalid GPS coordinates outside bounds", () => {
    const invalidLat = {
      project_id: "e8a2a14e-9876-4321-abcd-1234567890ab",
      metric_code: "TREES_PLANTED",
      quantity: 100,
      unit: "trees",
      activity_date: "2026-11-02",
      latitude: 95.0, // Invalid > 90
      longitude: 89.184,
    };
    assert.equal(activitySubmissionSchema.safeParse(invalidLat).success, false);
  });

  it("validates amendment submission requirements", () => {
    const validAmend = {
      quantity: 160,
      activity_date: "2026-11-03",
      amendment_reason: "Additional seedlings planted in adjacent row",
      field_notes: "Verified by GPS survey",
    };
    assert.equal(amendmentSchema.safeParse(validAmend).success, true);

    const missingReason = {
      quantity: 160,
      activity_date: "2026-11-03",
      amendment_reason: "",
    };
    assert.equal(amendmentSchema.safeParse(missingReason).success, false);
  });

  it("calculates positive and negative net pending adjustments correctly", () => {
    // Initial activity: 100 claimed, 0 verified -> net +100
    assert.equal(calculateNetPendingAdjustment(100, 0), 100);

    // Amendment up: 160 amended, 100 verified -> net +60
    assert.equal(calculateNetPendingAdjustment(160, 100), 60);

    // Amendment down: 80 amended, 100 verified -> net -20
    assert.equal(calculateNetPendingAdjustment(80, 100), -20);
  });

  it("enforces Rule 5: Anti-Self-Verification Gate in UI authorization logic", () => {
    const activity = {
      id: "act-1",
      project_id: "proj-100",
      created_by_id: "user-author-99",
    };

    const authorUser = {
      id: "user-author-99",
      role: "PROJECT_MANAGER",
    };

    const independentAdmin = {
      id: "user-admin-1",
      role: "ADMIN",
    };

    const assignedPM = {
      id: "user-pm-2",
      role: "PROJECT_MANAGER",
    };

    const unassignedPM = {
      id: "user-pm-3",
      role: "PROJECT_MANAGER",
    };

    const fieldOfficer = {
      id: "user-fo-4",
      role: "FIELD_OFFICER",
    };

    // Author cannot verify their own submission (Rule 5 violation)
    assert.equal(canUserVerifyActivity(authorUser, activity, ["proj-100"]), false);

    // Field Officer cannot verify any submission
    assert.equal(canUserVerifyActivity(fieldOfficer, activity, ["proj-100"]), false);

    // Unassigned PM cannot verify
    assert.equal(canUserVerifyActivity(unassignedPM, activity, ["proj-OTHER"]), false);

    // Independent Admin can verify
    assert.equal(canUserVerifyActivity(independentAdmin, activity), true);

    // Assigned independent PM can verify
    assert.equal(canUserVerifyActivity(assignedPM, activity, ["proj-100"]), true);
  });

  it("validates rejection reason codes and mandatory feedback notes", () => {
    const validRejection = {
      decision: "REJECTED",
      rejection_reason_code: "INSUFFICIENT_EVIDENCE",
      review_notes: "Photo blur prevents seedling verification.",
    };
    assert.equal(rejectionSchema.safeParse(validRejection).success, true);

    const invalidCode = {
      decision: "REJECTED",
      rejection_reason_code: "UNKNOWN_REASON",
      review_notes: "Invalid code",
    };
    assert.equal(rejectionSchema.safeParse(invalidCode).success, false);

    const emptyNotes = {
      decision: "REJECTED",
      rejection_reason_code: "INSUFFICIENT_EVIDENCE",
      review_notes: "   ",
    };
    assert.equal(rejectionSchema.safeParse(emptyNotes).success, false);
  });
});
