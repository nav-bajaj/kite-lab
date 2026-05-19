# Move dashboard to marketworks.in

## Context

`marketworks.in` was just bought via Namecheap. The dashboard currently
lives at `https://kite-lab.vercel.app` (the auto-provisioned Vercel
subdomain). We want the dashboard accessible at `https://marketworks.in`
without disrupting users mid-session.

## Decisions locked

- **Canonical URL:** `https://marketworks.in` (apex). `www.marketworks.in`
  redirects to apex.
- **Backend:** stays at `https://kite-lab-production.up.railway.app` for
  now. Frontend at `marketworks.in` will call it via the existing
  `NEXT_PUBLIC_API_URL` env var. Moving the API to `api.marketworks.in`
  is a separate task — not touched here.
- **Old vercel.app URL:** keep working during transition. Vercel keeps
  the auto-subdomain alive even after a custom domain is added; we'll
  set a redirect from it to `marketworks.in` once DNS is stable.

## Six steps in order

The first 3 are manual UI work in vendor dashboards. The last 3 are code
updates I do here on this branch.

### Step 1 — Vercel: add the custom domain

In **Vercel dashboard → kite-lab project → Settings → Domains**:

1. Click **Add Domain**.
2. Enter `marketworks.in`.
3. Vercel will prompt to also add `www.marketworks.in` — accept; set
   `www` to redirect to apex.
4. Vercel shows you the exact DNS records to configure. Note them:
   - Apex (`@`): an **A record** (typically `76.76.21.21`, but use the
     value Vercel shows).
   - `www`: a **CNAME** to `cname.vercel-dns.com.`.
5. Leave the Vercel screen open — it will start polling for the records
   and auto-issue an SSL cert via Let's Encrypt once they resolve.

### Step 2 — Namecheap: set the DNS records

In **Namecheap → Domain List → marketworks.in → Manage → Advanced DNS**:

1. **Remove** any default Namecheap parking records (CNAME for `www`
   pointing to `parkingpage.namecheap.com`, URL Redirect, etc.).
2. **Add** the records from step 1:

   | Type | Host | Value | TTL |
   |---|---|---|---|
   | A Record | `@` | `76.76.21.21` *(or whatever Vercel showed)* | Automatic |
   | CNAME Record | `www` | `cname.vercel-dns.com.` *(trailing dot)* | Automatic |

3. Save. Propagation usually takes 5–15 min on Namecheap, occasionally up
   to a few hours. Check progress with:
   ```bash
   dig +short marketworks.in
   dig +short www.marketworks.in
   ```
   You want to see Vercel's IPs once DNS has cut over.

4. Once Vercel's UI shows both domains as **Valid Configuration** with
   green checkmarks, SSL is provisioned automatically.

### Step 3 — Google Cloud Console: authorize the new origin

The dashboard signs users in via Google OAuth through NextAuth. Google
will reject sign-in attempts from any origin not on its allowlist.

In **Google Cloud Console → APIs & Services → Credentials → OAuth 2.0
Client IDs → the client used by kite-lab**:

1. **Authorized JavaScript origins** — add:
   - `https://marketworks.in`
   - `https://www.marketworks.in`
   *(keep the existing `https://kite-lab.vercel.app` for transition)*
2. **Authorized redirect URIs** — add:
   - `https://marketworks.in/api/auth/callback/google`
   - `https://www.marketworks.in/api/auth/callback/google`
   *(keep the existing kite-lab.vercel.app callback)*
3. Save. Takes effect within a few minutes.

### Step 4 — Railway: extend `ALLOWED_ORIGINS` (CORS)

The backend's CORS middleware (`kite-api/app/main.py:74-86`) reads
`ALLOWED_ORIGINS` (comma-separated env var) and rejects anything else.
The new dashboard at `marketworks.in` will be a cross-origin caller, so
it must be added.

Run on the dev machine (Railway CLI must be authenticated):

```bash
# Read current value to be safe
railway variables --kv | grep ALLOWED_ORIGINS

# Set new value (keep the old vercel domain for transition)
railway variables set ALLOWED_ORIGINS="https://marketworks.in,https://www.marketworks.in,https://kite-lab.vercel.app"

# Railway auto-redeploys; if not, force it:
railway service redeploy --yes
```

