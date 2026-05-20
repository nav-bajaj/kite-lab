# Clerk Setup — Step-by-Step

Single auth method for v1: **Google OAuth only**. Reuses your existing
Google Cloud OAuth client so users see the same consent screen they
already would for the internal dashboard.

Plan: ~10 minutes end-to-end. At the end you'll have 4 env vars to give me.

---

## Step 1 — Create the Clerk account + application

1. Go to <https://dashboard.clerk.com/> → **Sign up** (use your Google account or whichever email you want as the Clerk admin).
2. Once in, click **+ Create application** (or it auto-prompts on first sign-in).
3. **Application name:** `Marketworks`.
4. **Sign-in options:** untick everything *except* **Google**. (Email and password and phone are off in v1.)
5. Click **Create application**.

Clerk lands you on the application's Quickstart page with API keys visible.

---

## Step 2 — Wire your existing Google OAuth client into Clerk

Clerk gives you two options for Google: **Use Clerk's shared Google credentials** (works instantly, but shows "Clerk" branding on the consent screen — feels off for a real product), or **Use your own Google OAuth client** (consent screen says "Marketworks", reuses the existing GCP project).

Go with **your own** — it's the same Google project you set up for the internal Vercel dashboard, takes 2 minutes.

1. In Clerk: **User & Authentication → Social Connections → Google** → toggle **Use custom credentials**.
2. Clerk shows the **Authorized redirect URI** you need to add to Google — something like `https://<your-clerk-domain>.accounts.dev/v1/oauth_callback`. Copy it.
3. Open **Google Cloud Console → APIs & Services → Credentials → click your existing OAuth 2.0 Client ID** (the one currently authorized for `https://marketworks.in`).
4. Under **Authorized redirect URIs**, click **+ Add URI** → paste the Clerk redirect URI. Save.
5. Copy from Google: **Client ID** and **Client Secret**.
6. Back in Clerk: paste **Client ID** and **Client Secret** into the Google connection form. Save.

That's it. Existing JS origins on the Google client (`https://marketworks.in`, `https://www.marketworks.in`) stay valid because Clerk does the OAuth handshake server-to-server.

---

## Step 3 — Confirm role metadata is enabled

Clerk users get a `publicMetadata` JSON blob attached. We'll put `role` there.

1. In Clerk: **User & Authentication → Sessions → Customize session token**.
2. Click **+ Add claim** → key `metadata`, value `{{user.public_metadata}}`. Save.

(This makes `role` from `publicMetadata` visible in the JWT the backend verifies — needed for the `require_admin` dependency.)

---

## Step 4 — Set yourself as the first admin

After Phase 0 is built and you sign in once with Google through the new flow, do this:

1. **Clerk → Users → click your user**.
2. **Public metadata → Edit → paste `{"role": "admin"}` → save.**

Sign out + sign back in (the new role lands in the next session token). You're now an admin.

For v1 you'll do the same for any other admin emails when they sign up.

---

## Step 5 — Copy the 4 env vars I need

In **Clerk → API Keys** for your application, you'll see:

| Variable | Where in Clerk dashboard |
|---|---|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | API Keys → Publishable key (`pk_test_...` in dev, `pk_live_...` in prod) |
| `CLERK_SECRET_KEY` | API Keys → Secret key (`sk_test_...` / `sk_live_...`) |
| `CLERK_JWKS_URL` | API Keys → JWT public keys → "JWKS URL" (e.g. `https://<your-app>.clerk.accounts.dev/.well-known/jwks.json`) |
| `CLERK_ISSUER` | API Keys → JWT public keys → "Issuer" (e.g. `https://<your-app>.clerk.accounts.dev`) |

Paste them in chat (the secret keys are still safe to share in this terminal, but **do not commit them**; we'll set them via the Vercel and Railway dashboards / CLI, never in code).

For dev/test, Clerk gives you a "test" app you can use first; promote to "production" instance later.

---

## What I'll need from you to start Phase 0

Just the 4 env var values above. I'll then:

1. Add them to `.env.local` (your dev machine) — gitignored.
2. Add them to Vercel via `vercel env add` (production) — I'll run that CLI command.
3. Add the **backend ones** (`CLERK_SECRET_KEY`, `CLERK_JWKS_URL`, `CLERK_ISSUER`) to Railway via `railway variables set` — I'll run that too.

You don't need to touch any infra after this — I'll wire it.

---

## Things you do NOT need to do

- Don't add email/password — we deliberately disabled it.
- Don't add phone — deferred to v2.
- Don't migrate any existing user data — Clerk users are net new; the existing `allowed_users` table goes away in Phase 1 (your two emails just sign in via Google and you mark them admin).
- Don't worry about MFA right now — Clerk supports it but it's not on by default; revisit post-launch.
