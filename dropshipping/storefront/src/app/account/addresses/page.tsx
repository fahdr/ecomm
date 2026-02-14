/**
 * Customer addresses management page.
 *
 * **For End Users:**
 *   Manage your saved shipping addresses. Add new ones, edit existing
 *   ones, or set a default for faster checkout.
 *
 * **For QA Engineers:**
 *   - Fetches from ``GET /public/stores/{slug}/customers/me/addresses``.
 *   - Create calls ``POST .../addresses``.
 *   - Delete calls ``DELETE .../addresses/{id}``.
 *   - Setting default calls ``POST .../addresses/{id}/default``.
 */

"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";

interface Address {
  id: string;
  label: string;
  name: string;
  line1: string;
  line2: string | null;
  city: string;
  state: string | null;
  postal_code: string;
  country: string;
  phone: string | null;
  is_default: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AddressesPage() {
  const { customer, loading: authLoading, getAuthHeaders } = useCustomerAuth();
  const store = useStore();
  const router = useRouter();
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    if (!authLoading && !customer) {
      router.replace("/account/login");
    }
  }, [customer, authLoading, router]);

  async function fetchAddresses() {
    if (!store) return;
    const res = await fetch(
      `${API_BASE}/api/v1/public/stores/${store.slug}/customers/me/addresses`,
      { headers: getAuthHeaders() }
    );
    if (res.ok) setAddresses(await res.json());
    setLoading(false);
  }

  useEffect(() => {
    if (!customer || !store) return;
    fetchAddresses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customer, store]);

  async function handleDelete(id: string) {
    if (!store) return;
    await fetch(
      `${API_BASE}/api/v1/public/stores/${store.slug}/customers/me/addresses/${id}`,
      { method: "DELETE", headers: getAuthHeaders() }
    );
    setAddresses((prev) => prev.filter((a) => a.id !== id));
  }

  async function handleSetDefault(id: string) {
    if (!store) return;
    await fetch(
      `${API_BASE}/api/v1/public/stores/${store.slug}/customers/me/addresses/${id}/default`,
      { method: "POST", headers: getAuthHeaders() }
    );
    await fetchAddresses();
  }

  async function handleAdd(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!store) return;
    const form = new FormData(e.currentTarget);
    const body = {
      label: form.get("label") as string || "Home",
      name: form.get("name") as string,
      line1: form.get("line1") as string,
      line2: (form.get("line2") as string) || null,
      city: form.get("city") as string,
      state: (form.get("state") as string) || null,
      postal_code: form.get("postal_code") as string,
      country: form.get("country") as string,
      is_default: addresses.length === 0,
    };
    const res = await fetch(
      `${API_BASE}/api/v1/public/stores/${store.slug}/customers/me/addresses`,
      {
        method: "POST",
        headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );
    if (res.ok) {
      setShowForm(false);
      await fetchAddresses();
    }
  }

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="size-6 animate-spin rounded-full border-2 border-theme-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-heading font-bold">Addresses</h1>
        <div className="flex items-center gap-3">
          <Link
            href="/account"
            className="text-sm text-theme-muted hover:text-theme-primary"
          >
            Back to Account
          </Link>
          <button
            onClick={() => setShowForm(!showForm)}
            className="rounded-lg bg-theme-primary px-3 py-1.5 text-sm font-medium text-white hover:opacity-90"
          >
            {showForm ? "Cancel" : "Add Address"}
          </button>
        </div>
      </div>

      {showForm && (
        <form
          onSubmit={handleAdd}
          className="rounded-xl border border-theme bg-theme-surface p-4 mb-6 space-y-3"
        >
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Label</label>
              <input name="label" defaultValue="Home" className="w-full rounded-lg border border-theme bg-transparent px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Full Name *</label>
              <input name="name" required className="w-full rounded-lg border border-theme bg-transparent px-3 py-1.5 text-sm" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Address Line 1 *</label>
            <input name="line1" required className="w-full rounded-lg border border-theme bg-transparent px-3 py-1.5 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Address Line 2</label>
            <input name="line2" className="w-full rounded-lg border border-theme bg-transparent px-3 py-1.5 text-sm" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">City *</label>
              <input name="city" required className="w-full rounded-lg border border-theme bg-transparent px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">State</label>
              <input name="state" className="w-full rounded-lg border border-theme bg-transparent px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">ZIP *</label>
              <input name="postal_code" required className="w-full rounded-lg border border-theme bg-transparent px-3 py-1.5 text-sm" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Country (2-letter code) *</label>
            <input name="country" required maxLength={2} defaultValue="US" className="w-full rounded-lg border border-theme bg-transparent px-3 py-1.5 text-sm" />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-theme-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Save Address
          </button>
        </form>
      )}

      {addresses.length === 0 && !showForm ? (
        <div className="text-center py-16">
          <p className="text-theme-muted mb-4">No saved addresses.</p>
          <button
            onClick={() => setShowForm(true)}
            className="inline-block rounded-lg bg-theme-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Add Your First Address
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {addresses.map((addr) => (
            <div
              key={addr.id}
              className="rounded-xl border border-theme bg-theme-surface p-4"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{addr.label}</span>
                  {addr.is_default && (
                    <span className="rounded-full bg-theme-primary/10 px-2 py-0.5 text-xs font-medium text-theme-primary">
                      Default
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {!addr.is_default && (
                    <button
                      onClick={() => handleSetDefault(addr.id)}
                      className="text-xs text-theme-primary hover:underline"
                    >
                      Set Default
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(addr.id)}
                    className="text-xs text-red-500 hover:text-red-700"
                  >
                    Delete
                  </button>
                </div>
              </div>
              <div className="text-sm text-theme-muted space-y-0.5">
                <p>{addr.name}</p>
                <p>{addr.line1}</p>
                {addr.line2 && <p>{addr.line2}</p>}
                <p>
                  {addr.city}{addr.state ? `, ${addr.state}` : ""} {addr.postal_code}
                </p>
                <p>{addr.country}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
