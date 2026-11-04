import { describe, it } from "node:test";
import assert from "node:assert/strict";

/**
 * Resolves and validates Backend and API Base URLs based on environment mode.
 * Matches implementation in frontend/src/services/apiClient.ts
 */
function resolveApiUrls(env = {}) {
  const isProd = Boolean(env.PROD);
  const rawApiBase = env.VITE_API_BASE_URL?.trim();
  const rawBackend = env.VITE_BACKEND_URL?.trim();

  // 1. Production must require a valid backend API URL
  if (isProd && !rawApiBase && !rawBackend) {
    throw new Error(
      "[VANA CRITICAL CONFIGURATION ERROR] Production environment requires a valid backend API URL. " +
      "Neither VITE_BACKEND_URL nor VITE_API_BASE_URL is configured. " +
      "Silent fallback to localhost is strictly prohibited in production."
    );
  }

  function validateUrl(urlStr, varName) {
    const trimmed = urlStr.trim().replace(/\/+$/, "");
    if (!trimmed) {
      throw new Error(`[VANA CONFIGURATION ERROR] ${varName} cannot be empty.`);
    }
    let parsed;
    try {
      parsed = new URL(trimmed);
    } catch {
      throw new Error(`[VANA CONFIGURATION ERROR] ${varName} is a malformed URL: '${trimmed}'`);
    }

    if (!["http:", "https:"].includes(parsed.protocol)) {
      throw new Error(`[VANA CONFIGURATION ERROR] ${varName} must use http:// or https:// protocol: '${trimmed}'`);
    }

    if (isProd) {
      const hostname = parsed.hostname.toLowerCase();
      if (hostname === "localhost" || hostname === "127.0.0.1" || hostname === "0.0.0.0") {
        throw new Error(
          `[VANA CRITICAL CONFIGURATION ERROR] Production ${varName} cannot point to localhost or loopback address: '${trimmed}'`
        );
      }
    }
    return trimmed;
  }

  // 2. Prioritize VITE_API_BASE_URL if explicitly provided
  if (rawApiBase) {
    const validatedApi = validateUrl(rawApiBase, "VITE_API_BASE_URL");
    const cleanBackend = validatedApi.endsWith("/api/v1")
      ? validatedApi.slice(0, -"/api/v1".length).replace(/\/+$/, "")
      : validatedApi;
    return {
      backendUrl: cleanBackend,
      apiBaseUrl: validatedApi,
    };
  }

  // 3. Otherwise use VITE_BACKEND_URL, with development fallback to localhost
  let validatedBackend;
  if (rawBackend) {
    validatedBackend = validateUrl(rawBackend, "VITE_BACKEND_URL");
  } else {
    validatedBackend = "http://localhost:8000";
  }

  const apiBaseUrl = validatedBackend.endsWith("/api/v1")
    ? validatedBackend
    : `${validatedBackend}/api/v1`;

  const backendUrl = validatedBackend.endsWith("/api/v1")
    ? validatedBackend.slice(0, -"/api/v1".length).replace(/\/+$/, "")
    : validatedBackend;

  return {
    backendUrl,
    apiBaseUrl,
  };
}

describe("Frontend API Client URL Resolution & Production Safety", () => {
  describe("Development Environment Behavior (PROD = false)", () => {
    it("falls back to localhost:8000 when no environment variables are set", () => {
      const config = resolveApiUrls({ PROD: false });
      assert.equal(config.backendUrl, "http://localhost:8000");
      assert.equal(config.apiBaseUrl, "http://localhost:8000/api/v1");
    });

    it("respects custom development VITE_BACKEND_URL", () => {
      const config = resolveApiUrls({ PROD: false, VITE_BACKEND_URL: "http://localhost:9000" });
      assert.equal(config.backendUrl, "http://localhost:9000");
      assert.equal(config.apiBaseUrl, "http://localhost:9000/api/v1");
    });

    it("strips trailing slashes from development backend URL", () => {
      const config = resolveApiUrls({ PROD: false, VITE_BACKEND_URL: "http://localhost:8000///" });
      assert.equal(config.backendUrl, "http://localhost:8000");
      assert.equal(config.apiBaseUrl, "http://localhost:8000/api/v1");
    });

    it("prevents duplicate /api/v1 if backend URL already includes it", () => {
      const config = resolveApiUrls({ PROD: false, VITE_BACKEND_URL: "http://localhost:8000/api/v1" });
      assert.equal(config.backendUrl, "http://localhost:8000");
      assert.equal(config.apiBaseUrl, "http://localhost:8000/api/v1");
    });
  });

  describe("Production Environment Behavior (PROD = true)", () => {
    it("fails fast with critical error when neither VITE_BACKEND_URL nor VITE_API_BASE_URL is configured", () => {
      assert.throws(
        () => resolveApiUrls({ PROD: true }),
        (err) => {
          assert.match(err.message, /VANA CRITICAL CONFIGURATION ERROR/);
          assert.match(err.message, /Production environment requires a valid backend API URL/);
          assert.match(err.message, /Silent fallback to localhost is strictly prohibited/);
          return true;
        }
      );
    });

    it("fails fast in production if VITE_BACKEND_URL points to localhost", () => {
      assert.throws(
        () => resolveApiUrls({ PROD: true, VITE_BACKEND_URL: "http://localhost:8000" }),
        (err) => {
          assert.match(err.message, /cannot point to localhost or loopback address/);
          return true;
        }
      );
    });

    it("fails fast in production if VITE_BACKEND_URL points to 127.0.0.1", () => {
      assert.throws(
        () => resolveApiUrls({ PROD: true, VITE_BACKEND_URL: "http://127.0.0.1:8000" }),
        (err) => {
          assert.match(err.message, /cannot point to localhost or loopback address/);
          return true;
        }
      );
    });

    it("resolves valid remote Render production backend URL successfully", () => {
      const config = resolveApiUrls({
        PROD: true,
        VITE_BACKEND_URL: "https://vana-backend.onrender.com",
      });
      assert.equal(config.backendUrl, "https://vana-backend.onrender.com");
      assert.equal(config.apiBaseUrl, "https://vana-backend.onrender.com/api/v1");
    });

    it("resolves explicit VITE_API_BASE_URL and derives root backendUrl cleanly", () => {
      const config = resolveApiUrls({
        PROD: true,
        VITE_API_BASE_URL: "https://vana-backend.onrender.com/api/v1",
      });
      assert.equal(config.backendUrl, "https://vana-backend.onrender.com");
      assert.equal(config.apiBaseUrl, "https://vana-backend.onrender.com/api/v1");
    });

    it("rejects malformed URLs in production", () => {
      assert.throws(
        () => resolveApiUrls({ PROD: true, VITE_BACKEND_URL: "not-a-valid-url" }),
        (err) => {
          assert.match(err.message, /malformed URL/);
          return true;
        }
      );
    });

    it("rejects non-http/https protocols", () => {
      assert.throws(
        () => resolveApiUrls({ PROD: true, VITE_BACKEND_URL: "ftp://files.vana.earth" }),
        (err) => {
          assert.match(err.message, /must use http:\/\/ or https:\/\/ protocol/);
          return true;
        }
      );
    });
  });
});
