/**
 * Authentication context and provider.
 *
 * Manages user authentication state across the dashboard application.
 * Wraps the app in `AuthProvider` to make `useAuth()` available to all
 * client components.
 *
 * **For Developers:**
 *   - The provider loads the current user on mount by reading the access
 *     token cookie and calling `GET /api/v1/auth/me`.
 *   - If the access token is expired but a refresh token exists, it
 *     automatically refreshes before retrying.
 *   - Call `login()`, `register()`, or `logout()` to manage auth state.
 *
 * **For QA Engineers:**
 *   - `loading` is true during initial auth check (shows loading UI).
 *   - `error` contains the last auth error message (login/register failures).
 */

"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "@/lib/auth";

/** User profile returned by the `/auth/me` endpoint. */
interface User {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

/** Token response from login/register/refresh endpoints. */
interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

/** Shape of the authentication context value. */
interface AuthContextValue {
  /** The currently authenticated user, or null if not logged in. */
  user: User | null;
  /** Whether the initial auth check is still in progress. */
  loading: boolean;
  /** The last authentication error message, or null. */
  error: string | null;
  /**
   * Log in with email and password.
   * On success, stores tokens and redirects to `/`.
   */
  login: (email: string, password: string) => Promise<void>;
  /**
   * Register a new account with email and password.
   * On success, stores tokens and redirects to `/`.
   */
  register: (email: string, password: string) => Promise<void>;
  /** Log out, clear tokens, and redirect to `/login`. */
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Provider component that wraps the app and manages authentication state.
 *
 * @param children - Child components that can access auth via `useAuth()`.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  /**
   * Load the current user by calling GET /auth/me.
   * If the access token is expired, attempts a refresh first.
   */
  const loadUser = useCallback(async () => {
    const accessToken = getAccessToken();

    if (!accessToken) {
      // No access token — try refreshing if we have a refresh token.
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        const refreshResult = await api.post<TokenResponse>(
          "/api/v1/auth/refresh",
          { refresh_token: refreshToken }
        );
        if (refreshResult.data) {
          setTokens(refreshResult.data.access_token, refreshResult.data.refresh_token);
          api.setToken(refreshResult.data.access_token);
        } else {
          // Refresh failed — clear stale tokens.
          clearTokens();
          setLoading(false);
          return;
        }
      } else {
        setLoading(false);
        return;
      }
    } else {
      api.setToken(accessToken);
    }

    // Fetch user profile with the (possibly refreshed) access token.
    const result = await api.get<User>("/api/v1/auth/me");
    if (result.data) {
      setUser(result.data);
    } else {
      // Token is invalid — clear everything.
      clearTokens();
      api.setToken(null);
    }
    setLoading(false);
  }, []);

  // Load user on mount.
  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      setError(null);
      const result = await api.post<TokenResponse>("/api/v1/auth/login", {
        email,
        password,
      });

      if (result.error) {
        setError(result.error.message);
        return;
      }

      const { access_token, refresh_token } = result.data!;
      setTokens(access_token, refresh_token);
      api.setToken(access_token);

      // Load user profile after storing tokens.
      const meResult = await api.get<User>("/api/v1/auth/me");
      if (meResult.data) {
        setUser(meResult.data);
      }
      router.push("/");
    },
    [router]
  );

  const register = useCallback(
    async (email: string, password: string) => {
      setError(null);
      const result = await api.post<TokenResponse>("/api/v1/auth/register", {
        email,
        password,
      });

      if (result.error) {
        setError(result.error.message);
        return;
      }

      const { access_token, refresh_token } = result.data!;
      setTokens(access_token, refresh_token);
      api.setToken(access_token);

      // Load user profile after storing tokens.
      const meResult = await api.get<User>("/api/v1/auth/me");
      if (meResult.data) {
        setUser(meResult.data);
      }
      router.push("/");
    },
    [router]
  );

  const logout = useCallback(() => {
    clearTokens();
    api.setToken(null);
    setUser(null);
    router.push("/login");
  }, [router]);

  const value = useMemo(
    () => ({ user, loading, error, login, register, logout }),
    [user, loading, error, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to access the authentication context.
 *
 * Must be used within an `AuthProvider`. Returns the current user,
 * loading state, and auth action functions.
 *
 * @returns The AuthContextValue with user state and auth methods.
 * @throws Error if used outside of AuthProvider.
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
