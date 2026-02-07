/**
 * Customer authentication context for the storefront.
 *
 * Manages customer login state, token storage, and profile loading.
 * All API calls are scoped to the current store slug from the store context.
 *
 * **For Developers:**
 *   Use ``useCustomerAuth()`` in client components to access customer state.
 *   The provider handles token refresh on mount if an access token is missing
 *   but a refresh token exists.
 *
 * **For QA Engineers:**
 *   - ``customer`` is null when not logged in or still loading.
 *   - ``loading`` is true during initial auth check.
 *   - ``login`` / ``register`` / ``logout`` update state and tokens.
 *   - Tokens are stored in cookies (separate from dashboard tokens).
 *
 * **For End Users:**
 *   Sign in to your account to view order history and manage your wishlist.
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
import { useStore } from "./store-context";
import { api } from "@/lib/api";
import {
  clearCustomerTokens,
  getCustomerAccessToken,
  getCustomerRefreshToken,
  setCustomerTokens,
} from "@/lib/auth";
import type { Customer, CustomerTokenResponse } from "@/lib/types";

/** Shape of the customer authentication context. */
interface CustomerAuthContextValue {
  /** The currently authenticated customer, or null. */
  customer: Customer | null;
  /** Whether the initial auth check is in progress. */
  loading: boolean;
  /** Last error message from login/register, or null. */
  error: string | null;
  /** Log in with email and password. */
  login: (email: string, password: string) => Promise<boolean>;
  /** Register with email, password, and optional name. */
  register: (
    email: string,
    password: string,
    firstName?: string,
    lastName?: string
  ) => Promise<boolean>;
  /** Log out and clear tokens. */
  logout: () => void;
  /** Update the customer profile. */
  updateProfile: (data: {
    first_name?: string;
    last_name?: string;
    phone?: string;
  }) => Promise<boolean>;
}

const CustomerAuthContext = createContext<CustomerAuthContextValue | null>(null);

/**
 * Provider component that manages customer authentication state.
 *
 * @param props - Provider props.
 * @param props.children - Child components that can access auth via ``useCustomerAuth()``.
 * @returns A context provider wrapping the children.
 */
export function CustomerAuthProvider({ children }: { children: React.ReactNode }) {
  const store = useStore();
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const slug = store?.slug;

  /**
   * Load customer profile using stored tokens.
   * Attempts refresh if access token is expired.
   */
  const loadCustomer = useCallback(async () => {
    if (!slug) {
      setLoading(false);
      return;
    }

    let accessToken = getCustomerAccessToken();

    if (!accessToken) {
      const refreshToken = getCustomerRefreshToken();
      if (refreshToken) {
        const result = await api.post<CustomerTokenResponse>(
          `/api/v1/public/stores/${encodeURIComponent(slug)}/auth/refresh`,
          { refresh_token: refreshToken },
          { noAuth: true }
        );
        if (result.data) {
          setCustomerTokens(result.data.access_token, result.data.refresh_token);
          accessToken = result.data.access_token;
        } else {
          clearCustomerTokens();
          setLoading(false);
          return;
        }
      } else {
        setLoading(false);
        return;
      }
    }

    const result = await api.get<Customer>(
      `/api/v1/public/stores/${encodeURIComponent(slug)}/auth/me`,
      { authToken: accessToken }
    );
    if (result.data) {
      setCustomer(result.data);
    } else {
      clearCustomerTokens();
    }
    setLoading(false);
  }, [slug]);

  useEffect(() => {
    loadCustomer();
  }, [loadCustomer]);

  const login = useCallback(
    async (email: string, password: string): Promise<boolean> => {
      if (!slug) return false;
      setError(null);

      const result = await api.post<CustomerTokenResponse>(
        `/api/v1/public/stores/${encodeURIComponent(slug)}/auth/login`,
        { email, password },
        { noAuth: true }
      );

      if (result.error) {
        setError(result.error.message);
        return false;
      }

      const { access_token, refresh_token } = result.data!;
      setCustomerTokens(access_token, refresh_token);

      const me = await api.get<Customer>(
        `/api/v1/public/stores/${encodeURIComponent(slug)}/auth/me`,
        { authToken: access_token }
      );
      if (me.data) setCustomer(me.data);
      return true;
    },
    [slug]
  );

  const register = useCallback(
    async (
      email: string,
      password: string,
      firstName?: string,
      lastName?: string
    ): Promise<boolean> => {
      if (!slug) return false;
      setError(null);

      const result = await api.post<CustomerTokenResponse>(
        `/api/v1/public/stores/${encodeURIComponent(slug)}/auth/register`,
        {
          email,
          password,
          first_name: firstName || undefined,
          last_name: lastName || undefined,
        },
        { noAuth: true }
      );

      if (result.error) {
        setError(result.error.message);
        return false;
      }

      const { access_token, refresh_token } = result.data!;
      setCustomerTokens(access_token, refresh_token);

      const me = await api.get<Customer>(
        `/api/v1/public/stores/${encodeURIComponent(slug)}/auth/me`,
        { authToken: access_token }
      );
      if (me.data) setCustomer(me.data);
      return true;
    },
    [slug]
  );

  const logout = useCallback(() => {
    clearCustomerTokens();
    setCustomer(null);
  }, []);

  const updateProfile = useCallback(
    async (data: {
      first_name?: string;
      last_name?: string;
      phone?: string;
    }): Promise<boolean> => {
      if (!slug) return false;
      setError(null);

      const result = await api.patch<Customer>(
        `/api/v1/public/stores/${encodeURIComponent(slug)}/auth/me`,
        data
      );

      if (result.error) {
        setError(result.error.message);
        return false;
      }

      if (result.data) setCustomer(result.data);
      return true;
    },
    [slug]
  );

  const value = useMemo(
    () => ({ customer, loading, error, login, register, logout, updateProfile }),
    [customer, loading, error, login, register, logout, updateProfile]
  );

  return (
    <CustomerAuthContext.Provider value={value}>
      {children}
    </CustomerAuthContext.Provider>
  );
}

/**
 * Hook to access the customer authentication context.
 *
 * @returns The CustomerAuthContextValue with customer state and auth methods.
 * @throws Error if used outside of CustomerAuthProvider.
 */
export function useCustomerAuth(): CustomerAuthContextValue {
  const context = useContext(CustomerAuthContext);
  if (!context) {
    throw new Error("useCustomerAuth must be used within a CustomerAuthProvider");
  }
  return context;
}
