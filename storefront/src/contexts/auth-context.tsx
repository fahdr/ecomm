/**
 * Customer authentication context for the storefront.
 *
 * Provides login, register, logout, and auto-refresh functionality for
 * customer accounts. Wraps the app so any component can access the
 * current customer state via ``useCustomerAuth()``.
 *
 * **For Developers:**
 *   Add ``<CustomerAuthProvider>`` in the root layout, inside ``StoreProvider``.
 *   Use the ``useCustomerAuth()`` hook to access customer state and actions.
 *
 * **For QA Engineers:**
 *   - On mount, attempts to refresh the session using the stored refresh token.
 *   - Login/register set tokens and customer state.
 *   - Logout clears tokens and redirects to login.
 *   - ``loading`` is true during the initial auth check on mount.
 *
 * **For End Users:**
 *   Your login session persists across page refreshes. You'll be automatically
 *   signed back in when you return to the store.
 */

"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import {
  clearCustomerTokens,
  getCustomerAccessToken,
  getCustomerRefreshToken,
  setCustomerTokens,
} from "@/lib/auth";

/** Customer profile shape from the API. */
interface CustomerProfile {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  is_active: boolean;
  created_at: string;
}

/** Token response from login/register. */
interface TokenResponse {
  access_token: string;
  refresh_token: string;
  customer: CustomerProfile;
}

/** Auth context value exposed to consumers. */
interface CustomerAuthContextValue {
  customer: CustomerProfile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<string | null>;
  register: (
    email: string,
    password: string,
    firstName?: string,
    lastName?: string
  ) => Promise<string | null>;
  logout: () => void;
  getAuthHeaders: () => Record<string, string>;
}

const CustomerAuthContext = createContext<CustomerAuthContextValue>({
  customer: null,
  loading: true,
  login: async () => "Not initialized",
  register: async () => "Not initialized",
  logout: () => {},
  getAuthHeaders: () => ({}),
});

/**
 * Provider component for customer authentication.
 *
 * @param props - Provider props.
 * @param props.children - Child components.
 * @returns A context provider wrapping children with auth state.
 */
export function CustomerAuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const store = useStore();
  const [customer, setCustomer] = useState<CustomerProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const slug = store?.slug;

  /**
   * Build Authorization headers from the stored access token.
   */
  const getAuthHeaders = useCallback((): Record<string, string> => {
    const token = getCustomerAccessToken();
    if (!token) return {};
    return { Authorization: `Bearer ${token}` };
  }, []);

  /**
   * Try to refresh the session on mount using the stored refresh token.
   */
  useEffect(() => {
    if (!slug) {
      setLoading(false);
      return;
    }

    async function tryRefresh() {
      const refreshToken = getCustomerRefreshToken();
      if (!refreshToken) {
        setLoading(false);
        return;
      }

      const result = await api.post<{ access_token: string }>(
        `/api/v1/public/stores/${slug}/customers/refresh`,
        { refresh_token: refreshToken }
      );

      if (result.data) {
        setCustomerTokens(result.data.access_token, refreshToken);
        // Fetch profile with the new token
        const profileResult = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/public/stores/${slug}/customers/me`,
          { headers: { Authorization: `Bearer ${result.data.access_token}` } }
        );
        if (profileResult.ok) {
          const profile = await profileResult.json();
          setCustomer(profile);
        } else {
          clearCustomerTokens();
        }
      } else {
        clearCustomerTokens();
      }

      setLoading(false);
    }

    tryRefresh();
  }, [slug]);

  /**
   * Log in with email and password.
   * @returns Error message string, or null on success.
   */
  const login = useCallback(
    async (email: string, password: string): Promise<string | null> => {
      if (!slug) return "Store not loaded";

      const result = await api.post<TokenResponse>(
        `/api/v1/public/stores/${slug}/customers/login`,
        { email, password }
      );

      if (result.error) return result.error.message;
      if (!result.data) return "Unknown error";

      setCustomerTokens(result.data.access_token, result.data.refresh_token);
      setCustomer(result.data.customer);
      return null;
    },
    [slug]
  );

  /**
   * Register a new customer account.
   * @returns Error message string, or null on success.
   */
  const register = useCallback(
    async (
      email: string,
      password: string,
      firstName?: string,
      lastName?: string
    ): Promise<string | null> => {
      if (!slug) return "Store not loaded";

      const result = await api.post<TokenResponse>(
        `/api/v1/public/stores/${slug}/customers/register`,
        {
          email,
          password,
          first_name: firstName || null,
          last_name: lastName || null,
        }
      );

      if (result.error) return result.error.message;
      if (!result.data) return "Unknown error";

      setCustomerTokens(result.data.access_token, result.data.refresh_token);
      setCustomer(result.data.customer);
      return null;
    },
    [slug]
  );

  /**
   * Log out and clear all tokens.
   */
  const logout = useCallback(() => {
    clearCustomerTokens();
    setCustomer(null);
  }, []);

  return (
    <CustomerAuthContext.Provider
      value={{ customer, loading, login, register, logout, getAuthHeaders }}
    >
      {children}
    </CustomerAuthContext.Provider>
  );
}

/**
 * Hook to access customer auth state and actions.
 *
 * @returns The customer auth context value.
 *
 * @example
 * ```tsx
 * const { customer, login, logout, loading } = useCustomerAuth();
 * ```
 */
export function useCustomerAuth(): CustomerAuthContextValue {
  return useContext(CustomerAuthContext);
}
