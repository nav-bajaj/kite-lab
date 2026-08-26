# email_channel — tasks

Branch: `email_channel` off `beta_gtm_mvp` (the live prod branch — NOT
main; see `tasks/site_gate/RESULTS.md`). Commit prefix `email_channel:`.

Deploy constraints inherited from site_gate: no pushes 09:00–15:30 IST
(live services restart), and Railway CLI must be given
`--service kite-lab` explicitly or it targets the options worker.

## Phase 0 — founder decisions (blocks Phase 2)

- [ ] Sender address + display name. Must be a real Google Workspace
      mailbox — SES sends but cannot receive, so replies land in
      Workspace or nowhere
- [ ] Physical postal address for the footer
- [ ] Cadence promise to state in the welcome mail
- [ ] Ratify double opt-in (PLAN §1)
- [ ] Beta users folded in, or list kept separate?
- [ ] Collect an optional first name on the waitlist form? (PLAN §3a)

## Phase 0b — DNS, do before any send (PLAN §2 audit)

- [ ] Publish root SPF for Google Workspace:
      `v=spf1 include:_spf.google.com ~all` — currently MISSING, so
      Workspace-sent mail from @marketworks.in is unauthenticated.
      One SPF record per domain: reconcile, do not add a second
- [ ] Publish DMARC: start `v=DMARC1; p=none; rua=mailto:<inbox>`,
      currently MISSING entirely. Put it up early so aggregate reports
      accumulate before the first blast; tighten to quarantine in Phase 3
- [ ] Re-verify SES DKIM is still SUCCESS in the SES console (set up
      during auth_stack_v2; confirm it did not lapse)
- [ ] Watch the Namecheap doubled-Host gotcha on every record above

## Phase 1 — see the list (no email sent)

- [ ] Alembic revision off `0006_waitlist`: status, tokens, timestamps,
      consent-evidence columns (PLAN §4); idempotent `has_table`-style
      guard, real `downgrade()`
- [ ] Backfill existing rows to a sane status
- [ ] `GET /api/waitlist` returns the new fields; add
      `GET /api/waitlist/export.csv` (admin-only)
- [ ] `WaitlistPanel` in `kite-dashboard/src/components/admin/`, wired
      into `/admin` page beside `FreshnessPanel`; count, status
      breakdown, recent signups, CSV download
- [ ] Tests: new columns, export shape, `require_admin` on the export;
      update `test_clerk_authz.py` ADMIN_ENDPOINTS
- [ ] Remove the `deploy.probe@marketworks.in` row (site_gate leftover)

## Phase 2 — welcome mail + consent

- [ ] SES send helper in kite-api: stdlib `smtplib` + `email.message`,
      multipart HTML + plaintext, `List-Unsubscribe` +
      `List-Unsubscribe-Post` headers, retry with backoff
- [ ] Env: SES SMTP host/port/user/pass + sender identity on Railway
      `kite-lab` (`--service kite-lab`, `--skip-deploys`)
- [ ] React Email scaffold in `kite-dashboard/emails/` — note: import
      from `react-email`, NOT the deprecated `@react-email/components`;
      `render()` is async, always `await`
- [ ] Brand shell partial (`emails/_components/`): header, footer with
      disclaimer + postal address + unsubscribe, colours that survive
      dark-mode auto-inversion, real fallback font (web fonts will not
      load for most recipients — RESEARCH.md)
- [ ] Welcome template + `email export` step; commit exported HTML
- [ ] Token substitution helper — HTML-escaping, closed token list, no
      general templating language
- [ ] `GET /api/waitlist/confirm?token=` and
      `POST /api/waitlist/unsubscribe` (+ token GET landing page)
- [ ] Public confirm / unsubscribe pages in the dashboard — must be added
      to `PUBLIC_WHEN_GATED` in `src/lib/site-mode.ts` or the site gate
      will redirect them to `/` and silently break every email link
- [ ] Wire the welcome send into `POST /api/waitlist`; must not fail the
      signup if the send fails (queue/log and move on)
- [ ] Tests: send-once idempotency, token single-use + expiry, status
      transitions, gate allowlist covers the new public routes

## Phase 3 — deliverability hardening

- [ ] SES configuration set + event destination for bounces/complaints
- [ ] Ingest events → `status` (`bounced` / `complained`); never re-send
      to either
- [ ] Respect the SES account-level suppression list
- [ ] Verify SPF + DKIM + DMARC pass on a real received message (raw
      headers, not a checker's word)
- [ ] Verify one-click unsubscribe actually works from Gmail's UI
- [ ] Seed-inbox render test: Gmail, Outlook, Apple Mail, **light and
      dark on a real device** (preview server is light-only)
- [ ] Risk-register row for the outbound-email surface (PII in transit,
      token design, unsubscribe integrity)

## Phase 4 — newsletter

- [ ] Register `newsletter` format in
      `finance-content-os/registry/content_types.yml` with derivation
      edges from `long_article` / `research_report`
- [ ] SEBI pre-registration constraints as a hard check in the content
      gate for this format (PLAN §2)
- [ ] Newsletter React Email template reusing the brand shell
- [ ] Send runner: dry-run mode, seed-test mode, explicit confirmation
      before a real blast, batched at the SES rate limit, resumable
- [ ] Send log table — who got which issue when, for audit + idempotency
- [ ] First issue drafted, reviewed through the content gate, sent to
      seed, then to the list

## Explicitly out of scope

- Migrating the existing beta users onto this list (Phase 0 decision)
- Per-recipient dynamic content (portfolio data in email) — that is the
  trigger to move to a Node render service, PLAN §3
- Any content that constitutes a recommendation, until the RA
  registration is granted
