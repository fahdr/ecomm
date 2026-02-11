/**
 * Currency Settings page.
 *
 * Manages the store's default currency and provides a currency converter
 * tool. Shows the current default currency, allows changing it, and
 * fetches live exchange rates for conversions.
 *
 * **For End Users:**
 *   Set your store's primary currency and use the built-in converter to
 *   check exchange rates. Your product prices will be displayed in the
 *   default currency on your storefront.
 *
 * **For Developers:**
 *   - Fetches current currency via `GET /api/v1/stores/{store_id}/currency`.
 *   - Updates default currency via `PATCH /api/v1/stores/{store_id}/currency`.
 *   - Fetches exchange rates via `GET /api/v1/currencies/rates`.
 *   - Uses `useStore()` context for store ID (provided by the layout).
 *   - Wrapped in `PageTransition` for consistent page-level animations.
 *
 * **For QA Engineers:**
 *   - Verify the current currency displays on page load.
 *   - Verify that changing the currency sends a POST and updates the display.
 *   - Verify that the converter calculates correctly using fetched rates.
 *   - Verify that the converter handles invalid input gracefully.
 *   - Verify that loading states appear while fetching rates.
 *
 * **For Project Managers:**
 *   This page corresponds to Feature 21 (Multi-Currency) in the backlog.
 *   Multi-currency support enables selling to international markets.
 */

"use client";

import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";

/** Shape of the store currency configuration returned by the API. */
interface CurrencyConfig {
  store_id: string;
  base_currency: string;
  display_currencies: string[];
  auto_convert: boolean;
  rounding_method: string;
}

/** Shape of exchange rates returned by the API. */
interface ExchangeRates {
  base: string;
  rates: Record<string, number>;
  updated_at: string;
}

/** Common currency options for display. */
const CURRENCIES = [
  { code: "USD", label: "US Dollar" },
  { code: "EUR", label: "Euro" },
  { code: "GBP", label: "British Pound" },
  { code: "CAD", label: "Canadian Dollar" },
  { code: "AUD", label: "Australian Dollar" },
  { code: "JPY", label: "Japanese Yen" },
  { code: "CNY", label: "Chinese Yuan" },
  { code: "INR", label: "Indian Rupee" },
  { code: "BRL", label: "Brazilian Real" },
  { code: "MXN", label: "Mexican Peso" },
  { code: "KRW", label: "South Korean Won" },
  { code: "SGD", label: "Singapore Dollar" },
  { code: "SEK", label: "Swedish Krona" },
  { code: "NOK", label: "Norwegian Krone" },
  { code: "NZD", label: "New Zealand Dollar" },
];

/**
 * CurrencySettingsPage renders the store currency configuration and
 * a converter tool powered by live exchange rates.
 *
 * Retrieves the store ID from the StoreContext (provided by the parent layout)
 * and fetches the current currency configuration and exchange rates.
 *
 * @returns The rendered currency settings page.
 */
