/**
 * AcousticSpace — Auth Context
 * =============================
 * Provides authentication state and actions to the entire React tree.
 *
 * Storage strategy
 * ----------------
 * - access_token  → sessionStorage (cleared when tab closes)
 * - refresh_token → localStorage when remember_me=true, sessionStorage otherwise
 *
 * Token refresh
 * -------------
 * An Axios response interceptor in client.ts intercepts 401 responses,
 * calls POST /auth/refresh with the stored refresh token, updates storage,
 * and retries the original request once.  AuthContext exposes the raw
 * `refreshTokens()` helper so the interceptor can call it directly.
 *
 * Exported API
 * ------------
 * useAuth()            — hook to consume the context
 * AuthProvider         — wrap the app with this
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { LoginPayload, RegisterPayload, TokenResponse, User } from "../types";
import {
  apiLogin,
  apiLogout,
  apiRefresh,
  apiRegister,
} from "../api/client";

// ---------------------------------------------------------------------------
// Storage keys
// ---------------------------------------------------------------------------
const ACCESS_KEY = "as_access_token";
const REFRESH_KEY = "as_refresh_token";

function getStoredAccess(): string | null {
  return sessionStorage.getItem(ACCESS_KEY);
}

function getStoredRefresh(): string | null {
  return (
    localStorage.getItem(REFRESH_KEY) ?? sessionStorage.getItem(REFRESH_KEY)
  );
}

function storeTokens(tokens: TokenResponse, rememberMe: boolean): void {
  sessionStorage.setItem(ACCESS_KEY, tokens.access_token);
  if (rememberMe) {
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    sessionStorage.removeItem(REFRESH_KEY);
  } else {
    sessionStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    localStorage.removeItem(REFRESH_KEY);
  }
}

function clearTokens(): void {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// ---------------------------------------------------------------------------
// Context shape
// ---------------------------------------------------------------------------
interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;             // true while bootstrapping from storage
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  refreshTokens: () => Promise<string | null>;  // returns new access token or null
  getAccessToken: () => string | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount: if we have a refresh token, attempt a silent refresh to
  // restore the session without requiring re-login.
  useEffect(() => {
    const refresh = getStoredRefresh();
    if (!refresh) {
      setIsLoading(false);
      return;
    }
    apiRefresh({ refresh_token: refresh })
      .then((tokens) => {
        const rememberMe = localStorage.getItem(REFRESH_KEY) !== null;
        storeTokens(tokens, rememberMe);
        setUser(tokens.user);
      })
      .catch(() => {
        clearTokens();
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const tokens = await apiLogin(payload);
    console.debug("[AuthContext] login success", { user: tokens.user, hasUser: !!tokens.user });
    storeTokens(tokens, payload.remember_me ?? false);
    setUser(tokens.user);
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    // Register then immediately log in so the user lands in the app.
    await apiRegister(payload);
    const tokens = await apiLogin({
      email: payload.email,
      password: payload.password,
      remember_me: false,
    });
    storeTokens(tokens, false);
    setUser(tokens.user);
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      clearTokens();
      setUser(null);
    }
  }, []);

  const refreshTokens = useCallback(async (): Promise<string | null> => {
    const refresh = getStoredRefresh();
    if (!refresh) return null;
    try {
      const tokens = await apiRefresh({ refresh_token: refresh });
      const rememberMe = localStorage.getItem(REFRESH_KEY) !== null;
      storeTokens(tokens, rememberMe);
      setUser(tokens.user);
      return tokens.access_token;
    } catch {
      clearTokens();
      setUser(null);
      return null;
    }
  }, []);

  const getAccessToken = useCallback(() => getStoredAccess(), []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isLoading,
      login,
      register,
      logout,
      refreshTokens,
      getAccessToken,
    }),
    [user, isLoading, login, register, logout, refreshTokens, getAccessToken]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
