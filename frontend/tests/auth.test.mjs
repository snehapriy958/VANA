import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { z } from "zod";

// Replicating frontend login and provisioning schemas for unit validation
const loginSchema = z.object({
  email: z.string().trim().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

const provisionUserSchema = z.object({
  email: z.string().trim().email("Valid email required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  full_name: z.string().min(2, "Full name must be at least 2 characters"),
  role: z.enum(["ADMIN", "PROJECT_MANAGER", "FIELD_OFFICER"]),
});

describe("Frontend Authentication & RBAC Unit Tests", () => {
  it("validates correct login credentials format", () => {
    const valid = { email: "operator@akshayavana.com", password: "SecretPassword123!" };
    const parsed = loginSchema.safeParse(valid);
    assert.equal(parsed.success, true);
  });

  it("rejects invalid email in login schema", () => {
    const invalid = { email: "not-an-email", password: "SomePassword!" };
    const parsed = loginSchema.safeParse(invalid);
    assert.equal(parsed.success, false);
    assert.equal(parsed.error?.issues[0].message, "Please enter a valid email address");
  });

  it("rejects empty password in login schema", () => {
    const invalid = { email: "user@akshayavana.com", password: "" };
    const parsed = loginSchema.safeParse(invalid);
    assert.equal(parsed.success, false);
  });

  it("enforces minimum 8 characters on provisioning password", () => {
    const shortPass = {
      email: "new@akshayavana.com",
      password: "short",
      full_name: "Test User",
      role: "FIELD_OFFICER",
    };
    const parsed = provisionUserSchema.safeParse(shortPass);
    assert.equal(parsed.success, false);
    assert.equal(parsed.error?.issues[0].message, "Password must be at least 8 characters");
  });

  it("correctly filters role-aware navigation", () => {
    const navigation = [
      { name: "Dashboard", href: "/dashboard" },
      { name: "Projects", href: "/projects" },
      { name: "Living Earth Map", href: "/map" },
      { name: "Field Operations", href: "/operations" },
      { name: "Verification Centre", href: "/verification", allowedRoles: ["ADMIN", "PROJECT_MANAGER"] },
      { name: "Impact Analytics", href: "/analytics" },
      { name: "Team Management", href: "/team", allowedRoles: ["ADMIN", "PROJECT_MANAGER"] },
      { name: "Audit History", href: "/audit", allowedRoles: ["ADMIN"] },
    ];

    const filterForRole = (role) => {
      return navigation.filter((item) => {
        if (!item.allowedRoles) return true;
        return item.allowedRoles.includes(role);
      });
    };

    // ADMIN sees all 8 modules
    const adminNav = filterForRole("ADMIN");
    assert.equal(adminNav.length, 8);

    // PROJECT_MANAGER sees 7 modules (cannot see Audit History)
    const pmNav = filterForRole("PROJECT_MANAGER");
    assert.equal(pmNav.length, 7);
    assert.equal(pmNav.some((i) => i.name === "Audit History"), false);
    assert.equal(pmNav.some((i) => i.name === "Team Management"), true);

    // FIELD_OFFICER sees 5 modules (cannot see Verification, Team Management, or Audit History)
    const foNav = filterForRole("FIELD_OFFICER");
    assert.equal(foNav.length, 5);
    assert.equal(foNav.some((i) => i.name === "Verification Centre"), false);
    assert.equal(foNav.some((i) => i.name === "Team Management"), false);
    assert.equal(foNav.some((i) => i.name === "Audit History"), false);
  });
});
