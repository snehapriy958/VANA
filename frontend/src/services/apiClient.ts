import axios, { type AxiosError, type AxiosInstance } from "axios";
import type { HealthStatus } from "@/types";

export interface ApiUrlConfig {
  backendUrl: string;
  apiBaseUrl: string;
}

export interface EnvLike {
  PROD?: boolean;
  DEV?: boolean;
  MODE?: string;
  VITE_API_BASE_URL?: string;
  VITE_BACKEND_URL?: string;
}

/**
 * Resolves and validates Backend and API Base URLs based on environment mode.
 * - Production: Requires either VITE_API_BASE_URL or VITE_BACKEND_URL.
 *   Fails fast on missing, malformed, or localhost URLs.
 * - Development: Preserves fallback to http://localhost:8000.
 * - Normalizes trailing slashes and prevents duplicate /api/v1 path segments.
 */
export function resolveApiUrls(env: EnvLike = import.meta.env): ApiUrlConfig {
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

  function validateUrl(urlStr: string, varName: string): string {
    const trimmed = urlStr.trim().replace(/\/+$/, "");
    if (!trimmed) {
      throw new Error(`[VANA CONFIGURATION ERROR] ${varName} cannot be empty.`);
    }
    let parsed: URL;
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
  let validatedBackend: string;
  if (rawBackend) {
    validatedBackend = validateUrl(rawBackend, "VITE_BACKEND_URL");
  } else {
    // Development fallback
    validatedBackend = "http://localhost:8000";
  }

  // Prevent duplicate /api/v1 segments
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

// Initial configuration resolution
let activeConfig: ApiUrlConfig;
try {
  activeConfig = resolveApiUrls();
} catch (err) {
  // If running in production build context without injected env, provide safe dummy so build doesn't crash
  // Runtime evaluation in the browser will throw the configuration error.
  if (import.meta.env?.PROD) {
    console.error((err as Error).message);
    activeConfig = {
      backendUrl: "",
      apiBaseUrl: "/api/v1",
    };
  } else {
    throw err;
  }
}

export const BACKEND_URL = activeConfig.backendUrl;
export const API_BASE_URL = activeConfig.apiBaseUrl;

/**
 * Primary Axios client for versioned API endpoints (/api/v1/...)
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

/**
 * Updates or clears the in-memory Authorization header on apiClient.
 * Never writes tokens to localStorage.
 */
export function setAuthToken(token: string | null): void {
  if (token) {
    apiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete apiClient.defaults.headers.common["Authorization"];
  }
}

/**
 * Root client for unversioned endpoints (e.g., /health, /metrics)
 */
export const rootClient: AxiosInstance = axios.create({
  baseURL: BACKEND_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 5000,
});

// Listener for session expiration / unauthorized events
type AuthErrorCallback = () => void;
let onUnauthorizedCallback: AuthErrorCallback | null = null;

export function setOnUnauthorizedCallback(cb: AuthErrorCallback | null): void {
  onUnauthorizedCallback = cb;
}

// Response interceptor for centralized error extraction and 401 handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && onUnauthorizedCallback) {
      onUnauthorizedCallback();
    }
    // Normalizes API error payloads from FastAPI / Pydantic responses
    let message: string | undefined;
    const errorData = error.response?.data as
      | { detail?: string | { message?: string } | Array<{ msg?: string; loc?: string[] }>; message?: string }
      | undefined;

    if (typeof errorData?.detail === "string") {
      message = errorData.detail;
    } else if (errorData?.detail && typeof errorData.detail === "object") {
      if ("message" in errorData.detail && typeof errorData.detail.message === "string") {
        message = errorData.detail.message;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail
          .map((item) => item.msg || (item.loc ? `${item.loc.join(".")}: error` : "Validation error"))
          .join("; ");
      }
    } else if (typeof errorData?.message === "string") {
      message = errorData.message;
    }

    const finalMessage = message || error.message || "An unexpected network error occurred.";
    return Promise.reject(new Error(finalMessage));
  }
);

/**
 * Extracts a human-readable error message from an unknown error object.
 */
export function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  if (error && typeof error === "object" && "message" in error && typeof (error as any).message === "string") {
    return (error as any).message;
  }
  return "An unexpected error occurred.";
}

/**
 * Health check probe querying backend /health
 */
export async function fetchHealthStatus(): Promise<HealthStatus> {
  try {
    const response = await rootClient.get<HealthStatus>("/health");
    return response.data;
  } catch (error) {
    return {
      status: "down",
      database: "disconnected",
      environment: "unknown",
      platform: "VANA (offline)",
    };
  }
}
