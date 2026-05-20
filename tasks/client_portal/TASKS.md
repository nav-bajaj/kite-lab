# Client Portal — Task List

Concrete actionable breakdown of `PLAN.md`. Tasks are grouped by phase
and tagged for **owner** (👤 = you, 🤖 = me/Claude, ⚙️ = both/coordination)
and **risk** (⚠️ = security-critical, must verify; ⏱️ = blocking).

Endpoint inventory verified live: **46 routes total** across 11 files,
splits as ~17 admin/mutation · ~20 client-read · ~9 unauthenticated
bootstrap. The plan's "25 admin / 19 client" was a close estimate.

---

## Phase −1 — Prerequisites (do these before Phase 0)

| # | Task | Owner | Notes |
|---|---|---|---|
| P-1 | **SEBI RA/RIA registration check** | 👤 ⚠️ | Publishing buy/sell model portfolios to the public can trigger SEBI Research Analyst or Investment Adviser registration. Business + legal gate. Has to be resolved before go-live; doesn't block dev work. |
| P-2 | **Create Clerk app** at clerk.com | 👤 ⏱️ | Free tier covers v1. Note down: Publishable Key, Secret Key, JWKS URL, Issuer URL — needed for env vars. |
| P-3 | **Choose enabled auth methods in Clerk dashboard** | 👤 | Email (free), Google OAuth (free, just paste client_id/secret from the existing Google Cloud project), Phone+OTP (paid — SMS provider, ~$0.01–$0.05/message). Recommendation: enable email + Google in v1; defer phone until first user actually asks. |
| P-4 | **Draft legal copy** | 👤 ⏱️ | Terms of service, Privacy policy, Investment disclaimer ("model portfolios, not advice, no broker linkage, past performance ≠ future returns, SEBI position TBD"). Even rough first drafts suffice for Phase 2 pages. |
| P-5 | **Decide initial admin emails** | 👤 | Which Clerk users get `publicMetadata.role = "admin"` set manually post-signup. Probably just your two emails. |

---

## Phase 0 — Clerk wiring (frontend boots authenticated via Clerk)

