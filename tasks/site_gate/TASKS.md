# site_gate — tasks

- [x] Branch `site_gate` off `beta_gtm_mvp`
- [x] Backend: `private_mode` setting; `_enforce_private_mode` in
      `get_current_user` + `validate_token_string`;
      `require_admin_when_private` on insights/indices routers
- [x] Backend: `WaitlistSignup` model + `0006_waitlist` migration +
      `app/api/waitlist.py` (public POST, admin GET) + mount
- [x] Tests: `test_waitlist.py` (12), `test_private_mode.py` (inventory
      sweep under lockdown), `test_clerk_authz.py` inventories updated
- [x] Frontend: `src/lib/site-mode.ts`; middleware gate block
- [x] Frontend: extract `landing-page.tsx`; `coming-soon.tsx`,
      `waitlist-form.tsx`, `gated-chrome.tsx`; `page.tsx` switch
- [x] Frontend: legal layout gated chrome; `robots.ts`; legal-page
      noindex when gated; not-found label fix
- [x] Risk register rows R-027, R-028
- [x] Security review: `/security-review` (no findings) + `security-reviewer`
      subagent (APPROVE-WITH-NOTES; all notes addressed — deindex strategy,
      50k waitlist ceiling, no-store, DPDP notice, register wording,
      robots.txt reachability)
- [x] Local verification matrix (curl): all gated routes + unknown paths
      307 to /; open routes 200; robots.txt serves Allow:/ + sitewide
      X-Robots-Tag noindex; waitlist POST ok/dup/422/honeypot/401 matrix
      green; private mode 401s insights/indices/portfolio anon,
      market-status stays 200; coming-soon + legal HTML leak-scanned clean
- [x] Founder demo on local dev servers; founder copy pass on
      `coming-soon.tsx` (final text landed in `b8ba0a4`)
- [x] Coming-soon restyled to design language v2 per founder notes
      (dots at edges, sans wordmark, banded email section, thin
      edge-to-edge footer drench, one-line heading)
- [x] Merge `--no-ff` to `beta_gtm_mvp`; Vercel `SITE_MODE` + Railway
      `PRIVATE_MODE` set BEFORE pushing; pushed 15:47 IST (post-freeze)
- [x] Prod verification (full curl matrix, live waitlist POST, leak
      scan, deindex headers); RESULTS.md written
- [ ] Founder browser check: sign in as admin on marketworks.in and
      confirm the full site renders (needs a real Clerk admin session —
      cannot be curl-verified)
