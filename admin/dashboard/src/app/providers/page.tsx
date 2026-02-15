/**
 * LLM Provider management page for the Super Admin Dashboard.
 *
 * Lists all configured LLM providers and allows CRUD operations:
 *   - View provider cards with name, status, model count, rate limits
 *   - Add new providers via a dialog form
 *   - Edit existing provider settings
 *   - Delete providers
 *
 * For Developers:
 *   API endpoints used:
 *     GET    /llm/providers         — list all providers
 *     POST   /llm/providers         — create a provider
 *     PATCH  /llm/providers/:id     — update a provider
 *     DELETE /llm/providers/:id     — delete a provider
 *
 * For QA Engineers:
 *   - Test CRUD lifecycle: create, read, update, delete.
 *   - Verify form validation (required fields, format checks).
 *   - Verify error handling when API calls fail.
 *   - Verify the provider list refreshes after mutations.
 *
 * For Project Managers:
 *   This page lets admins manage which AI providers (OpenAI,
 *   Anthropic, etc.) are available to the platform services.
 *
 * For End Users:
 *   This page is exclusively for platform administrators.
 */

"use client";

import { useEffect, useState, FormEvent } from "react";
import {
  BrainCircuit,
  Plus,
  Pencil,
  Trash2,
  X,
  Loader2,
  ToggleLeft,
  ToggleRight,
  Gauge,
} from "lucide-react";
import * as motion from "motion/react-client";
import { AdminShell } from "@/components/admin-shell";
import { adminApi } from "@/lib/api";

/**
 * Shape of a provider response from the admin API.
 */
interface Provider {
  id: string;
  name: string;
  display_name: string;
  base_url: string | null;
  models: string[];
  is_enabled: boolean;
  rate_limit_rpm: number;
  rate_limit_tpm: number;
  priority: number;
  created_at: string;
  updated_at: string;
}

/**
 * Shape of the provider form data for create/edit operations.
 */
interface ProviderFormData {
  name: string;
  display_name: string;
  api_key: string;
  base_url: string;
  models: string;
  is_enabled: boolean;
  rate_limit_rpm: number;
  rate_limit_tpm: number;
  priority: number;
}

/** Default values for a new provider form. */
const EMPTY_FORM: ProviderFormData = {
  name: "",
  display_name: "",
  api_key: "",
  base_url: "",
  models: "",
  is_enabled: true,
  rate_limit_rpm: 60,
  rate_limit_tpm: 100000,
  priority: 10,
};

/**
 * LLM Provider management page component.
 *
 * Renders a grid of provider cards with an add/edit dialog and
 * delete confirmation.
 *
 * @returns The providers management page JSX.
 */
