# Marketworks Client Portal — v1 (View-Only, Clerk Auth, Light Footprint)

## Context

Marketworks is opening to external clients. Today the dashboard is a single-tenant internal tool: Google-only login against an `allowed_users` email whitelist, **no role concept**, and every authenticated user can hit all 44 API endpoints including admin/engine ones (jobs, sync, scheduler, headless-login). We need a **client-facing product** where external users sign up (email, Google, or phone+OTP), **view** the model portfolios, performance, rebalances, and trade history — and can do **nothing** to the engine.

**Decisions locked with the user:**
- **Auth:** Clerk (managed) — offloads email + Google + phone-OTP, user storage, verification, and session management entirely. No user/password/OTP tables to build or maintain.
- **Actionability:** View-only model portfolios. No broker linkage. Rebalance pages show "what changed / what to do" as guidance the client executes themselves.
- **Monetization:** Free v1. No billing code; subscription tiers deferred.
- **App shape:** Same Next.js app, role-gated — but **deliberately light in architecture and cost**, because clients only read once-daily data and never trigger compute.

**This task's home:** all planning/tracking docs live in this `tasks/client_portal/` folder (`PLAN.md` = this document, plus `PROGRESS.md` and `RESULTS.md` as execution proceeds).

> **Non-engineering prerequisite to flag (India regulatory):** Publishing buy/sell model portfolios to the public can trigger SEBI Research Analyst / Investment Adviser registration requirements. This is a business/legal gate, not a code task, but go-live depends on it. The product must carry clear "not investment advice" disclaimers and risk disclosures regardless. Treat this as a hard prerequisite owned outside this plan.

## Architecture (light + cheap)

The whole point: clients are **read-only consumers of data that changes once per day** (after the daily pipeline). Lean into that.

- **Auth → Clerk.** Replace NextAuth entirely. Clerk's prebuilt components handle every auth method. Role lives in Clerk `publicMetadata.role` (`"client"` default, `"admin"` set manually in Clerk dashboard). Zero new auth tables.
- **Backend stays read-only for clients.** Swap JWT validation from local HS256 (`/api/auth/token`) to **verifying Clerk session tokens via Clerk's JWKS** (public-key, no shared secret). Extract role from the verified claims.
- **Aggressive caching for client reads.** Client data (portfolio, holdings, metrics, equity curve, trades, rebalance) updates only after the daily sync. Add `Cache-Control` headers (e.g. `s-maxage` a few hours) on the 19 client-read endpoints so Railway/edge serve cached responses — keeps DB load and cost near-zero as users scale.
- **No new compute, no new heavy tables.** Lean on Clerk for profile/identity. Client preferences (theme, default portfolio, tour-seen) stay in localStorage (existing pattern in `universe-context.tsx`). Optional tiny `client_prefs` table only if a real need appears — not in v1.

## Part A — Auth: NextAuth → Clerk

**Frontend (`kite-dashboard/`):**
1. Install `@clerk/nextjs`; remove `next-auth` usage. Wrap the app in `<ClerkProvider>` (root `layout.tsx`).
2. Replace `src/middleware.ts` (currently the NextAuth `auth()` wrapper) with `clerkMiddleware()`. Define public routes (landing, `/sign-in`, `/sign-up`, `/terms`, `/privacy`, `/disclaimer`) and protect everything under `(dashboard)`. Gate `/admin` to `sessionClaims.metadata.role === "admin"`.
3. Replace `src/app/login/page.tsx` with Clerk `<SignIn>` and a new `src/app/sign-up/page.tsx` with `<SignUp>` — both configured for email + Google + phone (Clerk dashboard enables the methods; phone enables SMS OTP). No custom OTP UI needed.
4. Account/profile: mount Clerk `<UserProfile>` at `src/app/(dashboard)/account/page.tsx` — covers name/email/phone management, linked methods, sign-out. Replaces the need to build any settings UI.
5. Rework the API auth bridge: `src/contexts/api-auth-context.tsx` + `src/lib/api-client.ts` currently fetch a custom JWT from `/api/backend-token`. Replace with Clerk's `getToken()` (session JWT) attached as the Bearer token on `apiFetch`. Delete `/api/backend-token`.
6. Replace `useSession`/`signOut` call sites (navbar `src/components/shared/navbar.tsx`, sidebar) with Clerk's `useUser`/`<UserButton>`.
7. Update `src/types/next-auth.d.ts` → remove; add Clerk role typing where needed.

**Backend (`kite-api/`):**
8. `app/auth.py` — replace `decode_token()` HS256 logic with Clerk session-token verification against Clerk JWKS (cache the JWKS). Keep the `get_current_user` interface so the 19 client routes are unchanged. Extract `role` from `publicMetadata` claim.
9. Add a `require_admin` dependency. Apply it to the **25 admin/engine endpoints**: all of `/api/jobs/*`, `/api/sync/*`, `/api/schedule/*`, `POST /api/system/headless-login`, and any other mutation. (Inventory already done — see exploration.) This is the security core: frontend hiding is not enough; the API must reject client-role calls.
10. Remove/retire `POST /api/auth/token` (custom minting) and the `allowed_users` whitelist enforcement path. Config: add `CLERK_JWKS_URL` / `CLERK_ISSUER` / `CLERK_SECRET_KEY` to `app/config.py`; drop `jwt_secret` mint path.
11. `requirements.txt` — add a JWT/JWKS verification lib (e.g. `pyjwt[crypto]` if not present) or Clerk's backend SDK.

