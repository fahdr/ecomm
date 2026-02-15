# End User Guide

> Part of [Admin Dashboard](README.md) documentation

Workflows and feature guides for platform administrators using the Super Admin Dashboard.

## Who This Is For

The Super Admin Dashboard is for **platform operators** who manage the ecomm infrastructure: engineers monitoring service health, operations leads tracking LLM costs, DevOps engineers configuring AI providers, product owners reviewing uptime.

**Not for:** Store owners (use Dropshipping Dashboard), end customers (use Storefront), or service subscribers (use individual service dashboards).

## Getting Started

### First-Time Login

1. **Create admin account** -- run `POST /api/v1/admin/auth/setup` with `{email, password}`. Only works once.
2. **Log in** -- navigate to `http://localhost:3300`, enter credentials, click "Log In".
3. **Explore** -- use the sidebar: Overview, Providers, Costs, Services.

## Core Workflows

### 1: Check Platform Health

1. Open the **Overview** page (default after login)
2. Check the **Service Health** grid (9 cards) for status badges:
   - **Green (Healthy)** -- responding normally
   - **Amber (Degraded)** -- slow or returning errors
   - **Red (Down)** -- not responding
   - **Gray (Unknown)** -- no health checks yet

**Action:** Green = no action. Amber = monitor. Red = alert DevOps. Gray = run manual check.

### 2: Run a Manual Health Check

1. Open the **Services** page
2. Click the **Refresh** button (top-right)
3. Wait 5-10 seconds for status badges to update

Pings `/api/v1/health` on all 9 services and records response times.

**When to use:** After restarting a service, after a deployment, during incident investigation.

### 3: View LLM Cost Breakdown

1. Open the **Costs** page
2. Review **Summary Cards**: Total Spend, Total Requests, Total Tokens (last 30 days)
3. **By Provider** table: cost per AI vendor with request count and percentage
4. **By Service** table: cost per platform service

**Action:** High costs = consider cheaper models or rate limits. One service dominates = optimize its AI usage. One provider expensive = consider switching.

### 4: Add a New LLM Provider

1. Open **Providers** page, click **Add Provider**
2. Fill: Provider Name, Display Name, API Key, Base URL (optional), Models (comma-separated), RPM, TPM, Priority, Enabled toggle
3. Click **Add Provider**, verify it appears in the grid

### 5: Disable an Expensive Provider

1. Open **Providers**, find the provider card
2. Click **Edit**, toggle **Enabled** to off, click **Save Changes**

Stops routing new requests without deleting configuration. Re-enable anytime.

### 6: Delete a Provider

1. Open **Providers**, find the provider card
2. Click the **trash icon**, confirm deletion

Permanently removes configuration. Historical usage data is preserved. Cannot be undone.

### 7: View Service Uptime History

1. Open **Services**, find the service card, note the current status
2. For detailed history, use the API: `GET /api/v1/admin/health/history?service_name=trendscout&limit=100`

Coming soon: click a service card to open a modal with uptime percentage, response time graph, and recent incidents.

### 8: Log Out

Click **Log Out** (top-right corner) to clear your JWT token and redirect to login.

## Dashboard Pages

| Page | Purpose | Key Elements |
|------|---------|-------------|
| **Overview** | At-a-glance health + costs | KPI cards (cost, requests, cache rate), service health grid |
| **Providers** | Manage LLM providers | Provider cards with status toggle, add/edit dialog, delete confirmation |
| **Costs** | Analyze LLM spending | Summary cards, by-provider table, by-service table |
| **Services** | Detailed service status | Health summary bar, service cards with badges, refresh button |
| **Login** | Admin authentication | Email/password inputs, log in button |

## Tips & Best Practices

1. **Run health checks after deployments** -- verify status turns green; if red, rollback
2. **Monitor costs weekly** -- compare week-over-week to spot anomalies
3. **Keep rate limits realistic** -- match provider's tier limits
4. **Enable multiple providers** for redundancy -- gateway auto-fails over
5. **Use priority to control routing** -- primary at 10, backup at 5
6. **Disable providers instead of deleting** -- preserves config for re-enabling
7. **Log out on shared computers** -- JWT tokens valid for 8 hours

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| "Cannot connect to backend" | Backend offline | Check `curl http://localhost:8300/api/v1/health`; check CORS |
| All services show Down | Services offline or wrong URLs | Check services manually; verify `config.py` URLs |
| Costs page empty | No LLM usage data yet | Verify gateway running; wait for AI requests |
| Provider list empty | No providers configured | Click "Add Provider"; ensure gateway is running |
| Login fails with correct password | Account deactivated or JWT secret changed | Contact DevOps; re-run setup if needed |
| Token expired | JWT tokens expire after 8 hours | Re-enter credentials on login page |

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [QA Engineer Guide](QA_ENGINEER.md)*
