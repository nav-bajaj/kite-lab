# web_performance — phased tasks

Owners: 🤖 = agent, 👤 = user (review / sign-off).
Risk tags: 🟢 low · 🟡 medium · 🔴 high.
User checks in at the end of **every** phase before the next begins.

---

## Phase 0 — Kill the false login error 🟢🟢🟡 🤖

The bug the user cares about most. Self-contained to the client
data-fetching layer; does not touch backend auth.

- [ ] **0.1** Add `authReady` to `ApiAuthContext` — `true` once Clerk
  `isLoaded` and either a token is set (signed in) or we know we're signed
  out. Don't flip `isLoading` back to `true` on the 50s periodic refresh
  (avoids re-render flicker). 🟢
- [ ] **0.2** Resolve the token at fetch time. Add an async
  token-provider so `apiFetch` can await a ready token instead of reading
  a possibly-null global. Keep the global slot for non-React callers. 🟡
- [ ] **0.3** Gate every authed SWR hook key on `authReady`
  (`useSWR(authReady ? key : null, …)`) so SWR simply waits — no request,
  no 401, no toast — until auth is ready. 🟢
- [ ] **0.4** Rewrite the 401 handler in `swr-config.tsx`: toast only on a
  *genuine* expiry (was-authed → now rejected), de-dupe toasts, and use
  wording that doesn't conflate Clerk session vs. Zerodha broker token. 🟢
- [ ] **0.5** `npm run build` clean; manual login loop shows no false
  toast. 🟢
- [ ] **0.6** 👤 **CHECK-IN** — review diff + confirm the toast is gone.

## Phase 1 — Make it feel instant 🟡 🤖

- [ ] **1.1** localStorage-backed SWR cache `provider` so returning users
  see last data immediately, then revalidate (SWR-versioned, namespaced,
  cleared on sign-out). 🟡
- [ ] **1.2** `keepPreviousData: true` for universe switch + trades
  pagination (no blanking). 🟢
- [ ] **1.3** Route-level `loading.tsx` per dashboard route; ensure
  skeletons match final layout (minimize CLS). 🟢
- [ ] **1.4** `next/dynamic` for Recharts chart components (equity curve,
  drawdown, allocation, heatmap) with skeleton fallback. 🟡
- [ ] **1.5** SWR `preload` on nav hover/focus to warm cache pre-click. 🟢
- [ ] **1.6** `npm run build` clean; spot-check each route.
- [ ] **1.7** 👤 **CHECK-IN**.

## Phase 2 — Smart caching (client + backend) 🟡🔴 🤖

- [ ] **2.1** Align frontend `refreshInterval`s with backend cache
  windows (don't poll faster than data changes). 🟢
- [ ] **2.2** Backend: ETag + `304 Not Modified` on daily endpoints to
  skip payloads when unchanged. 🟡
- [ ] **2.3** Backend: per-universe, per-trading-day in-process TTL cache
  for daily DB endpoints (portfolio/metrics/trades). 🟡
- [ ] **2.4** Re-run `pytest tests/` + `test_clerk_authz.py` (backend
  touched). 🔴 — must stay green; no authz change.
- [ ] **2.5** Decide on Redis (only if >1 Railway dyno). Document
  decision; likely defer. 🟢
- [ ] **2.6** 👤 **CHECK-IN**.

## Phase 3 — Smooth live prices 🟡 🤖

- [ ] **3.1** Gate all polling on market hours (no polling when closed)
  via `useMarketStatus`. 🟢
- [ ] **3.2** Gate polling on tab visibility (Page Visibility API) — pause
  when hidden, resume + revalidate on show. 🟢
- [ ] **3.3** Remove SSE + 10s poll overlap on the positions page (one
  source of truth while the stream is healthy). 🟡
- [ ] **3.4** Animate value changes + show an "as of HH:MM:SS" stamp so
  updates read as smooth, not janky. 🟢
- [ ] **3.5** `npm run build` clean; manual market-hours / closed check.
- [ ] **3.6** 👤 **CHECK-IN**.

## Phase 4 — Mobile + measurement 🟢 🤖

- [ ] **4.1** Network-aware polling (slow down on cellular via Network
  Information API where available). 🟢
- [ ] **4.2** Responsive / lighter charts on small screens. 🟢
- [ ] **4.3** Add Vercel Speed Insights / Web Vitals reporting. 🟢
- [ ] **4.4** Capture a Lighthouse baseline + after numbers; record
  LCP / INP / TTFB deltas in RESULTS.md. 🟢
- [ ] **4.5** 👤 **CHECK-IN**.

## Phase 5 — Security audit of the changes 🟡 🤖

Confirm the performance work introduced no security regressions before
close-out. The data-fetching / caching / auth-readiness changes are
exactly the kind of diff CLAUDE.md says must pass the threat model.

- [ ] **5.1** Run the `security-reviewer` subagent over the full
  `web_performance` diff (auth-context, api-client token provider, SWR
  gating, persisted client cache, backend caching). 🟡
- [ ] **5.2** Run the `/security-audit` skill for the deeper scan
  (gitleaks / bandit / semgrep / npm audit, etc.). 🟢
- [ ] **5.3** Specifically verify: (a) the `authReady` gating and token
  provider never *weaken* authentication — they only change *when* the
  client fetches; (b) the persisted localStorage SWR cache is namespaced
  + cleared on sign-out and can't leak one user's portfolio to another or
  one universe's data across the `check_universe_access` boundary; (c) any
  backend cache keys include the universe + user-scope so cached responses
  can't cross tenants; (d) no CSP / CORS widening crept in. 🟡
- [ ] **5.4** Triage findings; record in RESULTS.md + risk register if a
  row is warranted. 🟢
- [ ] **5.5** 👤 **CHECK-IN** + close-out (write RESULTS.md, flip
  `_meta.yml` to shipped).
