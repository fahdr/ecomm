/**
 * Customer account settings page.
 *
 * **For End Users:**
 *   Update your name, email, or change your password.
 *
 * **For QA Engineers:**
 *   - Profile update calls ``PATCH /public/stores/{slug}/customers/me``.
 *   - Password change calls ``POST .../me/change-password``.
 *   - Success shows a confirmation message.
 */

"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SettingsPage() {
  const { customer, loading: authLoading, getAuthHeaders } = useCustomerAuth();
  const store = useStore();
  const router = useRouter();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [profileMsg, setProfileMsg] = useState<string | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordMsg, setPasswordMsg] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !customer) {
      router.replace("/account/login");
    }
    if (customer) {
      setFirstName(customer.first_name || "");
      setLastName(customer.last_name || "");
    }
  }, [customer, authLoading, router]);

  async function handleProfileUpdate(e: FormEvent) {
    e.preventDefault();
    if (!store) return;
    const res = await fetch(
      `${API_BASE}/api/v1/public/stores/${store.slug}/customers/me`,
      {
        method: "PATCH",
        headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ first_name: firstName, last_name: lastName }),
      }
    );
    if (res.ok) {
      setProfileMsg("Profile updated!");
      setTimeout(() => setProfileMsg(null), 3000);
    }
  }

  async function handlePasswordChange(e: FormEvent) {
    e.preventDefault();
    if (!store) return;
    setPasswordError(null);
    setPasswordMsg(null);

    const res = await fetch(
      `${API_BASE}/api/v1/public/stores/${store.slug}/customers/me/change-password`,
      {
        method: "POST",
        headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      }
    );
    if (res.ok || res.status === 204) {
      setPasswordMsg("Password changed!");
      setCurrentPassword("");
      setNewPassword("");
      setTimeout(() => setPasswordMsg(null), 3000);
    } else {
      const err = await res.json().catch(() => ({}));
      setPasswordError(err.detail || "Failed to change password");
    }
  }

  if (authLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="size-6 animate-spin rounded-full border-2 border-theme-primary border-t-transparent" />
      </div>
    );
  }

  if (!customer) return null;

  return (
    <div className="mx-auto max-w-lg px-4 py-12">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-heading font-bold">Settings</h1>
        <Link
          href="/account"
          className="text-sm text-theme-muted hover:text-theme-primary"
        >
          Back to Account
        </Link>
      </div>

      {/* Profile */}
      <form onSubmit={handleProfileUpdate} className="mb-8">
        <h2 className="font-heading font-semibold mb-4">Profile</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              value={customer.email}
              disabled
              className="w-full rounded-lg border border-theme bg-theme-surface px-3 py-2 text-sm opacity-60"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">
                First Name
              </label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="w-full rounded-lg border border-theme bg-theme-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Last Name
              </label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="w-full rounded-lg border border-theme bg-theme-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary"
              />
            </div>
          </div>
          {profileMsg && (
            <p className="text-sm text-green-600">{profileMsg}</p>
          )}
          <button
            type="submit"
            className="rounded-lg bg-theme-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Save Changes
          </button>
        </div>
      </form>

      {/* Password */}
      <form onSubmit={handlePasswordChange}>
        <h2 className="font-heading font-semibold mb-4">Change Password</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">
              Current Password
            </label>
            <input
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full rounded-lg border border-theme bg-theme-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              New Password
            </label>
            <input
              type="password"
              required
              minLength={6}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full rounded-lg border border-theme bg-theme-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-theme-primary"
            />
          </div>
          {passwordMsg && (
            <p className="text-sm text-green-600">{passwordMsg}</p>
          )}
          {passwordError && (
            <p className="text-sm text-red-600">{passwordError}</p>
          )}
          <button
            type="submit"
            className="rounded-lg bg-theme-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Change Password
          </button>
        </div>
      </form>
    </div>
  );
}