export default function CurrencySettingsPage() {
  const { store: contextStore } = useStore();
  const id = contextStore!.id;
  const { user, loading: authLoading } = useAuth();
  const [config, setConfig] = useState<CurrencyConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Change currency state */
  const [selectedCurrency, setSelectedCurrency] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  /* Converter state */
  const [rates, setRates] = useState<ExchangeRates | null>(null);
  const [ratesLoading, setRatesLoading] = useState(false);
  const [converterAmount, setConverterAmount] = useState("");
  const [converterFrom, setConverterFrom] = useState("USD");
  const [converterTo, setConverterTo] = useState("EUR");
  const [convertedResult, setConvertedResult] = useState<string | null>(null);

  /**
   * Fetch the current currency configuration for this store.
   */
  async function fetchConfig() {
    setLoading(true);
    const result = await api.get<CurrencyConfig>(
      `/api/v1/stores/${id}/currency`
    );
    if (result.error) {
      setError(result.error.message);
    } else if (result.data) {
      setConfig(result.data);
      setSelectedCurrency(result.data.base_currency);
    }
    setLoading(false);
  }

  /**
   * Fetch live exchange rates for the converter tool.
   */
  async function fetchRates() {
    setRatesLoading(true);
    const result = await api.get<ExchangeRates>("/api/v1/currencies/rates");
    if (result.data) {
      setRates(result.data);
    }
    setRatesLoading(false);
  }

  useEffect(() => {
    if (authLoading || !user) return;
    fetchConfig();
    fetchRates();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, user, authLoading]);

  /**
   * Handle the change-currency form submission.
   *
   * @param e - The form submission event.
   */
  async function handleSaveCurrency(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    const result = await api.patch<CurrencyConfig>(
      `/api/v1/stores/${id}/currency`,
      { base_currency: selectedCurrency }
    );

    if (result.error) {
      setSaveError(result.error.message);
    } else if (result.data) {
      setConfig(result.data);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    }
    setSaving(false);
  }

  /**
   * Convert an amount using fetched exchange rates.
   * Uses cross-rate calculation via the base currency.
   */
  function handleConvert() {
    if (!rates || !converterAmount) return;

    const amount = parseFloat(converterAmount);
    if (isNaN(amount)) {
      setConvertedResult("Invalid amount");
      return;
    }

    const fromRate = rates.rates[converterFrom] ?? 1;
    const toRate = rates.rates[converterTo] ?? 1;

    /* Convert: amount in "from" currency -> base -> "to" currency */
    const inBase = amount / fromRate;
    const converted = inBase * toRate;

    setConvertedResult(
      `${amount.toFixed(2)} ${converterFrom} = ${converted.toFixed(2)} ${converterTo}`
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-muted-foreground">Loading currency settings...</p>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        <h1 className="text-2xl font-bold font-heading">Currency</h1>

        {error && (
          <Card className="border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Default Currency */}
        <Card>
          <CardHeader>
            <CardTitle>Default Currency</CardTitle>
            <CardDescription>
              {config
                ? `Your store currently uses ${config.base_currency} as the default currency.`
                : "Configure your store's default currency for product pricing."}
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSaveCurrency}>
            <CardContent className="space-y-4">
              {saveError && (
                <p className="text-sm text-destructive">{saveError}</p>
              )}
              {saveSuccess && (
                <p className="text-sm text-green-600">
                  Currency updated successfully.
                </p>
              )}
              <div className="space-y-2">
                <Label htmlFor="default-currency">Currency</Label>
                <Select
                  value={selectedCurrency}
                  onValueChange={setSelectedCurrency}
                >
                  <SelectTrigger id="default-currency">
                    <SelectValue placeholder="Select currency" />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map((curr) => (
                      <SelectItem key={curr.code} value={curr.code}>
                        {curr.code} -- {curr.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
            <CardFooter className="flex justify-end">
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save Currency"}
              </Button>
            </CardFooter>
          </form>
        </Card>

        <Separator />

        {/* Currency Converter */}
        <Card>
          <CardHeader>
            <CardTitle>Currency Converter</CardTitle>
            <CardDescription>
              Convert amounts between currencies using live exchange rates.
              {rates && (
                <span className="block mt-1 text-xs">
                  Rates updated:{" "}
                  {new Date(rates.updated_at).toLocaleString()}
                </span>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {ratesLoading && (
              <p className="text-sm text-muted-foreground">
                Loading exchange rates...
              </p>
            )}
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="conv-amount">Amount</Label>
                <Input
                  id="conv-amount"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="100.00"
                  value={converterAmount}
                  onChange={(e) => {
                    setConverterAmount(e.target.value);
                    setConvertedResult(null);
                  }}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="conv-from">From</Label>
                <Select value={converterFrom} onValueChange={setConverterFrom}>
                  <SelectTrigger id="conv-from">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map((curr) => (
                      <SelectItem key={curr.code} value={curr.code}>
                        {curr.code}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="conv-to">To</Label>
                <Select value={converterTo} onValueChange={setConverterTo}>
                  <SelectTrigger id="conv-to">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map((curr) => (
                      <SelectItem key={curr.code} value={curr.code}>
                        {curr.code}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Button
              onClick={handleConvert}
              disabled={!rates || !converterAmount}
              className="w-full"
            >
              Convert
            </Button>

            {convertedResult && (
              <div className="rounded-md border bg-muted/30 p-4 text-center">
                <p className="text-lg font-semibold">{convertedResult}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </PageTransition>
  );
}
