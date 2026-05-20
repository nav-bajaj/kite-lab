# Client Portal v1 — Results

**Status:** Shipped to production. Private Beta open with Clerk sign-up allowlist.
**Branch:** `client-portal` → merged to `main` on 2026-05-20.
**Production URL:** <https://marketworks.in>

---

## Summary

Replaced the internal NextAuth + `ALLOWED_EMAILS` whitelist with managed
Clerk authentication. Built a role-gated client portal where invited users
sign in via Google and see the 4 production portfolios; admins keep the
full 7-universe view + Admin engine surface. Wired Cache-Control on read
endpoints, fixed the night-mode toggle bug, and closed the backend
universe-filter defense-in-depth gap (R-022).

Engineering work landed across 9 commits over ~1 day. 277 pytest authz
tests cover the security gate end-to-end.

---

## Phase-by-phase outcome (vs. `PLAN.md` and `TASKS.md`)

| Phase | Planned | Shipped | Commits |
|---|---|---|---|
| Phase −1 — Prereqs | Clerk app, auth methods, env vars, admin emails | All except P-1 (SEBI) and P-4 final legal review — both flagged as long-running business work | (setup only) |
| Phase 0 — Frontend Clerk wiring | 10 items | All 10. ClerkProvider, middleware, sign-in/up, UserButton, api-client + Clerk getToken, NextAuth artifacts deleted | `09e1e1f`, `a58aad6`, `6c5c8df` (CSP follow-ups) |
| Phase 1 — Backend Clerk + require_admin | 9 items + 97-test suite | All 9. JWKS verification, role extraction, `require_admin` on the 17 admin endpoints, `POST /api/auth/token` removed | `2ffdc41` |
| Phase 2 — Client experience | 11 items | 11. Role-gated universe selector, account page (Clerk `<UserProfile>`), terms/privacy/disclaimer pages with Private Beta callouts, persistent disclaimer footer, sidebar hides Admin for non-admins | `821b2a7`, `109c6d4` (CSP fix) |
| Phase 3 — Caching + polish | 7 items | 3 done (3.1 Cache-Control on 20 read endpoints, 3.6 dark-mode bug, 3.2 dev CSP). 3.3/3.4/3.5/3.7 (empty/loading/mobile/perf polish) — deferred to a future UI redesign task per user decision | `3e3749f` |
| Phase 4 — Deferred | Tour, notifications, billing, watchlist | Not built (intentional) | — |
| **R-022 close** (post-merge follow-up) | Frontend universe filter only at merge time | Backend defense-in-depth added: `check_universe_access` on 19 client-read endpoints + 180 new pytest assertions | `6833d3c`, `e5e0057` |
| Docs alignment | Update CLAUDE.md + README + legal copy for Private Beta | Done — SEBI-applied / Private Beta language live on `/disclaimer`, `/terms`, footer; CLAUDE.md describes the role-gated portal; README front-matter notes Private Beta status | `6833d3c` |

---

## Architecture decisions (vs. PLAN.md)

| Decision | Outcome |
|---|---|
| Auth: Clerk vs. roll our own | Clerk. Zero new user/password/OTP tables. JWKS verification on the backend; `publicMetadata.role` surfaced via the `metadata` session claim. |
| Auth methods enabled | **Google only.** Email/password and phone+OTP deferred per the cost + simplicity argument; Clerk dashboard makes those one-toggle additions later. |
| App shape | Same Next.js app, role-gated — no separate client portal app. Justified by the low cost of role-checks vs. the high cost of maintaining two codebases. |
| Backend changes for clients | Cache-Control on the 20 client-read endpoints; no new tables; `Vary`-less because data isn't user-personalised. |
| Universe gating | Frontend filter + (post-merge) backend defense-in-depth via `check_universe_access`. Both verified by 180-test parametrized matrix. |

---

## Production state at completion

| Layer | What's live |
|---|---|
| **Auth** | Clerk (test instance — `pk_test_…` / `sk_test_…`). Sign-up restricted to allowlist. Google OAuth via the existing GCP client (consent screen shows "Marketworks"). |
| **Frontend** (`https://marketworks.in` on Vercel) | Role-gated dashboard. Clients see 4 portfolios (Quality Momentum, Trend Leaders, Core Momentum, Defensive Blend). Admins see all 7 + Admin nav. Persistent disclaimer footer. Legal pages at `/disclaimer`, `/terms`, `/privacy` accessible without auth. |
| **Backend** (`kite-lab-production.up.railway.app`) | Clerk JWT verification via JWKS (RS256, issuer-pinned). 17 admin endpoints behind `require_admin`. 19 universe-taking endpoints behind `check_universe_access`. Cache-Control on the 20 client-read endpoints. |
| **DB** | Unchanged. `allowed_users` table still present but unused. |
| **CSP** | `*.clerk.accounts.dev`, `*.accounts.dev`, `*.clerk.com`, `challenges.cloudflare.com` allowlisted on script/connect/frame-src. R-006 stays Closed. |

