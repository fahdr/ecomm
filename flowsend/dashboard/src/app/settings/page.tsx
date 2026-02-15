/**
 * Settings page — profile, email provider, SMS provider, and quick links.
 *
 * Displays the user's profile (email, current plan), email provider
 * configuration (Console, SMTP, SES, SendGrid), SMS provider configuration
 * (Console, Twilio, SNS), and quick links to API Keys and Billing.
 *
 * **For Developers:**
 *   - User email is read from localStorage via `getUserEmail()`.
 *   - Plan info is fetched from `GET /api/v1/billing/overview`.
 *   - Email provider settings are saved to `POST /api/v1/settings/email-provider`.
 *   - SMS provider settings are saved to `POST /api/v1/settings/sms-provider`.
 *   - Provider-specific credential fields are conditionally rendered
 *     based on the selected provider using a switch pattern.
 *   - Sensitive fields (passwords, API keys, tokens) use type="password".
 *
 * **For Project Managers:**
 *   - Email and SMS provider configuration enables multi-provider support.
 *   - "Console" mode is for development (logs to stdout, no real delivery).
 *   - Enterprise customers can bring their own SMTP, SES, SendGrid, Twilio, or SNS credentials.
 *
 * **For QA Engineers:**
 *   - Verify each provider selection shows the correct credential fields.
 *   - Verify the "Console" provider shows no credential fields.
 *   - Test saving with empty required fields (should show validation error).
 *   - Verify toast notifications appear on save success and failure.
 *   - Verify the profile section displays the correct email and plan.
 *   - Test all quick links navigate to valid pages.
 *
 * **For End Users:**
 *   - Configure your email delivery provider (SMTP, AWS SES, or SendGrid).
 *   - Configure your SMS delivery provider (Twilio or AWS SNS).
 *   - Use "Console" mode during development to test without sending real messages.
 *   - View your account information and plan details.
 */

"use client";

import * as React from "react";
import Link from "next/link";
import {
  User,
  Key,
  CreditCard,
  ArrowUpRight,
  Mail,
  MessageSquare,
  Loader2,
  Save,
} from "lucide-react";
import { Shell } from "@/components/shell";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { FadeIn, StaggerChildren, PageTransition } from "@/components/motion";
import { api } from "@/lib/api";
import { getUserEmail } from "@/lib/auth";
import { serviceConfig } from "@/service.config";
import { cn } from "@/lib/utils";

/** Shape of the billing overview response (subset needed for settings). */
interface BillingOverview {
  plan: string;
  status: string;
}

/** Available email provider types. */
type EmailProvider = "console" | "smtp" | "ses" | "sendgrid";

/** Available SMS provider types. */
type SmsProvider = "console" | "twilio" | "sns";

/** Email provider options for the selector. */
const EMAIL_PROVIDERS: { value: EmailProvider; label: string; description: string }[] = [
  { value: "console", label: "Console", description: "Development mode — logs emails to stdout" },
  { value: "smtp", label: "SMTP", description: "Custom SMTP server (Mailgun, Postmark, etc.)" },
  { value: "ses", label: "AWS SES", description: "Amazon Simple Email Service" },
  { value: "sendgrid", label: "SendGrid", description: "Twilio SendGrid email API" },
];

/** SMS provider options for the selector. */
const SMS_PROVIDERS: { value: SmsProvider; label: string; description: string }[] = [
  { value: "console", label: "Console", description: "Development mode — logs SMS to stdout" },
  { value: "twilio", label: "Twilio", description: "Twilio Programmable SMS" },
  { value: "sns", label: "AWS SNS", description: "Amazon Simple Notification Service" },
];

/**
 * Settings page component.
 *
 * Renders profile, email provider config, SMS provider config,
 * quick links, and service info sections.
 *
 * @returns The settings page wrapped in the Shell layout.
 */