export default function ProvidersPage() {
  /** List of providers from the API. */
  const [providers, setProviders] = useState<Provider[]>([]);

  /** Loading state for the initial fetch. */
  const [loading, setLoading] = useState(true);

  /** Whether the add/edit dialog is open. */
  const [dialogOpen, setDialogOpen] = useState(false);

  /** The provider being edited (null for new provider). */
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);

  /** Form data for the dialog. */
  const [form, setForm] = useState<ProviderFormData>(EMPTY_FORM);

  /** Whether the form is currently submitting. */
  const [submitting, setSubmitting] = useState(false);

  /** Error message for the dialog form. */
  const [formError, setFormError] = useState<string | null>(null);

  /** ID of the provider pending deletion confirmation. */
  const [deletingId, setDeletingId] = useState<string | null>(null);

  /**
   * Fetch all providers from the API.
   */
  const fetchProviders = async () => {
    try {
      const data = await adminApi.get<Provider[]>("/llm/providers");
      setProviders(data || []);
    } catch {
      /* Silently handle — empty list is shown. */
    } finally {
      setLoading(false);
    }
  };

  /** Fetch providers on mount. */
  useEffect(() => {
    fetchProviders();
  }, []);

  /**
   * Open the dialog for adding a new provider.
   */
  const handleAdd = () => {
    setEditingProvider(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setDialogOpen(true);
  };

  /**
   * Open the dialog for editing an existing provider.
   *
   * @param provider - The provider to edit.
   */
  const handleEdit = (provider: Provider) => {
    setEditingProvider(provider);
    setForm({
      name: provider.name,
      display_name: provider.display_name,
      api_key: "",
      base_url: provider.base_url || "",
      models: provider.models.join(", "),
      is_enabled: provider.is_enabled,
      rate_limit_rpm: provider.rate_limit_rpm,
      rate_limit_tpm: provider.rate_limit_tpm,
      priority: provider.priority,
    });
    setFormError(null);
    setDialogOpen(true);
  };

  /**
   * Handle form submission for create or update.
   *
   * @param e - The form submit event.
   */
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);

    try {
      const models = form.models
        .split(",")
        .map((m) => m.trim())
        .filter(Boolean);

      if (editingProvider) {
        /* Update existing provider. */
        const payload: Record<string, unknown> = {
          display_name: form.display_name,
          base_url: form.base_url || null,
          models,
          is_enabled: form.is_enabled,
          rate_limit_rpm: form.rate_limit_rpm,
          rate_limit_tpm: form.rate_limit_tpm,
          priority: form.priority,
        };
        if (form.api_key) {
          payload.api_key = form.api_key;
        }
        await adminApi.patch(`/llm/providers/${editingProvider.id}`, payload);
      } else {
        /* Create new provider. */
        await adminApi.post("/llm/providers", {
          name: form.name,
          display_name: form.display_name,
          api_key: form.api_key,
          base_url: form.base_url || null,
          models,
          is_enabled: form.is_enabled,
          rate_limit_rpm: form.rate_limit_rpm,
          rate_limit_tpm: form.rate_limit_tpm,
          priority: form.priority,
        });
      }

      setDialogOpen(false);
      await fetchProviders();
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Failed to save provider"
      );
    } finally {
      setSubmitting(false);
    }
  };

  /**
   * Delete a provider by ID.
   *
   * @param id - The provider UUID to delete.
   */
  const handleDelete = async (id: string) => {
    try {
      await adminApi.delete(`/llm/providers/${id}`);
      setDeletingId(null);
      await fetchProviders();
    } catch {
      /* Silently handle — provider remains in list. */
    }
  };

  return (
    <AdminShell>
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Page header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="flex items-center justify-between"
        >
          <div>
            <div className="flex items-center gap-3 mb-1">
              <BrainCircuit
                size={20}
                className="text-[var(--admin-primary)]"
              />
              <h1 className="text-lg font-semibold text-[var(--admin-text-primary)]">
                LLM Providers
              </h1>
            </div>
            <p className="text-sm text-[var(--admin-text-muted)]">
              Manage AI provider configurations and API keys
            </p>
          </div>
          <button onClick={handleAdd} className="admin-btn-primary flex items-center gap-2">
            <Plus size={16} />
            Add Provider
          </button>
        </motion.div>

        {/* Provider grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="admin-card p-5 h-40 animate-pulse bg-[var(--admin-bg-surface)]"
              />
            ))}
          </div>
        ) : providers.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="admin-card p-12 text-center"
          >
            <BrainCircuit
              size={40}
              className="mx-auto mb-4 text-[var(--admin-text-muted)]"
            />
            <h3 className="text-sm font-medium text-[var(--admin-text-secondary)] mb-1">
              No providers configured
            </h3>
            <p className="text-xs text-[var(--admin-text-muted)] mb-4">
              Add your first LLM provider to start routing AI requests
            </p>
            <button onClick={handleAdd} className="admin-btn-primary">
              <Plus size={14} className="inline mr-1.5" />
              Add Provider
            </button>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {providers.map((provider, index) => (
              <motion.div
                key={provider.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: 0.05 * index }}
                className="admin-card p-5"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-semibold text-[var(--admin-text-primary)]">
                      {provider.display_name}
                    </h3>
                    <p className="font-data text-[11px] text-[var(--admin-text-muted)]">
                      {provider.name}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {provider.is_enabled ? (
                      <ToggleRight
                        size={20}
                        className="text-[var(--admin-success)]"
                      />
                    ) : (
                      <ToggleLeft
                        size={20}
                        className="text-[var(--admin-text-muted)]"
                      />
                    )}
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div>
                    <p className="text-[10px] text-[var(--admin-text-muted)] uppercase tracking-wider">
                      Models
                    </p>
                    <p className="font-data text-sm font-semibold text-[var(--admin-text-primary)]">
                      {provider.models.length}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[var(--admin-text-muted)] uppercase tracking-wider">
                      RPM
                    </p>
                    <p className="font-data text-sm font-semibold text-[var(--admin-text-primary)]">
                      {provider.rate_limit_rpm}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[var(--admin-text-muted)] uppercase tracking-wider">
                      Priority
                    </p>
                    <p className="font-data text-sm font-semibold text-[var(--admin-text-primary)]">
                      {provider.priority}
                    </p>
                  </div>
                </div>

                {/* Rate limit bar */}
                <div className="mb-4">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Gauge size={12} className="text-[var(--admin-text-muted)]" />
                    <span className="text-[10px] text-[var(--admin-text-muted)] uppercase tracking-wider">
                      TPM Limit
                    </span>
                  </div>
                  <p className="font-data text-xs text-[var(--admin-text-secondary)]">
                    {new Intl.NumberFormat("en-US").format(
                      provider.rate_limit_tpm
                    )}{" "}
                    tokens/min
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-3 border-t border-[var(--admin-border-subtle)]">
                  <button
                    onClick={() => handleEdit(provider)}
                    className="admin-btn-ghost flex items-center gap-1.5 text-xs"
                  >
                    <Pencil size={12} />
                    Edit
                  </button>
                  {deletingId === provider.id ? (
                    <div className="flex items-center gap-2 ml-auto">
                      <span className="text-[11px] text-[var(--admin-danger)]">
                        Delete?
                      </span>
                      <button
                        onClick={() => handleDelete(provider.id)}
                        className="admin-btn-danger text-xs px-3 py-1"
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => setDeletingId(null)}
                        className="admin-btn-ghost text-xs px-3 py-1"
                      >
                        No
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDeletingId(provider.id)}
                      className="ml-auto text-[var(--admin-text-muted)] hover:text-[var(--admin-danger)] transition-colors"
                      aria-label={`Delete ${provider.display_name}`}
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Add/Edit dialog */}
        {dialogOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => setDialogOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.25 }}
              className="relative admin-card w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto"
            >
              {/* Dialog header */}
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-base font-semibold text-[var(--admin-text-primary)]">
                  {editingProvider ? "Edit Provider" : "Add Provider"}
                </h2>
                <button
                  onClick={() => setDialogOpen(false)}
                  className="text-[var(--admin-text-muted)] hover:text-[var(--admin-text-primary)]"
                  aria-label="Close dialog"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Dialog form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Name (only for new providers) */}
                {!editingProvider && (
                  <div>
                    <label className="block text-xs font-medium text-[var(--admin-text-secondary)] mb-1.5 uppercase tracking-wider">
                      Provider Name
                    </label>
                    <input
                      type="text"
                      value={form.name}
                      onChange={(e) =>
                        setForm({ ...form, name: e.target.value })
                      }
                      placeholder="e.g., openai, anthropic, gemini"
                      className="admin-input font-data"
                      required
                    />
                  </div>
                )}

                {/* Display name */}
                <div>
                  <label className="block text-xs font-medium text-[var(--admin-text-secondary)] mb-1.5 uppercase tracking-wider">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={form.display_name}
                    onChange={(e) =>
                      setForm({ ...form, display_name: e.target.value })
                    }
                    placeholder="e.g., OpenAI, Anthropic, Google Gemini"
                    className="admin-input"
                    required
                  />
                </div>

                {/* API key */}
                <div>
                  <label className="block text-xs font-medium text-[var(--admin-text-secondary)] mb-1.5 uppercase tracking-wider">
                    API Key
                    {editingProvider && (
                      <span className="text-[var(--admin-text-muted)] normal-case tracking-normal ml-1">
                        (leave blank to keep current)
                      </span>
                    )}
                  </label>
                  <input
                    type="password"
                    value={form.api_key}
                    onChange={(e) =>
                      setForm({ ...form, api_key: e.target.value })
                    }
                    placeholder="sk-..."
                    className="admin-input font-data"
                    required={!editingProvider}
                  />
                </div>

                {/* Base URL */}
                <div>
                  <label className="block text-xs font-medium text-[var(--admin-text-secondary)] mb-1.5 uppercase tracking-wider">
                    Base URL
                    <span className="text-[var(--admin-text-muted)] normal-case tracking-normal ml-1">
                      (optional)
                    </span>
                  </label>
                  <input
                    type="url"
                    value={form.base_url}
                    onChange={(e) =>
                      setForm({ ...form, base_url: e.target.value })
                    }
                    placeholder="https://api.openai.com/v1"
                    className="admin-input font-data"
                  />
                </div>

                {/* Models */}
                <div>
                  <label className="block text-xs font-medium text-[var(--admin-text-secondary)] mb-1.5 uppercase tracking-wider">
                    Models
                  </label>
                  <input
                    type="text"
                    value={form.models}
                    onChange={(e) =>
                      setForm({ ...form, models: e.target.value })
                    }
                    placeholder="gpt-4o, gpt-4o-mini, gpt-3.5-turbo"
                    className="admin-input font-data"
                  />
                  <p className="text-[10px] text-[var(--admin-text-muted)] mt-1">
                    Comma-separated list of model identifiers
                  </p>
                </div>

                {/* Rate limits and priority */}
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-[var(--admin-text-secondary)] mb-1.5 uppercase tracking-wider">
                      RPM
                    </label>
                    <input
                      type="number"
                      value={form.rate_limit_rpm}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          rate_limit_rpm: parseInt(e.target.value) || 0,
                        })
                      }
                      className="admin-input font-data"
                      min={1}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[var(--admin-text-secondary)] mb-1.5 uppercase tracking-wider">
                      TPM
                    </label>
                    <input
                      type="number"
                      value={form.rate_limit_tpm}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          rate_limit_tpm: parseInt(e.target.value) || 0,
                        })
                      }
                      className="admin-input font-data"
                      min={1}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[var(--admin-text-secondary)] mb-1.5 uppercase tracking-wider">
                      Priority
                    </label>
                    <input
                      type="number"
                      value={form.priority}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          priority: parseInt(e.target.value) || 0,
                        })
                      }
                      className="admin-input font-data"
                      min={1}
                    />
                  </div>
                </div>

                {/* Enabled toggle */}
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() =>
                      setForm({ ...form, is_enabled: !form.is_enabled })
                    }
                    className="flex items-center gap-2 text-sm"
                  >
                    {form.is_enabled ? (
                      <ToggleRight
                        size={24}
                        className="text-[var(--admin-success)]"
                      />
                    ) : (
                      <ToggleLeft
                        size={24}
                        className="text-[var(--admin-text-muted)]"
                      />
                    )}
                    <span
                      className={`text-xs ${
                        form.is_enabled
                          ? "text-[var(--admin-success)]"
                          : "text-[var(--admin-text-muted)]"
                      }`}
                    >
                      {form.is_enabled ? "Enabled" : "Disabled"}
                    </span>
                  </button>
                </div>

                {/* Error */}
                {formError && (
                  <div className="text-sm text-[var(--admin-danger)] bg-[oklch(0.63_0.22_25_/_0.08)] border border-[oklch(0.63_0.22_25_/_0.2)] rounded-lg px-3 py-2">
                    {formError}
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-3 pt-2">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="admin-btn-primary flex items-center gap-2"
                  >
                    {submitting && (
                      <Loader2 size={14} className="animate-spin" />
                    )}
                    {editingProvider ? "Save Changes" : "Add Provider"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setDialogOpen(false)}
                    className="admin-btn-ghost"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </div>
    </AdminShell>
  );
}
