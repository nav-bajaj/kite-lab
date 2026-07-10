# Runbook — /insights admin launch (insights_v2 Phase A)

Founder-only production actions to make `/insights` visible to admins on
<https://marketworks.in>. All the code is merged on branch `insights-v2`;
this runbook is the human-in-the-loop part: uploading the data files with a
prod admin JWT and flipping the Vercel env flag. An agent must NOT run these
(they need founder credentials and are prod mutations).

Backend URL: `https://kite-lab-production.up.railway.app`
Frontend: <https://marketworks.in> (Vercel)

## What this fixes

`/insights` 500s in prod because the insight engine reads two data folders
that were never provisioned on the Railway volume:

| Folder (prod read path) | Source on your machine | Size |
|---|---|---|
| `nse500_data_merged` (16y split-adjusted stock panel) | `<repo>/nse500_data_merged` (501 files) | ~105 MB |
| `indices_data_historical` (16y indices + VIX) | `/Users/navdeep/Documents/stock_data/indices_data_full` (143 files) | ~9.5 MB |

Note the rename: the indices panel is built FROM `indices_data_full` but
uploaded AS `indices_data_historical` (the name the engine's path resolver
looks for in prod).

## Prerequisites

1. Branch `insights-v2` merged to `main` and deployed:
   - Railway redeployed (so `init_persistent_storage.sh` has created +
     symlinked `nse500_data_merged`, `indices_data_historical`, `cache/` on
     the volume, and `ALLOWED_UPLOAD_DIRS` accepts the two new targets).
   - Vercel picked up the new build (so the tri-state flag + middleware exist).
   Do the Railway deploy BEFORE uploading — the upload targets only exist
   after the init script runs.
2. Your marketworks account has `publicMetadata.role = "admin"` in Clerk.
3. Local `.venv` active; the two source folders present on disk.

## Step 0 — Get a prod admin JWT