---

## Security gate (Phase 1 / R-022 verification)

`kite-api/tests/test_clerk_authz.py` — **277 tests, all passing**.

Matrix coverage:

| Case | Count |
|---|---|
| 17 admin endpoints × {client→403, admin→pass, unauth→401} | 51 |
| 20 client-read endpoints × {client→pass, unauth→401} | 40 |
| 7 public endpoints unauth→pass | 7 |
| 6 edge cases (expired, malformed, missing kid, wrong issuer, no-role default, etc.) | 6 |
| **R-022:** 18 universe endpoints × 3 admin universes × client→403 | 54 |
| **R-022:** 18 universe endpoints × 4 client universes × client→pass | 72 |
| **R-022:** 18 universe endpoints × 3 admin universes × admin→pass | 54 |
| Other parametrized cases | various |

The tests use a locally-generated RSA keypair; the JWKS cache is
monkey-patched so verification is fully offline. `httpx.get` is blocked
at the test level as defense-in-depth so no live Clerk calls happen.

---

## Items deferred (tracked, not blocking)

| Item | Where | Why |
|---|---|---|
| **P-1 / SEBI RA registration** | Business workstream | Long-running. Required before opening sign-ups to the public (currently allowlisted). Legal copy already states "applied for". |
| **P-4 / Final legal review** | `/disclaimer`, `/terms`, `/privacy` | Current copy reflects Private Beta + SEBI-applied state. Full legal review needed before any external launch. |
| **Clerk production-instance promotion** | Clerk dashboard | Currently shipping with `_test_` keys. Promote + rotate to `_live_` when opening to external users. |
| **Phase 4 features** | Tour, notifications, billing, watchlist, broker linkage | Not built in v1 per scope. |
| **UI redesign / polish pass** | 3.3 (empty), 3.4 (loading), 3.5 (mobile), 3.7 (perf) from TASKS.md | User decision: tackle as a separate fresh-scope UI task rather than rolled into v1. |

---

## Verification log

Manual end-to-end checks performed by the user during merge:

- ✅ Sign-in via Google with admin email — lands on dashboard
- ✅ Dashboard data loads (after Railway redeploy + CSP fix for `*.accounts.dev` and dev `localhost:8000`)
- ✅ Universe selector shows 7 portfolios for admin, 4 for client (verified in Clerk by setting `publicMetadata.role = "admin"`)
- ✅ Sidebar hides Admin nav for non-admin role
- ✅ Dark-mode toggle works consistently at night (the `@media (prefers-color-scheme: dark)` override removed in `3e3749f`)
- ✅ `/api/portfolio` returns 200 with cached headers for authenticated users; 401 without token; 403 with client token + admin universe (post-`6833d3c`)
- ✅ 277/277 pytest authz tests pass

Auto-deploy: Vercel + Railway pick up every merge to `main`. Both
deployed cleanly post-merge after two CSP follow-ups during the cutover
(`a58aad6` for Clerk origins; `6c5c8df` for Cloudflare Turnstile;
`13a8fca` for `*.accounts.dev`).

---

## Commit log (chronological)

```
fef2d1d  Add client portal v1 plan: view-only client product on Clerk auth
b9f30a9  client-portal: Add TASKS.md — phased breakdown of the v1 plan
6892b4a  client-portal: Add CLERK_SETUP.md walkthrough for Phase -1
92d2a65  client-portal: gitignore tmp/ for one-off local secret-pasting
09e1e1f  Phase 0: Swap NextAuth → Clerk on the frontend
a58aad6  Phase 0 fix: add Clerk origins to CSP allowlist
6c5c8df  Phase 0 fix: allow Cloudflare Turnstile in CSP (Clerk bot protection)
2ffdc41  Phase 1: backend Clerk JWKS verification + require_admin gating
821b2a7  Phase 2: client experience — role-gated nav, account, legal, footer
109c6d4  Phase 2 fix: CSP allow http://localhost:8000 in dev
3e3749f  Phase 3: Cache-Control headers + dark-mode toggle fix
2fdb35d  Add R-022: backend universe-filter defense-in-depth gap
fdf4a39  Merge client-portal: Clerk auth + role-gated client portal v1
13a8fca  CSP fix: allow Clerk's bare *.accounts.dev (accounts portal)
6833d3c  Close R-022, update CLAUDE.md + README + legal copy for Private Beta
e5e0057  Close R-022 — backend universe filter live in production
```
