# email_channel — tasks

Branch: `email_channel` off `beta_gtm_mvp` (the live prod branch — NOT
main; see `tasks/site_gate/RESULTS.md`). Commit prefix `email_channel:`.

Deploy constraints inherited from site_gate, plus one learned on
2026-08-26:

- **No pushes 09:00–15:30 IST** — market hours; a deploy restarts live
  services and the options worker is capturing ticks.
- **Also avoid 15:55–17:30 IST.** 16:00 is the EOD proposed-orders job
  and 16:30 is the daily pipeline. A push in that window restarts the
  API mid-job. The safe windows are before 09:00 or after ~17:30.
- **Railway CLI needs `--service kite-lab`** explicitly, or it targets
  the options worker.
- **Railway keeps logs only for the CURRENT deployment.** Pushing again
  destroys the previous process's logs, so verify a scheduled job BEFORE
  the next deploy, or you lose the evidence. Use the admin
  `GET /api/freshness` endpoint instead — it reads state, not logs.
- **Re-read the clock immediately before deciding to push.** Hours pass
  between turns. On 2026-08-27 a stale 02:25 IST reading was carried
  forward as "03:15 IST" and nearly produced a push recommendation at
  13:28 IST, mid-session with the worker live. `TZ=Asia/Kolkata date`,
  fresh, every time.

## Phase 0 — founder decisions

DECIDED 2026-08-27:
- [x] **Self-hosted**, not a newsletter SaaS. SES + our own Postgres +
      React Email. No new subscription.
- [x] **Sender: `mail@marketworks.in`**, a new Google Workspace mailbox
      the founder is creating. Real monitored inbox — SES cannot receive,
      so replies land here. Never `noreply@`.

DECIDED 2026-08-27 (second round):
- [x] **Postal address** for the footer:
      SCO 185-187, First Floor, Sector 9-C, Madhya Marg, Chandigarh
- [x] **Single opt-in** — NOT double. Founder wants to see how signups
      behave first. Implemented as `WAITLIST_DOUBLE_OPT_IN` (default
      false): signups go straight to `confirmed` and are mailable. The
      confirm-token path is built and tested, so flipping the env var is
      the whole change if complaint rates force it.
- [x] **No first-name field.** Greeting stays generic; nothing to
      personalise, which also keeps the template token-free.
- [~] **Cadence: "daily market updates, weekly product update"** —
      recorded, but see the concern in PLAN §2a before this wording goes
      into the welcome mail.

STILL OPEN:
- [ ] Beta users folded in, or list kept separate? (default: separate)
- [x] `mail@marketworks.in` CONFIRMED RECEIVING (founder, 2026-08-27) —
      a test from an outside address arrived. The reply path works.
      NOTE this proves receiving only; SES sending AS that address is a
      separate direction and is still untested.
- [ ] Resolve the cadence question (PLAN §2a)

## Phase 0b — DNS (PLAN §2 audit)

DONE 2026-08-27, verified on both authoritative nameservers
(`dns1`/`dns2.registrar-servers.com`) and via 8.8.8.8 + 1.1.1.1:

- [x] Root SPF live: `v=spf1 include:_spf.google.com ~all`. Single
      record, no duplicate. Correctly omits `amazonses.com` — SES sends
      with envelope domain `mail.marketworks.in`, which carries its own
      SPF, so the root only needs to cover Google Workspace.
- [x] DMARC live at `_dmarc.marketworks.in`:
      `v=DMARC1; p=none; rua=mailto:mail@marketworks.in`
- [x] Google Workspace DKIM was ALREADY published
      (`google._domainkey.marketworks.in`, valid DKIM1/rsa) — no action
      was needed.
- [x] Sender mailbox `mail@marketworks.in` created.

Outstanding tidy-up and checks:

- [ ] **Delete the stray record at `_dmarc.marketworks.in.marketworks.in`**
      (value `v=DMARC1; p=none;`) — a first attempt where the Host field
      got the FQDN instead of `_dmarc`, so Namecheap doubled it. Harmless
      (nothing resolves that name) but delete it so it does not confuse a
      future audit. In Namecheap the entry to remove is the one whose
      Host reads `_dmarc.marketworks.in`; keep the one reading `_dmarc`.
- [ ] Re-verify SES DKIM is still SUCCESS in the SES console. Cannot be
      checked from outside — SES DKIM selectors are random per-identity
      CNAMEs, so DNS alone will not confirm it. Definitive check is the
      Phase 3 real-send header inspection.
- [ ] Send a test message TO `mail@marketworks.in` from an outside
      address and confirm it lands — SES cannot receive, so this mailbox
      is the only path for replies.
- [ ] After ~2 weeks of DMARC reports, confirm legitimate mail passes,
      then tighten `p=none` → `p=quarantine` (Phase 3)

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

## Phase 4 — newsletter — PARKED, do not start yet

Deliberately deferred (founder discussion 2026-08-27). There is no list
yet, so tooling and format decisions for it are premature. Revisit when
there are enough real confirmed subscribers to be worth writing to, and
when we know we will actually write on a cadence. Phases 1–3 are the
near-term work and stand alone without this.

Also gated on the SEBI question in PLAN §2 — whether any market
commentary is permissible pre-registration decides what a newsletter may
contain at all, and that needs professional advice, not a guess.

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