export default function SettingsPage() {
  const [email, setEmail] = React.useState<string | null>(null);
  const [plan, setPlan] = React.useState<BillingOverview | null>(null);
  const [loading, setLoading] = React.useState(true);

  /* ── Email provider state ── */
  const [emailProvider, setEmailProvider] = React.useState<EmailProvider>("console");
  const [smtpHost, setSmtpHost] = React.useState("");
  const [smtpPort, setSmtpPort] = React.useState("587");
  const [smtpUsername, setSmtpUsername] = React.useState("");
  const [smtpPassword, setSmtpPassword] = React.useState("");
  const [smtpUseTls, setSmtpUseTls] = React.useState(true);
  const [smtpFromAddress, setSmtpFromAddress] = React.useState("");
  const [smtpFromName, setSmtpFromName] = React.useState("");
  const [sesRegion, setSesRegion] = React.useState("us-east-1");
  const [sesAccessKeyId, setSesAccessKeyId] = React.useState("");
  const [sesSecretAccessKey, setSesSecretAccessKey] = React.useState("");
  const [sesConfigurationSet, setSesConfigurationSet] = React.useState("");
  const [sendgridApiKey, setSendgridApiKey] = React.useState("");
  const [savingEmail, setSavingEmail] = React.useState(false);

  /* ── SMS provider state ── */
  const [smsProvider, setSmsProvider] = React.useState<SmsProvider>("console");
  const [twilioAccountSid, setTwilioAccountSid] = React.useState("");
  const [twilioAuthToken, setTwilioAuthToken] = React.useState("");
  const [twilioFromNumber, setTwilioFromNumber] = React.useState("");
  const [snsRegion, setSnsRegion] = React.useState("us-east-1");
  const [snsAccessKeyId, setSnsAccessKeyId] = React.useState("");
  const [snsSecretAccessKey, setSnsSecretAccessKey] = React.useState("");
  const [savingSms, setSavingSms] = React.useState(false);

  /* ── Toast state ── */
  const [toast, setToast] = React.useState<{ message: string; type: "success" | "error" } | null>(null);

  /**
   * Show a toast notification that auto-dismisses after 3 seconds.
   *
   * @param message - The message to display.
   * @param type - Whether this is a success or error toast.
   */
  function showToast(message: string, type: "success" | "error") {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }

  React.useEffect(() => {
    /* Read email from localStorage */
    setEmail(getUserEmail());

    /* Fetch plan information */
    async function fetchPlan() {
      const { data } = await api.get<BillingOverview>("/api/v1/billing/overview");
      if (data) setPlan(data);
      setLoading(false);
    }
    fetchPlan();
  }, []);

  /**
   * Save email provider settings to the API.
   */
  async function handleSaveEmailProvider() {
    setSavingEmail(true);

    const payload: Record<string, unknown> = { provider: emailProvider };

    switch (emailProvider) {
      case "smtp":
        payload.smtp_host = smtpHost;
        payload.smtp_port = parseInt(smtpPort, 10);
        payload.smtp_username = smtpUsername;
        payload.smtp_password = smtpPassword;
        payload.smtp_use_tls = smtpUseTls;
        payload.from_address = smtpFromAddress;
        payload.from_name = smtpFromName;
        break;
      case "ses":
        payload.ses_region = sesRegion;
        payload.ses_access_key_id = sesAccessKeyId;
        payload.ses_secret_access_key = sesSecretAccessKey;
        payload.ses_configuration_set = sesConfigurationSet || null;
        break;
      case "sendgrid":
        payload.sendgrid_api_key = sendgridApiKey;
        break;
    }

    const { error: apiError } = await api.post(
      "/api/v1/settings/email-provider",
      payload
    );
    setSavingEmail(false);

    if (apiError) {
      showToast(apiError.message, "error");
      return;
    }

    showToast("Email provider settings saved.", "success");
  }

  /**
   * Save SMS provider settings to the API.
   */
  async function handleSaveSmsProvider() {
    setSavingSms(true);

    const payload: Record<string, unknown> = { provider: smsProvider };

    switch (smsProvider) {
      case "twilio":
        payload.twilio_account_sid = twilioAccountSid;
        payload.twilio_auth_token = twilioAuthToken;
        payload.twilio_from_number = twilioFromNumber;
        break;
      case "sns":
        payload.sns_region = snsRegion;
        payload.sns_access_key_id = snsAccessKeyId;
        payload.sns_secret_access_key = snsSecretAccessKey;
        break;
    }

    const { error: apiError } = await api.post(
      "/api/v1/settings/sms-provider",
      payload
    );
    setSavingSms(false);

    if (apiError) {
      showToast(apiError.message, "error");
      return;
    }

    showToast("SMS provider settings saved.", "success");
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div>
            <h2 className="font-heading text-2xl font-bold tracking-tight">
              Settings
            </h2>
            <p className="text-muted-foreground mt-1">
              Manage your account, email delivery, and SMS delivery preferences.
            </p>
          </div>
        </FadeIn>

        <StaggerChildren className="space-y-6" staggerDelay={0.1}>
          {/* ── Profile Section ── */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="size-5 text-primary" />
                </div>
                <div>
                  <CardTitle>Profile</CardTitle>
                  <CardDescription>Your account information</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Email */}
              <div className="flex items-center justify-between py-3 border-b">
                <div>
                  <p className="text-sm font-medium">Email</p>
                  <p className="text-sm text-muted-foreground">
                    {email || "Not available"}
                  </p>
                </div>
              </div>

              {/* Current Plan */}
              <div className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm font-medium">Current Plan</p>
                  {loading ? (
                    <Skeleton className="h-4 w-24 mt-1" />
                  ) : (
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-sm text-muted-foreground capitalize">
                        {plan?.plan || "Free"}
                      </span>
                      <Badge
                        variant={plan?.status === "active" ? "success" : "secondary"}
                        className="text-xs"
                      >
                        {plan?.status || "active"}
                      </Badge>
                    </div>
                  )}
                </div>
                <Button asChild variant="outline" size="sm">
                  <Link href="/billing">
                    Manage
                    <ArrowUpRight className="size-3.5" />
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* ── Email Provider Section ── */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <Mail className="size-5 text-primary" />
                </div>
                <div>
                  <CardTitle>Email Provider</CardTitle>
                  <CardDescription>
                    Configure how FlowSend delivers email campaigns
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Provider selector */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {EMAIL_PROVIDERS.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setEmailProvider(p.value)}
                    className={cn(
                      "rounded-lg border p-3 text-left transition-all hover:border-primary/50",
                      emailProvider === p.value
                        ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                        : "border-border"
                    )}
                  >
                    <p className="text-sm font-medium">{p.label}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 leading-tight">
                      {p.description}
                    </p>
                  </button>
                ))}
              </div>

              {/* SMTP Settings */}
              {emailProvider === "smtp" && (
                <div className="space-y-4 pt-2 border-t">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label htmlFor="smtp-host" className="text-sm font-medium">
                        SMTP Host
                      </label>
                      <Input
                        id="smtp-host"
                        placeholder="smtp.mailgun.org"
                        value={smtpHost}
                        onChange={(e) => setSmtpHost(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <label htmlFor="smtp-port" className="text-sm font-medium">
                        Port
                      </label>
                      <Input
                        id="smtp-port"
                        type="number"
                        placeholder="587"
                        value={smtpPort}
                        onChange={(e) => setSmtpPort(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label htmlFor="smtp-user" className="text-sm font-medium">
                        Username
                      </label>
                      <Input
                        id="smtp-user"
                        placeholder="postmaster@example.com"
                        value={smtpUsername}
                        onChange={(e) => setSmtpUsername(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <label htmlFor="smtp-pass" className="text-sm font-medium">
                        Password
                      </label>
                      <Input
                        id="smtp-pass"
                        type="password"
                        placeholder="Enter SMTP password"
                        value={smtpPassword}
                        onChange={(e) => setSmtpPassword(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label htmlFor="smtp-from-addr" className="text-sm font-medium">
                        From Address
                      </label>
                      <Input
                        id="smtp-from-addr"
                        type="email"
                        placeholder="noreply@example.com"
                        value={smtpFromAddress}
                        onChange={(e) => setSmtpFromAddress(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <label htmlFor="smtp-from-name" className="text-sm font-medium">
                        From Name
                      </label>
                      <Input
                        id="smtp-from-name"
                        placeholder="My Store"
                        value={smtpFromName}
                        onChange={(e) => setSmtpFromName(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <label htmlFor="smtp-tls" className="text-sm font-medium">
                      Use TLS
                    </label>
                    <button
                      id="smtp-tls"
                      type="button"
                      role="switch"
                      aria-checked={smtpUseTls}
                      onClick={() => setSmtpUseTls(!smtpUseTls)}
                      className={cn(
                        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                        smtpUseTls ? "bg-emerald-500" : "bg-muted"
                      )}
                    >
                      <span
                        className={cn(
                          "inline-block size-4 rounded-full bg-white transition-transform",
                          smtpUseTls ? "translate-x-6" : "translate-x-1"
                        )}
                      />
                    </button>
                    <span className="text-sm text-muted-foreground">
                      {smtpUseTls ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                </div>
              )}

              {/* SES Settings */}
              {emailProvider === "ses" && (
                <div className="space-y-4 pt-2 border-t">
                  <div className="space-y-2">
                    <label htmlFor="ses-region" className="text-sm font-medium">
                      AWS Region
                    </label>
                    <Input
                      id="ses-region"
                      placeholder="us-east-1"
                      value={sesRegion}
                      onChange={(e) => setSesRegion(e.target.value)}
                    />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label htmlFor="ses-key" className="text-sm font-medium">
                        Access Key ID
                      </label>
                      <Input
                        id="ses-key"
                        placeholder="AKIAIOSFODNN7EXAMPLE"
                        value={sesAccessKeyId}
                        onChange={(e) => setSesAccessKeyId(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <label htmlFor="ses-secret" className="text-sm font-medium">
                        Secret Access Key
                      </label>
                      <Input
                        id="ses-secret"
                        type="password"
                        placeholder="Enter secret access key"
                        value={sesSecretAccessKey}
                        onChange={(e) => setSesSecretAccessKey(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="ses-config-set" className="text-sm font-medium">
                      Configuration Set{" "}
                      <span className="text-muted-foreground font-normal">(optional)</span>
                    </label>
                    <Input
                      id="ses-config-set"
                      placeholder="my-config-set"
                      value={sesConfigurationSet}
                      onChange={(e) => setSesConfigurationSet(e.target.value)}
                    />
                  </div>
                </div>
              )}

              {/* SendGrid Settings */}
              {emailProvider === "sendgrid" && (
                <div className="space-y-4 pt-2 border-t">
                  <div className="space-y-2">
                    <label htmlFor="sg-key" className="text-sm font-medium">
                      SendGrid API Key
                    </label>
                    <Input
                      id="sg-key"
                      type="password"
                      placeholder="SG.xxxxxxxxxxxxxxxxxxxx"
                      value={sendgridApiKey}
                      onChange={(e) => setSendgridApiKey(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">
                      Create an API key in your SendGrid dashboard with Mail Send permissions.
                    </p>
                  </div>
                </div>
              )}

              {/* Console info */}
              {emailProvider === "console" && (
                <div className="rounded-md bg-muted/50 border p-3">
                  <p className="text-sm text-muted-foreground">
                    Console mode logs all outgoing emails to the server console
                    without actually delivering them. Use this for local
                    development and testing.
                  </p>
                </div>
              )}

              {/* Save button */}
              <div className="flex justify-end pt-2">
                <Button onClick={handleSaveEmailProvider} disabled={savingEmail}>
                  {savingEmail ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Save className="size-4" />
                  )}
                  {savingEmail ? "Saving..." : "Save Email Settings"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* ── SMS Provider Section ── */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                  <MessageSquare className="size-5 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div>
                  <CardTitle>SMS Provider</CardTitle>
                  <CardDescription>
                    Configure how FlowSend delivers SMS campaigns
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Provider selector */}
              <div className="grid grid-cols-3 gap-3">
                {SMS_PROVIDERS.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setSmsProvider(p.value)}
                    className={cn(
                      "rounded-lg border p-3 text-left transition-all hover:border-emerald-400/50",
                      smsProvider === p.value
                        ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/20 ring-1 ring-emerald-500/20"
                        : "border-border"
                    )}
                  >
                    <p className="text-sm font-medium">{p.label}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 leading-tight">
                      {p.description}
                    </p>
                  </button>
                ))}
              </div>

              {/* Twilio Settings */}
              {smsProvider === "twilio" && (
                <div className="space-y-4 pt-2 border-t">
                  <div className="space-y-2">
                    <label htmlFor="twilio-sid" className="text-sm font-medium">
                      Account SID
                    </label>
                    <Input
                      id="twilio-sid"
                      placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      value={twilioAccountSid}
                      onChange={(e) => setTwilioAccountSid(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="twilio-token" className="text-sm font-medium">
                      Auth Token
                    </label>
                    <Input
                      id="twilio-token"
                      type="password"
                      placeholder="Enter auth token"
                      value={twilioAuthToken}
                      onChange={(e) => setTwilioAuthToken(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="twilio-from" className="text-sm font-medium">
                      From Number
                    </label>
                    <Input
                      id="twilio-from"
                      placeholder="+1234567890"
                      value={twilioFromNumber}
                      onChange={(e) => setTwilioFromNumber(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">
                      A Twilio phone number or short code from your account.
                    </p>
                  </div>
                </div>
              )}

              {/* SNS Settings */}
              {smsProvider === "sns" && (
                <div className="space-y-4 pt-2 border-t">
                  <div className="space-y-2">
                    <label htmlFor="sns-region" className="text-sm font-medium">
                      AWS Region
                    </label>
                    <Input
                      id="sns-region"
                      placeholder="us-east-1"
                      value={snsRegion}
                      onChange={(e) => setSnsRegion(e.target.value)}
                    />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label htmlFor="sns-key" className="text-sm font-medium">
                        Access Key ID
                      </label>
                      <Input
                        id="sns-key"
                        placeholder="AKIAIOSFODNN7EXAMPLE"
                        value={snsAccessKeyId}
                        onChange={(e) => setSnsAccessKeyId(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <label htmlFor="sns-secret" className="text-sm font-medium">
                        Secret Access Key
                      </label>
                      <Input
                        id="sns-secret"
                        type="password"
                        placeholder="Enter secret access key"
                        value={snsSecretAccessKey}
                        onChange={(e) => setSnsSecretAccessKey(e.target.value)}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Console info */}
              {smsProvider === "console" && (
                <div className="rounded-md bg-muted/50 border p-3">
                  <p className="text-sm text-muted-foreground">
                    Console mode logs all outgoing SMS messages to the server
                    console without actually delivering them. Use this for local
                    development and testing.
                  </p>
                </div>
              )}

              {/* Save button */}
              <div className="flex justify-end pt-2">
                <Button
                  onClick={handleSaveSmsProvider}
                  disabled={savingSms}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  {savingSms ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Save className="size-4" />
                  )}
                  {savingSms ? "Saving..." : "Save SMS Settings"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* ── Quick Links ── */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Links</CardTitle>
              <CardDescription>
                Navigate to commonly used settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* API Keys Link */}
              <Link
                href="/api-keys"
                className="flex items-center justify-between p-3 rounded-lg border hover:bg-secondary/50 transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="size-9 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Key className="size-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">API Keys</p>
                    <p className="text-xs text-muted-foreground">
                      Create and manage your API keys
                    </p>
                  </div>
                </div>
                <ArrowUpRight className="size-4 text-muted-foreground group-hover:text-foreground transition-colors" />
              </Link>

              {/* Billing Link */}
              <Link
                href="/billing"
                className="flex items-center justify-between p-3 rounded-lg border hover:bg-secondary/50 transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="size-9 rounded-lg bg-primary/10 flex items-center justify-center">
                    <CreditCard className="size-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">Billing</p>
                    <p className="text-xs text-muted-foreground">
                      Manage your subscription and view usage
                    </p>
                  </div>
                </div>
                <ArrowUpRight className="size-4 text-muted-foreground group-hover:text-foreground transition-colors" />
              </Link>
            </CardContent>
          </Card>

          {/* ── Service Info ── */}
          <Card>
            <CardHeader>
              <CardTitle>About</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-lg bg-primary flex items-center justify-center">
                  <span className="text-primary-foreground font-bold font-heading">
                    {serviceConfig.name.charAt(0)}
                  </span>
                </div>
                <div>
                  <p className="font-heading font-bold">{serviceConfig.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {serviceConfig.tagline}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </StaggerChildren>

        {/* ── Toast Notification ── */}
        {toast && (
          <div
            className={cn(
              "fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all duration-300",
              toast.type === "success"
                ? "bg-emerald-600 text-white"
                : "bg-destructive text-destructive-foreground"
            )}
          >
            {toast.message}
          </div>
        )}
      </PageTransition>
    </Shell>
  );
}
