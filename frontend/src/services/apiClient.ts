import axios, { type AxiosError, type AxiosInstance } from "axios";
import type { HealthStatus } from "@/types";

// Base URLs derived from Vite environment variables (fallback to localhost)
// Strip any trailing slashes to prevent double slashes in constructed endpoint paths
const RAW_BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || "http://localhost:8000").trim();
export const BACKEND_URL = RAW_BACKEND_URL.replace(/\/+$/, "");

const RAW_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || `${BACKEND_URL}/api/v1`).trim();
export const API_BASE_URL = RAW_API_BASE_URL.replace(/\/+$/, "");

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
    // Normalizes API error payloads
    const errorData = error.response?.data as { detail?: { message?: string } } | undefined;
    const message = errorData?.detail?.message || error.message || "An unexpected network error occurred.";
    return Promise.reject(new Error(message));
  }
);

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
