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
- [ ] Founder demo on local dev servers; founder copy pass on
      `coming-soon.tsx` placeholders; browser check of admin sign-in
      (needs real Clerk admin session — cannot be curl-verified)
- [ ] Merge `--no-ff` to `beta_gtm_mvp`; set Vercel `SITE_MODE` +
      Railway `PRIVATE_MODE` BEFORE pushing; push after 15:30 IST only
- [ ] Prod verification (curl matrix, live waitlist POST, admin
      click-through); RESULTS.md