Once `marketworks.in` is stable for a week or two and we're confident no
bookmarks/external links still hit `kite-lab.vercel.app`, drop that
origin from the list.

### Step 5 — Vercel: set NEXTAUTH_URL (if used)

NextAuth needs to know its own canonical URL for OAuth callbacks. In
**Vercel → Project Settings → Environment Variables**, ensure
`NEXTAUTH_URL` is set to `https://marketworks.in` (was
`https://kite-lab.vercel.app`).

If `NEXTAUTH_URL` is unset, NextAuth derives it from the request — that
works but can produce wrong absolute URLs in OAuth flows. Explicit is
better.

After updating, click **Redeploy** on the latest deployment.

### Step 6 — Vercel: redirect kite-lab.vercel.app → marketworks.in

In **Vercel → kite-lab project → Settings → Domains**:

1. Click the `kite-lab.vercel.app` row → **Redirect** → enter
   `marketworks.in` → permanent (308).

Anyone hitting the old URL after that gets a 308 redirect to the new
one.

## Code-side changes (done in this branch)

These are landing on the `move-domain` branch:

- `CLAUDE.md` — production URL table updated to `marketworks.in`;
  Backend stays at the Railway URL.
- `docs/handover.md` — no change (only references the Railway backend,
  not the frontend URL).
- `tasks/security_agent/SETUP.md` — verification `curl -sI` line
  updated to `marketworks.in`.
- `tasks/name_change/PLAN.md` — note that the canonical URL is now
  `marketworks.in`.

`next.config.ts` CSP does **not** change. The CSP defines what the
frontend can connect *to* — the backend Railway URL, Google OAuth
endpoints. The frontend's own origin (`marketworks.in`) doesn't appear
in its own CSP (the browser knows the origin from the URL bar).

`kite-dashboard/src/lib/auth.ts` (NextAuth config) does not need code
changes — NextAuth reads `NEXTAUTH_URL` from env at runtime.

`kite-dashboard/src/lib/api-client.ts` reads `NEXT_PUBLIC_API_URL` at
build time — backend URL unchanged, so no code change.

## Verification — after all six steps

1. **DNS:**
   ```bash
   dig +short marketworks.in   # → Vercel IPs
   dig +short www.marketworks.in   # → cname.vercel-dns.com → Vercel IPs
   ```
2. **SSL:**
   ```bash
   curl -sI https://marketworks.in/ | head -5
   # Expect: HTTP/2 200, valid cert from Let's Encrypt
   ```
3. **Security headers carry over (R-006 should still close):**
   ```bash
   curl -sI https://marketworks.in/ | grep -iE '(content-security|strict-transport|x-frame|permissions)'
   ```
4. **OAuth flow:** open `https://marketworks.in/`, click Sign in with
   Google, confirm the consent screen redirects back to
   `marketworks.in/api/auth/callback/google` (not the old vercel URL)
   and lands on the dashboard.
5. **API calls work cross-origin:** load any dashboard page, open
   browser DevTools → Network tab → confirm calls to
   `kite-lab-production.up.railway.app/api/*` return 200, no CORS
   errors.
6. **Redirect:** visit `https://kite-lab.vercel.app/` — should 308 to
   `https://marketworks.in/`.

If any check fails, the most common culprits are (1) DNS not propagated
yet — wait, or flush DNS with `sudo dscacheutil -flushcache`, (2) CORS
not updated on Railway — re-run step 4, (3) OAuth origin missing —
re-check step 3.

## Out of scope (future work)

- Move the API to `api.marketworks.in` (Railway custom domain + Zerodha
  REDIRECT_URI update + CSP `connect-src` change).
- Email setup at `*@marketworks.in` (Namecheap private email or
  ImprovMX forwarding).
- HSTS preload registration for `marketworks.in` at
  <https://hstspreload.org/> — wait until the setup is stable for
  ~2 weeks.
- Auto-redirect any subdomain (e.g. `app.marketworks.in`) to the apex.
- Custom favicon and 404/login backgrounds matching the Marketworks
  brand.
