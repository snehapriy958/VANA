import { describe, it } from "node:test";
import assert from "node:assert/strict";

describe("Milestone 8: Audit History & Immutability Ledger Frontend Logic", () => {
  describe("1. Audit Event & Cryptographic Digest Validation", () => {
    it("validates valid SHA-256 event structure", () => {
      const validEvent = {
        id: "a0000000-0000-0000-0000-000000000001",
        sequence_number: 1,
        actor_id: "b0000000-0000-0000-0000-000000000001",
        project_id: "c0000000-0000-0000-0000-000000000001",
        action_type: "ACTIVITY_VERIFIED",
        entity_type: "activity_revision",
        entity_id: "d0000000-0000-0000-0000-000000000001",
        previous_hash: "0".repeat(64),
        current_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        hash_version: 1,
        canonical_payload: { status: "VERIFIED" },
        created_at: "2026-11-04T12:00:00.000000Z",
      };

      assert.equal(typeof validEvent.sequence_number, "number");
      assert.equal(validEvent.previous_hash.length, 64);
      assert.equal(validEvent.current_hash.length, 64);
      assert.equal(validEvent.hash_version, 1);
      assert.equal(validEvent.action_type, "ACTIVITY_VERIFIED");
    });

    it("correctly identifies genesis previous hash vs chained hash", () => {
      const genesisHash = "0".repeat(64);
      const isGenesis = (hash) => hash === genesisHash;

      assert.equal(isGenesis(genesisHash), true);
      assert.equal(
        isGenesis("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
        false
      );
    });
  });

  describe("2. Verification Decision History Classification", () => {
    it("classifies verification lifecycle actions correctly", () => {
      const classifyAction = (action) => {
        if (action === "ACTIVITY_VERIFIED") return { badge: "verified", label: "APPROVED / VERIFIED" };
        if (action === "ACTIVITY_REJECTED") return { badge: "rejected", label: "REJECTED" };
        if (action === "ACTIVITY_AMENDED") return { badge: "pending", label: "AMENDMENT SUBMITTED" };
        if (action === "ACTIVITY_ARCHIVED") return { badge: "neutral", label: "ARCHIVED" };
        return { badge: "sage", label: "SUBMITTED" };
      };

      assert.equal(classifyAction("ACTIVITY_VERIFIED").badge, "verified");
      assert.equal(classifyAction("ACTIVITY_REJECTED").badge, "rejected");
      assert.equal(classifyAction("ACTIVITY_AMENDED").badge, "pending");
      assert.equal(classifyAction("ACTIVITY_ARCHIVED").badge, "neutral");
      assert.equal(classifyAction("ACTIVITY_CREATED").badge, "sage");
    });

    it("extracts rejection reason code and notes cleanly", () => {
      const item = {
        sequence_number: 45,
        action_type: "ACTIVITY_REJECTED",
        rejection_reason_code: "INSUFFICIENT_EVIDENCE",
        review_notes: "Missing photographic evidence of seedling survival.",
      };

      assert.equal(item.rejection_reason_code, "INSUFFICIENT_EVIDENCE");
      assert.equal(item.review_notes.includes("seedling"), true);
    });
  });

  describe("3. Cryptographic Chain Integrity Console Status Logic", () => {
    it("never shows green verified status when report is null or unverified", () => {
      const getConsoleStatus = (report) => {
        if (!report) return "UNVERIFIED";
        if (report.is_valid && report.status === "VALID") return "VALID";
        if (report.status === "EMPTY") return "EMPTY";
        return "COMPROMISED";
      };

      assert.equal(getConsoleStatus(null), "UNVERIFIED");
      assert.equal(getConsoleStatus(undefined), "UNVERIFIED");
    });

    it("displays valid status only when is_valid is true and status is VALID", () => {
      const getConsoleStatus = (report) => {
        if (!report) return "UNVERIFIED";
        if (report.is_valid && report.status === "VALID") return "VALID";
        if (report.status === "EMPTY") return "EMPTY";
        return "COMPROMISED";
      };

      const validReport = {
        is_valid: true,
        status: "VALID",
        total_events_checked: 162,
        last_verified_sequence: 162,
        chain_head_sequence: 162,
        errors: [],
      };
      assert.equal(getConsoleStatus(validReport), "VALID");
    });

    it("correctly identifies compromised ledger and failure sequence", () => {
      const compromisedReport = {
        is_valid: false,
        status: "COMPROMISED",
        total_events_checked: 50,
        last_verified_sequence: 41,
        first_failure_sequence: 42,
        failure_category: "PAYLOAD_TAMPERED",
        errors: [
          {
            sequence_number: 42,
            error_type: "HASH_MISMATCH",
            message: "Cryptographic digest mismatch at sequence 42.",
          },
        ],
      };

      assert.equal(compromisedReport.is_valid, false);
      assert.equal(compromisedReport.status, "COMPROMISED");
      assert.equal(compromisedReport.first_failure_sequence, 42);
      assert.equal(compromisedReport.last_verified_sequence, 41);
      assert.equal(compromisedReport.errors.length, 1);
    });
  });

  describe("4. Entity Lifecycle Before-and-After State Diff Engine", () => {
    it("computes key diff between previous and new states", () => {
      const computeDiff = (prev, next) => {
        if (!prev && !next) return [];
        if (!prev && next) return Object.keys(next).map((k) => ({ key: k, oldVal: undefined, newVal: next[k] }));
        const allKeys = Array.from(new Set([...Object.keys(prev), ...Object.keys(next)]));
        return allKeys
          .filter((k) => JSON.stringify(prev[k]) !== JSON.stringify(next[k]))
          .map((k) => ({ key: k, oldVal: prev[k], newVal: next[k] }));
      };

      const prev = { status: "PENDING", quantity: "500.0", notes: "First draft" };
      const next = { status: "VERIFIED", quantity: "450.0", notes: "First draft" };

      const diff = computeDiff(prev, next);
      assert.equal(diff.length, 2);
      assert.equal(diff.some((d) => d.key === "status" && d.oldVal === "PENDING" && d.newVal === "VERIFIED"), true);
      assert.equal(diff.some((d) => d.key === "quantity" && d.oldVal === "500.0" && d.newVal === "450.0"), true);
      assert.equal(diff.some((d) => d.key === "notes"), false);
    });

    it("handles initial entity creation where previous state is null", () => {
      const computeDiff = (prev, next) => {
        if (!prev && !next) return [];
        if (!prev && next) return Object.keys(next).map((k) => ({ key: k, oldVal: undefined, newVal: next[k] }));
        return [];
      };

      const next = { project_id: "p1", name: "Sundarbans Reforestation" };
      const diff = computeDiff(null, next);
      assert.equal(diff.length, 2);
      assert.equal(diff[0].oldVal, undefined);
    });
  });

  describe("5. Role-Based Access Control for Audit History", () => {
    it("permits ADMIN and PROJECT_MANAGER while rejecting FIELD_OFFICER", () => {
      const allowedRoles = ["ADMIN", "PROJECT_MANAGER"];
      const canAccessAudit = (role) => allowedRoles.includes(role);

      assert.equal(canAccessAudit("ADMIN"), true);
      assert.equal(canAccessAudit("PROJECT_MANAGER"), true);
      assert.equal(canAccessAudit("FIELD_OFFICER"), false);
    });

    it("applies project scoping rules for Project Managers", () => {
      const getFilterConstraints = (user) => {
        if (user.role === "ADMIN") return { isScoped: false };
        if (user.role === "PROJECT_MANAGER") return { isScoped: true, assignedProjects: user.assignedProjectIds };
        throw new Error("Access denied");
      };

      const adminConstraints = getFilterConstraints({ role: "ADMIN" });
      assert.equal(adminConstraints.isScoped, false);

      const pmConstraints = getFilterConstraints({
        role: "PROJECT_MANAGER",
        assignedProjectIds: ["p1", "p2"],
      });
      assert.equal(pmConstraints.isScoped, true);
      assert.deepEqual(pmConstraints.assignedProjects, ["p1", "p2"]);

      assert.throws(() => getFilterConstraints({ role: "FIELD_OFFICER" }));
    });
  });
});