## Part B — Client experience (pages & features)

**Reuse as-is (read-only, already client-appropriate):** dashboard/portfolio overview, positions, performance, rebalance views, trades — with their existing SWR hooks (`src/lib/hooks.ts`) and universe-aware fetching.

**v1 client feature set:**
1. **Public marketing/landing page** (unauthenticated `/`) — value prop, the named products, CTA to sign up, links to legal pages. New.
2. **Sign in / Sign up** — Clerk components (email, Google, phone+OTP).
3. **Portfolio browse + detail** — universe selector limited to the **4 client products** (om25_v3, tl25_v3, l6_v2, combo_defensive); hide the 3 legacy research universes (nse500/nifty250/nifty100) from clients via the role. Holdings, allocation pie, value/return cards.
4. **Performance** — equity curve vs benchmark, drawdown, monthly-returns heatmap, metrics grid (CAGR/Sharpe/Sortino/MaxDD).
5. **Rebalance view** — latest adds/drops, "what to do" guidance, rebalance history. Read-only (no order placement).
6. **Trades history** — paginated table + CSV export.
7. **Account** — Clerk `<UserProfile>` (name, phone, email, methods).
8. **Legal pages** — `/terms`, `/privacy`, `/disclaimer` (static MDX/TSX). Persistent "not investment advice" disclaimer in the dashboard footer.
9. **Client nav** — drop Admin; clean sidebar to client routes only.

**Deferred to later phases (explicitly not v1):**
- Onboarding product tour (the earlier driver.js plan — slots in cleanly post-launch).
- Notifications/alerts on rebalance (email/SMS via Clerk or a provider).
- Subscription/billing (Razorpay/Stripe).
- Watchlist / follow, risk-profile questionnaire, connected-broker execution.

## Which portfolios clients see

Expose only the **4 production products** (om25_v3, tl25_v3, l6_v2, combo_defensive). Gate the 3 legacy research universes to admin. Implement by filtering `UNIVERSE_IDS` in `src/lib/universes.ts` by role (and defensively, the backend can reject non-product universes for client-role requests).

## Critical files

**Frontend modify:** `src/middleware.ts` · `src/app/layout.tsx` · `src/app/login/page.tsx` (→ Clerk) · `src/contexts/api-auth-context.tsx` · `src/lib/api-client.ts` · `src/components/shared/navbar.tsx` · `src/components/shared/sidebar.tsx` · `src/components/shared/mobile-sidebar.tsx` · `src/lib/universes.ts` · `package.json` · remove `src/lib/auth.ts`, `src/types/next-auth.d.ts`, `/api/backend-token`.
**Frontend create:** `src/app/(marketing)/page.tsx` (landing) · `src/app/sign-up/page.tsx` · `src/app/(dashboard)/account/page.tsx` · `src/app/terms`, `/privacy`, `/disclaimer` · disclaimer footer component.
**Backend modify:** `kite-api/app/auth.py` (Clerk JWKS verify + `require_admin`) · `kite-api/app/config.py` · `kite-api/requirements.txt` · the 25 admin/engine route files under `kite-api/app/api/` (add `require_admin`) · add `Cache-Control` to the 19 client-read endpoints.
**Reuse:** SWR hook pattern (`src/lib/hooks.ts`), universe context localStorage pattern, all existing chart/table components.

## Phased execution

- **Phase 0 — Clerk wiring (frontend):** ClerkProvider, middleware, sign-in/up pages, UserButton; app boots authenticated via Clerk. Verify locally.
- **Phase 1 — Backend Clerk verification + admin gating:** swap `get_current_user` to JWKS verify; add `require_admin` to all 25 admin endpoints; write tests asserting a client-role token gets 403 on every admin endpoint and 200 on client reads. **This is the security gate — do not skip tests here.**
- **Phase 2 — Client experience:** role-based nav/universe filtering, account page, landing + legal pages, disclaimer footer.
- **Phase 3 — Caching + polish:** `Cache-Control` on client reads, empty/loading states, mobile pass, dark mode check.
- **Phase 4 (later):** onboarding tour, notifications, billing.

## Verification

1. **Backend authz (automated):** pytest — a `client`-role Clerk token returns 403 on each of the 25 admin/engine endpoints and 200 on the 19 client-read endpoints; an `admin`-role token returns 200 on admin endpoints. This is the must-pass gate before any external exposure.
2. **Frontend static:** `cd kite-dashboard && npx tsc --noEmit && npm run lint && npm run build`.
3. **Auth flows (manual, dev server):** sign up via email, via Google, and via phone+OTP; confirm each lands in the dashboard as a `client`; confirm Admin nav hidden and `/admin` redirects; confirm an admin account sees Admin.
4. **Data views:** each client page renders for the 4 products; legacy universes not selectable as a client.
5. **Cost/footprint sanity:** confirm client pages hit only cached read endpoints (no job/sync calls in network tab); confirm no new DB tables added.
6. **Run the dev server and click through the full client journey in a browser** (sign-up → browse → performance → rebalance → trades → account → sign-out) before declaring done.

## Out of scope (flagged)
- SEBI RA/RIA registration and legal copy sign-off (business prerequisite — see note above).
- Billing/subscriptions, notifications/alerts, onboarding tour, connected-broker execution (later phases).
- Migrating existing internal admins off the whitelist beyond setting their Clerk role to `admin`.