Goal: developer can `npm run dev` → see landing → sign in → land on dashboard, all via Clerk. No backend changes yet — frontend talks to backend with the Clerk token but the backend still uses NextAuth-era validation (will reject; that's expected and gets fixed in Phase 1).

| # | Task | Files | Owner |
|---|---|---|---|
| 0.1 | Add Clerk env vars to local `.env.local` + Vercel | `kite-dashboard/.env.local`, Vercel dashboard | ⚙️ |
| 0.2 | Install `@clerk/nextjs`; remove `next-auth` + `@auth/*` from `package.json` deps | `kite-dashboard/package.json` | 🤖 |
| 0.3 | Replace root layout: wrap children in `<ClerkProvider>` | `src/app/layout.tsx` | 🤖 |
| 0.4 | Rewrite `middleware.ts`: `clerkMiddleware()` with public routes (`/`, `/sign-in(.*)`, `/sign-up(.*)`, `/terms`, `/privacy`, `/disclaimer`); protect everything under `(dashboard)`; gate `/admin` to admin role | `src/middleware.ts` | 🤖 ⚠️ |
| 0.5 | Replace `src/app/login/page.tsx` with Clerk `<SignIn />` mounted at `/sign-in/[[...sign-in]]/page.tsx` | new file; delete old `login/page.tsx` | 🤖 |
| 0.6 | Create `src/app/sign-up/[[...sign-up]]/page.tsx` with Clerk `<SignUp />` | new file | 🤖 |
| 0.7 | Replace navbar auth UI (`useSession` → `useUser`, sign-out button → `<UserButton />`) | `src/components/shared/navbar.tsx` | 🤖 |
| 0.8 | Delete NextAuth artifacts | remove `src/lib/auth.ts`, `src/types/next-auth.d.ts`, `src/app/api/auth/[...nextauth]/*`, `src/app/api/backend-token/*` | 🤖 |
| 0.9 | Update `api-client.ts` to attach Clerk token via `getToken()` on every request; remove the `/api/backend-token` fetch | `src/lib/api-client.ts`, `src/contexts/api-auth-context.tsx` | 🤖 |
| 0.10 | Smoke test: `npm run dev`, sign up via email → land on `/`; sign in via Google → land on `/`. Confirm token attached on dashboard API calls (backend will 401 — expected before Phase 1) | manual | 👤 |

**Phase 0 exit gate:** dev server boots, sign-up/sign-in via at least email + Google work, Clerk JWT is in the Authorization header on backend calls. Backend 401s are fine for now.

---

## Phase 1 — Backend Clerk verification + admin gating (SECURITY GATE)

Goal: backend stops accepting NextAuth JWTs and instead verifies Clerk session tokens, extracts role, and **hard-rejects every admin endpoint from a client-role caller**. This is the must-pass gate.

| # | Task | Files | Owner |
|---|---|---|---|
| 1.1 | Endpoint inventory finalization: lock down the admin vs client list. Initial split below; review before applying. | `tasks/client_portal/TASKS.md` (this file) | 👤 ⚠️ |
| 1.2 | Add `pyjwt[crypto]` (or `python-jose[cryptography]` already present) for JWKS verify; add `httpx` JWKS fetcher with module-level cache | `kite-api/requirements.txt`, `kite-api/app/auth.py` | 🤖 |
| 1.3 | Add Clerk config: `CLERK_JWKS_URL`, `CLERK_ISSUER`, optional `CLERK_SECRET_KEY` (for admin SDK calls if needed) | `kite-api/app/config.py`, Railway env vars | ⚙️ |
| 1.4 | Rewrite `app/auth.py`: `get_current_user` now fetches JWKS (cached), verifies the bearer JWT (RS256 + iss + exp + nbf), pulls `sub`, `email`, `publicMetadata.role` from claims. Keep the function signature so existing 20 client endpoints don't change. | `kite-api/app/auth.py` | 🤖 ⚠️ |
| 1.5 | Add `require_admin = Annotated[dict, Depends(_require_admin_role)]` dependency that 403s if role != "admin" | `kite-api/app/auth.py` | 🤖 ⚠️ |
| 1.6 | Apply `require_admin` to **all admin endpoints** (list below) | `kite-api/app/api/jobs.py`, `schedule.py`, `sync.py`, `positions.py` (mutations only), `system.py` (POST /headless-login only) | 🤖 ⚠️ |
| 1.7 | Remove `POST /api/auth/token` (custom HS256 mint) and delete the `allowed_users` enforcement path; keep `GET /api/auth/me`, `GET /api/auth/verify` but rewrite to read from Clerk-verified `current_user` | `kite-api/app/api/auth_routes.py`, `kite-api/app/models/models.py` (AllowedUser stays in DB but enforcement gone) | 🤖 |
| 1.8 | Pytest suite: `tests/test_clerk_authz.py` — given a synthetic client-role JWT, hit every admin endpoint and assert 403; hit every client endpoint and assert 200. Given a synthetic admin-role JWT, hit all and assert no 403s. Use Clerk's test JWT signing or mock JWKS. | `kite-api/tests/test_clerk_authz.py` (new) | 🤖 ⚠️ |
| 1.9 | Manual verify against staging: actual client + admin Clerk users sign in via the frontend, hit endpoints via browser DevTools or curl with their tokens, confirm responses match expectations. | manual | 👤 ⚠️ |

### Endpoint classification (review before 1.6)

**Apply `require_admin` to (17):**
- `kite-api/app/api/jobs.py` — POST `/`, GET `/`, GET `/{job_id}`, GET `/{job_id}/logs`, POST `/{job_id}/cancel` (5)
- `kite-api/app/api/schedule.py` — GET `/`, POST `/`, DELETE `/{job_id}`, POST `/{job_id}/run`, GET `/defaults` (5)
- `kite-api/app/api/sync.py` — POST `/`, POST `/all`, POST `/upload-data` (3)
- `kite-api/app/api/positions.py` — POST `/sync`, POST `/sync-from-csv` (2)
- `kite-api/app/api/system.py` — POST `/headless-login` (1)
- `kite-api/app/api/auth_routes.py` — none (auth-issuing endpoints removed; `/me` and `/verify` stay client-accessible since every user can check their own token)

**Apply `get_current_user` only (client-readable, 20):**
- `kite-api/app/api/portfolio.py` — GET `/`, `/holdings`, `/allocation` (3)
- `kite-api/app/api/positions.py` — GET `/`, `/holdings`, `/quotes`, `/stream` (4)
- `kite-api/app/api/metrics.py` — GET `/`, `/equity-curve`, `/monthly-returns` (3)
- `kite-api/app/api/trades.py` — GET `/`, `/summary`, `/recent`, `/export` (4)
- `kite-api/app/api/rebalance.py` — GET `/status`, `/preview`, `/orders`, `/orders/export`, `/history` (5)
- `kite-api/app/api/auth_routes.py` — GET `/me`, GET `/verify` (2 — non-admin authenticated)

**Stay unauthenticated (9, by design — AD-1 / R-003 in security register):**
- `kite-api/app/api/health.py` — GET `/health` (1)
- `kite-api/app/api/positions.py` — GET `/market-status` (1)
- `kite-api/app/api/system.py` — GET `/status`, `/token`, `/database`, `/sync`, `/login-url`, `/callback` (6 — Zerodha OAuth bootstrap surface)

**Phase 1 exit gate:** pytest passes (`test_clerk_authz.py` all green), and a real client-role Clerk user gets 403 on `/api/jobs` and 200 on `/api/portfolio` via the deployed staging.

---

## Phase 2 — Client experience (pages, role gates, legal)

Goal: external users land on a real product. Admin-only surfaces hidden.

| # | Task | Files | Owner |
|---|---|---|---|
| 2.1 | Role-gate the universe selector: clients see only the 4 product universes (`om25_v3`, `tl25_v3`, `l6_v2`, `combo_defensive`); admins see all 7 | `src/lib/universes.ts`, `src/contexts/universe-context.tsx` | 🤖 |
| 2.2 | Backend defense-in-depth: reject `universe in {nse500, nifty100, nifty250}` for non-admin callers | `kite-api/app/auth.py` (helper) + thin check in portfolio/metrics/trades routes | 🤖 ⚠️ |
| 2.3 | Hide Admin nav item from sidebar + mobile-sidebar when user.role !== "admin" | `src/components/shared/sidebar.tsx`, `src/components/shared/mobile-sidebar.tsx` | 🤖 |
| 2.4 | Account page using Clerk `<UserProfile />` at `/account` | `src/app/(dashboard)/account/page.tsx` (new) | 🤖 |
| 2.5 | Landing page at `/` (when unauthenticated). Hero, named products with one-line value props, "Sign up free" CTA, footer links to terms/privacy/disclaimer | `src/app/(marketing)/page.tsx` (new route group) | 🤖 |
| 2.6 | Authenticated-user routing: if logged in, `/` redirects to `/(dashboard)` | `src/app/(marketing)/page.tsx` (server component check) | 🤖 |
| 2.7 | Static legal pages: `/terms`, `/privacy`, `/disclaimer`. Plain MDX/TSX, no auth required. | `src/app/terms/page.tsx`, `src/app/privacy/page.tsx`, `src/app/disclaimer/page.tsx` | 🤖 + 👤 (copy) |
| 2.8 | Persistent disclaimer footer component in `(dashboard)/layout.tsx`: "Model portfolios, not investment advice. Past performance ≠ future returns." | `src/components/shared/disclaimer-footer.tsx` (new), `src/app/(dashboard)/layout.tsx` | 🤖 + 👤 (final copy) |
| 2.9 | Portfolio name display polish: confirm the universe selector shows "Quality Momentum" / "Trend Leaders" / "Core Momentum" / "Defensive Blend" (already done in `name-change` work; just verify) | manual | 👤 |
| 2.10 | Update `CLAUDE.md` Production Dashboard section to reflect Clerk + client portal; mark roles + which surfaces are public vs gated | `CLAUDE.md` | 🤖 |
| 2.11 | Update README front matter to reference Marketworks + client portal (currently just talks about the internal toolkit) | `README.md` | 🤖 |

**Phase 2 exit gate:** sign up as a new email, see the 4 products + no Admin nav; admin user sees all 7 + Admin nav; legal pages render; disclaimer visible on every dashboard page.

---

## Phase 3 — Caching + polish

Goal: client reads land on cached responses → Railway DB load + cost stay near-zero at any scale.

| # | Task | Files | Owner |
|---|---|---|---|
| 3.1 | Add `Cache-Control: public, max-age=300, s-maxage=14400, stale-while-revalidate=86400` (or similar) to the 20 client-read endpoints. Tune per endpoint: equity curves (4h), trades (1h), live positions (60s), etc. | `kite-api/app/api/portfolio.py`, `metrics.py`, `trades.py`, `rebalance.py`, `positions.py` (excluding /stream) | 🤖 |
| 3.2 | Confirm Railway edge cache picks up the headers (curl `-D -` shows `cf-cache-status: HIT` or Railway-equivalent on second hit) | manual | 👤 |
| 3.3 | Empty-state polish: each page when the user has no data shows a friendly placeholder (currently shows raw empty tables/charts) | various component files | 🤖 |
| 3.4 | Loading-state polish: Skeleton components on every initial fetch (some present, audit the rest) | various | 🤖 |
| 3.5 | Mobile responsive pass: verify every client page renders cleanly at 375px width (iPhone SE baseline) | manual browser test | 👤 + 🤖 fixes |
| 3.6 | Dark mode check: Clerk components inherit the theme; verify no light-on-light text on any new page | manual | 👤 |
| 3.7 | Performance budget: confirm initial page bundle doesn't balloon with Clerk addition (Lighthouse) | manual | 👤 |

**Phase 3 exit gate:** repeated browser refreshes on /portfolio hit cached responses; mobile passes a visual sanity check.

---

## Phase 4 — Deferred (not built in v1, listed for shared memory)

| Item | Trigger |
|---|---|
| Onboarding product tour (driver.js) | After ~5 client signups, if signal/retention suggests confused new users |
| Email/SMS notifications on rebalance day | When clients ask "how do I know when to rebalance?" |
| Subscription/billing (Razorpay) | When monetization is unblocked (SEBI + product-market fit) |
| Watchlist / follow specific products | Real ask from users |
| Risk-profile questionnaire | Tied to SEBI RIA path if pursued |
| Connected-broker execution | Big effort; lots of risk surface; only with strong demand |

---

## Verification (all phases) — run before declaring done

| # | Check | Type |
|---|---|---|
| V-1 | `cd kite-api && pytest tests/test_clerk_authz.py -v` — all green | automated |
| V-2 | `cd kite-dashboard && npx tsc --noEmit` — clean | automated |
| V-3 | `cd kite-dashboard && npm run lint` — clean (R-007 eslint-plugin-security stays at 0 errors) | automated |
| V-4 | `cd kite-dashboard && npm run build` — clean | automated |
| V-5 | Sign up via **email** in browser; land on dashboard as `client`; verify Admin hidden | manual |
| V-6 | Sign up via **Google** in browser; same | manual |
| V-7 | Sign up via **phone+OTP** if enabled in P-3; same | manual |
| V-8 | Set `publicMetadata.role = "admin"` on one Clerk user; verify Admin nav appears and admin endpoints work | manual |
| V-9 | As client, call `/api/jobs` directly in DevTools console → 403 | manual |
| V-10 | As client, browse all 4 products → see data, no errors | manual |
| V-11 | Confirm legacy universes (nse500/nifty100/nifty250) not selectable as client | manual |
| V-12 | Run `/security-audit` skill → 0 new HIGH/CRITICAL findings introduced by this branch | automated + LLM |
| V-13 | Cost sanity: DevTools Network tab on client journey shows no calls to `/api/jobs`, `/api/sync`, `/api/schedule` | manual |

---

## Risks called out

1. **Phase 1 is the security gate.** If `require_admin` is missed on even one mutation endpoint, a client could trigger arbitrary subprocess execution or DB writes. The pytest test is non-negotiable. V-9 catches it from the outside.
2. **JWKS verification correctness.** Wrong algorithm verification (e.g. accepting `alg: none`) is a classic RS256 vuln. Use the library's built-in verifier; don't roll claim parsing.
3. **NextAuth → Clerk transition window.** During Phase 0, frontend uses Clerk but backend still uses NextAuth JWT — so dashboard APIs will 401 until Phase 1 lands. Plan to do 0+1 back-to-back or feature-flag the old auth path during the transition.
4. **Cost surprise from phone+OTP.** A spike of signups burns SMS credits fast. Skipping phone in v1 (P-3 recommendation) avoids this.
5. **SEBI gate.** External-facing buy/sell models may need a registered RA/RIA. Treat as a hard go-live blocker, even if all the engineering is done.

---

## Suggested execution sequence

```
P-1 ─┐
P-2 ─┼─► Phase 0 ─► Phase 1 ─► Phase 2 ─► Phase 3 ─► v1 launch readiness
P-3 ─┤      (FE)       (BE,        (UX,         (perf,
P-4 ─┤              security)   role-gating)   polish)
P-5 ─┘
```

P-1 (SEBI) runs in parallel as a business workstream — must be resolved before public launch but doesn't block engineering.

Total engineering effort estimate (rough): **Phase 0** ~half day, **Phase 1** ~1–1.5 days, **Phase 2** ~1–2 days, **Phase 3** ~half day. **~3–5 days of focused work** end-to-end.