The upload endpoint is behind `require_admin`, which verifies a Clerk session
JWT. Clerk session tokens are short-lived (~60s from when they're minted).

**Preferred — mint a fresh token on demand from the browser console.** This
always returns a brand-new token; the DevTools Network-tab method can hand you
a *stale* one (the header shown belongs to whenever the page last called the
API, which may already be a minute old — a common cause of a 401 on the second
upload):

1. Sign in to <https://marketworks.in> as your admin account.
2. Open DevTools → Console and run:
   ```js
   await window.Clerk.session.getToken()
   ```
3. Copy the printed string (raw JWT — three `eyJ….eyJ….<sig>` segments, no
   `Bearer ` prefix, no quotes) and use it immediately.

The 60s clock starts at mint and includes the local tarball step, so grab the
token right before running, and mint a new one per upload. If you hit
`401 Invalid or expired token`, see Troubleshooting at the bottom — the
1-hour JWT-template token removes the timing pressure entirely.

Export it for the commands below:

```sh
export ADMIN_JWT='<paste token>'
export API=https://kite-lab-production.up.railway.app
```

## Step 1 — Upload the stock panel (nse500_data_merged, ~105 MB)

From the repo root:

```sh
source .venv/bin/activate
python scripts/upload_price_data.py \
  --api-url "$API" \
  --token "$ADMIN_JWT" \
  --target nse500_data_merged
```

The script auto-detects the source at `<repo>/nse500_data_merged`, tarballs
it, and POSTs to `/api/sync/upload-data?target=nse500_data_merged`. Expect
`Success: 501 files written to /app/nse500_data_merged`. This is the big one
(~30-40 MB compressed). The HTTP client waits up to 300s, but the **Clerk
session token only lives ~60s** — if your uplink can't push the tar within
that window the server rejects it mid-upload with `401 Invalid or expired
token`. If that happens, use the longer-lived token in Troubleshooting below.

## Step 2 — Upload the indices panel (indices_data_historical, ~9.5 MB)

This one renames on the way up: source folder is `indices_data_full`, target
is `indices_data_historical`. Use `--source-dir` (a fresh token — see Step 0):

```sh
python scripts/upload_price_data.py \
  --api-url "$API" \
  --token "$ADMIN_JWT" \
  --target indices_data_historical \
  --source-dir /Users/navdeep/Documents/stock_data/indices_data_full
```

Expect `Success: ~143 files written to /app/indices_data_historical`.

## Step 3 — Verify the data landed (before touching the flag)

The insights API is public (read-only), so you can hit it directly without a
token even while the surface is still gated in the UI:

```sh
curl -s "$API/api/insights/reading" -o /dev/null -w "%{http_code}\n"
```

- `200` → the engine found both panels and built a MarketReading. Good.
- `500` → data still missing/misnamed. Re-check the two uploads and that the
  Railway deploy ran the init script (symlinks). Do NOT flip the flag yet.

Optional deeper check:

```sh
curl -s "$API/api/insights/breadth/timeseries?days=20" | head -c 300
```

## Step 4 — Force a fresh cache build (optional)

If you uploaded after the API had already served a (failed) request, its
in-process cache may be stale. Force a rebuild without a redeploy:

```sh
curl -s -X POST "$API/api/insights/cache/clear" \
  -H "Authorization: Bearer $ADMIN_JWT"
# -> {"status":"cleared"}
```

Then re-run the Step 3 `/reading` check.

## Step 5 — Flip the Vercel flag to admin mode

1. Vercel → project → Settings → Environment Variables.
2. Add (Production scope): `NEXT_PUBLIC_INSIGHTS_ACCESS = admin`.
   - `admin` = reachable only by admin-role sessions; clients bounce to
     `/dashboard`; marketing surfaces do NOT advertise it. This is the safe
     pre-public sandbox.
   - Leave any legacy `NEXT_PUBLIC_INSIGHTS_ENABLED` unset/false — if it is
     `true` it maps to `all` (public) and would override the intent. Remove it
     to avoid confusion.
3. Redeploy Production (env changes need a rebuild — `NEXT_PUBLIC_*` is
   inlined at build time). Trigger from Vercel or push an empty commit.

## Post-deploy verification checklist

- [ ] Signed in as **admin**: `/insights` renders (Pulse) with real data; the
      "Insights" item shows in the sidebar (desktop + mobile). Click through
      Pulse / Sectors / Watchlists / Learn — no 500s.
- [ ] Signed in as a **client** account (or an account without the admin
      role): visiting `/insights` redirects to `/dashboard`; no "Insights"
      sidebar item.
- [ ] Signed out: `/insights` redirects to sign-in.
- [ ] Marketing nav + footer on the public landing do NOT list "Insights"
      (correct for `admin` mode; they only appear on `all`).
- [ ] `curl $API/api/insights/reading` → `200`.

## Redeploy-survival check (the whole point of the symlinks)

1. Trigger a Railway redeploy (or wait for the next one).
2. After it's up, re-run `curl $API/api/insights/reading` → still `200`.
   If it 500s after a redeploy, the volume symlinks aren't holding — check
   `scripts/init_persistent_storage.sh` ran and `/data/nse500_data_merged` +
   `/data/indices_data_historical` exist on the volume.

## Step 6 — Confirm daily freshness is scheduled

The daily pipeline now appends new EOD rows onto the long-history panels and
clears the on-disk insight caches (POST_PORTFOLIO steps "Sync insight panels"
+ "Clear insight caches" in `scripts/run_daily_pipeline.py`). Confirm the
production schedule runs `run_daily_pipeline.py` (jobs/schedule API, job
`daily_pipeline`) so `/insights` doesn't go stale.

Note: the pipeline's cache-clear runs in a separate subprocess from the live
API worker, so it refreshes the on-disk pkls but not the worker's in-memory
cache. If a given day's data looks stale in the UI, POST
`/api/insights/cache/clear` (Step 4) or let the next redeploy rebuild it.

## Rollback

Set `NEXT_PUBLIC_INSIGHTS_ACCESS = off` on Vercel + redeploy. The surface
hides and `/insights*` redirects to `/dashboard` again. The uploaded data can
stay on the volume harmlessly.

## Troubleshooting — `401 Invalid or expired token` on upload

The upload endpoint verifies a Clerk **session** JWT, and Clerk session
tokens expire ~60 seconds after they're minted. The backend rejects the
request the instant `exp` passes, so a 401 almost always means the token
aged out — not that anything is wrong with the data or the endpoint.

Order of likelihood:

1. **Stale token (most common).** You reused a token across both uploads, or
   grabbed it more than a minute before running. The small indices upload
   finishes in ~1-2s, so if *it* 401s the token was already dead. **Fix:**
   copy a brand-new token and run the command within a few seconds. Do the
   two uploads as two separate fresh-token runs, not one shared token.
2. **Copy hygiene.** The value must be the raw JWT only — no `Bearer ` prefix,
   no surrounding quotes, no trailing newline. A stray `Bearer ` makes the
   header `Bearer Bearer …` and 401s. Quick sanity check: a Clerk JWT is
   three dot-separated base64 segments (`eyJ….eyJ….<sig>`).
3. **Wrong value.** Copy the `Authorization: Bearer …` request-header value
   (or the `__session` cookie), not some other cookie/CSRF token.

### For the 105 MB stock panel — use a longer-lived token

If a fresh session token still can't push the big tar inside 60s (slow
uplink), mint a longer-lived token via a **Clerk JWT template** instead of
the default session token. It's signed by the same Clerk instance, so it
passes JWKS + issuer verification exactly like a session token — it just
lives longer.

One-time setup (Clerk Dashboard):

1. **JWT Templates → New template.** Name it e.g. `upload`.
2. Set **Token lifetime** to `3600` (1 hour).
3. In the **Claims** editor, include the role claim the backend reads
   (`require_admin` → `_extract_role` reads `metadata.role`):
   ```json
   { "metadata": { "role": "{{user.public_metadata.role}}" } }
   ```
   Save. (The issuer is the same instance issuer the backend pins, so no
   other change is needed.)

Mint one from the browser console on <https://marketworks.in> while signed
in as your admin account:

```js
await window.Clerk.session.getToken({ template: 'upload' })
```

Copy the printed string into `ADMIN_JWT` and run the upload — you now have a
one-hour window instead of 60 seconds. Delete the template afterward if you
prefer not to keep a long-lived admin-token path around.

> Note: the `POST /api/insights/cache/clear` call in Step 4 is a tiny
> request, so a normal fresh session token is fine there.
