import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { apiClient, setAuthToken, setOnUnauthorizedCallback } from "@/services/apiClient";
import type { UserProfile, AuthResponse } from "@/types/auth";

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<UserProfile>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<UserProfile | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Session storage keys — strictly session-scoped, never persistent localStorage
const SESSION_ACCESS_TOKEN_KEY = "vana_session_access_token";
const SESSION_REFRESH_TOKEN_KEY = "vana_session_refresh_token";

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setTokenState] = useState<string | null>(() => {
    return sessionStorage.getItem(SESSION_ACCESS_TOKEN_KEY);
  });
  const [refreshToken, setRefreshTokenState] = useState<string | null>(() => {
    return sessionStorage.getItem(SESSION_REFRESH_TOKEN_KEY);
  });
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const applyTokens = useCallback((newAccessToken: string | null, newRefreshToken?: string | null) => {
    setTokenState(newAccessToken);
    setAuthToken(newAccessToken);
    if (newAccessToken) {
      sessionStorage.setItem(SESSION_ACCESS_TOKEN_KEY, newAccessToken);
    } else {
      sessionStorage.removeItem(SESSION_ACCESS_TOKEN_KEY);
    }

    if (newRefreshToken !== undefined) {
      setRefreshTokenState(newRefreshToken);
      if (newRefreshToken) {
        sessionStorage.setItem(SESSION_REFRESH_TOKEN_KEY, newRefreshToken);
      } else {
        sessionStorage.removeItem(SESSION_REFRESH_TOKEN_KEY);
      }
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      if (token || refreshToken) {
        await apiClient.post("/auth/logout", {
          refresh_token: refreshToken || undefined,
        });
      }
    } catch {
      // Ignore network errors on logout
    } finally {
      applyTokens(null, null);
      setUser(null);
    }
  }, [token, refreshToken, applyTokens]);

  const refreshProfile = useCallback(async (): Promise<UserProfile | null> => {
    try {
      const response = await apiClient.get<UserProfile>("/auth/me");
      setUser(response.data);
      return response.data;
    } catch {
      applyTokens(null, null);
      setUser(null);
      return null;
    }
  }, [applyTokens]);

  const login = useCallback(
    async (email: string, password: string): Promise<UserProfile> => {
      const response = await apiClient.post<AuthResponse>("/auth/login", {
        email: email.trim(),
        password,
      });
      const data = response.data;
      applyTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      return data.user;
    },
    [applyTokens]
  );

  // Initialize session verification on mount
  useEffect(() => {
    setOnUnauthorizedCallback(() => {
      applyTokens(null, null);
      setUser(null);
    });

    const initAuth = async () => {
      const storedToken = sessionStorage.getItem(SESSION_ACCESS_TOKEN_KEY);
      if (storedToken) {
        setAuthToken(storedToken);
        try {
          const response = await apiClient.get<UserProfile>("/auth/me");
          setUser(response.data);
        } catch {
          applyTokens(null, null);
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    initAuth();

    return () => {
      setOnUnauthorizedCallback(null);
    };
  }, [applyTokens]);

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!user && !!token,
    isLoading,
    login,
    logout,
    refreshProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
