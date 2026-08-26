# email_channel — welcome mail, list management, and the newsletter

## Why

`tasks/site_gate` shipped a public waitlist on 2026-08-26. Right now a
signup writes one row to `waitlist_signups` and **nothing else happens**:
no confirmation to the person who signed up, no notification to us, and
no way to reach the list. Someone who hands over their email today gets
silence, which is the worst possible first impression from a research
brand asking to be trusted.

This task closes that. Three deliverables:

1. **An automatic welcome email** on signup — confirms they joined and
   sets the expectation that updates follow.
2. **A curated list we can actually see and manage** — not a psql query.
3. **A newsletter channel** we can send during the pre-launch period.

## Current state (verified 2026-08-26)

| Thing | State |
|---|---|
| Signup storage | `waitlist_signups` (email, source, created_at), Alembic head `0006_waitlist` |
| Write path | public `POST /api/waitlist` in `kite-api/app/api/waitlist.py` |
| Read path | admin-only `GET /api/waitlist` — curl / browser console only |
| Emails sent | **none** — no email code anywhere in kite-api |
| Rows today | 1 (a deploy-verification probe; see site_gate RESULTS) |

**SES is already production-ready and this is the big head start.**
Granted 2026-08-13: `ProductionAccessEnabled`, 50,000/day at 14/sec,
region `eu-north-1`, account-level BOUNCE + COMPLAINT suppression active.
`marketworks.in` already has verified DKIM (3 CNAMEs) and a MAIL FROM
subdomain from the auth_stack_v2 work — those are DNS-level, so they are
live regardless of which branch is deployed. **We are not warming a cold
domain from zero.** ZeptoMail (Zoho, India-hosted) is signed up and
parked as a fallback.

Known DNS gotcha from that work: Namecheap doubled-Host — records get
published under `x.marketworks.in.marketworks.in` if you paste the FQDN.
Enter host-only values.

## 1. Consent model — decide this first, it drives the schema

**Recommendation: double opt-in.** The signup writes a `pending` row and
sends a confirm link; only a confirmed row may receive a newsletter.

Reasons, in order of weight:

1. **It is the only honest answer to "did this person consent?"** Under
   India's DPDP Act the burden is on us to evidence consent. A confirmed
   click is evidence; an unverified string typed into a public form is
   not.
2. **The form is public and unauthenticated.** Anyone can type anyone
   else's address into it. Without confirmation we would mail people who
   never asked — which is both a complaint-rate problem and, at our
   sending reputation's age, a deliverability problem.
3. It costs us one extra email and a token column.

The cost is real: some people never click, so the mailable list is
smaller than the signup count. That is the correct tradeoff for a
regulated-adjacent brand with a brand-new sending reputation.

## 2. Compliance gates — these are constraints, not preferences

**SEBI (the sharp one).** The Research Analyst registration is
**applied for, not granted**. A newsletter is a far more direct
regulated-communication surface than a gated website: it is push, it is
targeted, and it is retained by the recipient. Hard rules for every
send during this period:

- Never state or imply we are SEBI-registered. (Note the live-mode
  `footer-panel.tsx` bug tracked in site_gate — the same false claim must
  not reach an email template.)
- No stock recommendations, no buy/sell/hold, no target prices.
- No performance or return claims, including backtested figures.
- Educational and explanatory content only; process, methodology, market
  statistics, what we are building.
- Every send carries the same risk disclaimer the site carries.

**Practical consequence for content:** the newsletter during this period
is *"here is how we think and what we are building"*, not *"here is what
the market did and what to do about it."* Treat any draft that reads
like a market call as a blocked send.

**DPDP Act 2023 (India).** Notice at collection (shipped — the
coming-soon form links the privacy policy), purpose limitation, a working
withdrawal mechanism, and a named grievance contact. The privacy policy
must state waitlist collection and deletion-on-request — already flagged
as open in site_gate R-027.

**Bulk-sender mechanics.** One-click unsubscribe (`List-Unsubscribe` and
`List-Unsubscribe-Post`, RFC 8058) on every newsletter, unsubscribe
honoured immediately, physical postal address in the footer, SPF + DKIM +
DMARC aligned. Transactional welcome mail is exempt from unsubscribe
requirements but we will include a link anyway.

*(Section to be finalised against the compliance research pass — the
defaults above are deliberately the strict reading, which research can
only relax.)*

## 3. Architecture — where React Email runs

The tension: React Email is Node/React; our waitlist data and SES path
live in Python on Railway. Full options and tradeoffs are in
`RESEARCH.md`. The decision:

**Author in React Email → `email export` to static HTML → commit the HTML
→ Python substitutes a small number of escaped tokens → send via SES.**

Why this works better here than it looks on paper: **a newsletter is the
same HTML for every recipient except the unsubscribe URL.** There is no
per-recipient dynamic content in anything we plan to send. So the
substitution surface is 1–3 tokens (`{{unsubscribe_url}}`,
`{{confirm_url}}`, optionally `{{preferences_url}}`) — not a templating
language fighting a component tree.

What we get:
- The full React Email authoring and `email dev` preview loop for design.
- No Node runtime in production; no new deployable.
- **One** sending path in Python, shared by welcome and newsletter, so
  bounces, complaints and suppression are handled in one place.
- Blasts run on Railway with no serverless timeout ceiling (a Vercel
  function is a poor place to send to a growing list).

The explicit tripwire: **the first template that needs a loop or a
conditional is the signal to move to a small Node render service.** Do
not grow a Jinja dialect inside exported HTML — React-Email escaping and
Jinja escaping do not compose, and that is an HTML-injection vector in
outbound mail. Substitute only through a single helper that
HTML-escapes, and keep the token list closed.

**Transport: SES SMTP via stdlib `smtplib` + `email.message`, not boto3.**
`boto3` is not currently a kite-api dependency and R-018 (dependency CVE
surface) is an open High row; stdlib costs zero new packages and SES SMTP
credentials are a known quantity here. Accepted downside: no native
suppression-list API and coarser error reporting, so bounce/complaint
handling comes from the SES event stream instead (Phase 3). Revisit
boto3 if we ever need the SES v2 list-management or per-message
telemetry APIs.

## 4. Schema

Extend `waitlist_signups` (new Alembic revision off `0006_waitlist`).
The superset below serves either consent model, so it is safe to build
before §1 is ratified:

| Column | Purpose |
|---|---|
| `status` | `pending` / `confirmed` / `unsubscribed` / `bounced` / `complained` |
| `confirm_token` | unguessable, single-use, expiring |
| `unsubscribe_token` | unguessable, long-lived, per-subscriber |
| `confirmed_at`, `unsubscribed_at` | timestamps |
| `consent_source`, `consent_ip`, `consent_user_agent` | DPDP consent evidence at collection |
| `welcome_sent_at`, `last_sent_at` | send bookkeeping / idempotency |

Only `status = 'confirmed'` is mailable. Sends must be idempotent —
never rely on "did the blast finish?" as state.

## 5. Getting the list automatically

Three layers, cheapest first:

1. **Admin panel** — a `WaitlistPanel` in `kite-dashboard/src/components/admin/`,
   slotted into the existing `/admin` page beside `FreshnessPanel` (the
   pattern is established: 10 panels already live there). Shows count,
   recent signups, status breakdown, and a CSV export. This is the
   answer to "how do I get them automatically" for day-to-day use.
2. **Signup notification** — optional low-volume ping to the founder on
   each new confirmed signup. Cheap; useful while volume is small.
3. **CSV export endpoint** — admin-only, for anything the panel does not
   cover and for taking the list elsewhere if we ever switch providers.

## 6. The newsletter, as content rather than plumbing

The content OS (`/Users/navdeep/finance-content-os`) already registers
reel, carousel, caption, short_article, long_article, research_report and
long_video — **but no email/newsletter format**. Rather than growing a
second content workflow, add `newsletter` as a registered format that is
`derivable_to`/`derivable_from` the existing article types, so it inherits
the frame → dossier → draft → humanizer → reviewer pipeline and the voice
rules already in place.

That means a newsletter is normally *derived* from a published `/library`
piece rather than written from scratch, and it goes through the same
content-quality gate. The SEBI constraints in §2 become a hard check in
that gate for this format specifically.

## 7. Phasing

Each phase is independently shippable and independently useful.

**Phase 1 — see the list.** Schema migration, admin `WaitlistPanel`, CSV
export. No email sent. Ships value immediately with near-zero risk.

**Phase 2 — welcome mail + consent.** SES send helper, React Email
scaffold + welcome template, confirm and unsubscribe endpoints and pages,
wire the send into `POST /api/waitlist`. This is the phase that makes the
form honest.

**Phase 3 — deliverability hardening.** SES configuration set, bounce and
complaint handling into `status`, suppression respect, DMARC check,
`List-Unsubscribe` headers verified in real clients.

**Phase 4 — newsletter.** `newsletter` format in the content OS, a send
runner with dry-run and a hard confirmation step, send log, and the first
issue.

Do not start Phase 4 before Phase 3. Sending a blast without bounce
handling on a young domain is how a sending reputation dies.

## 8. Verification bar

- Real send to a seed set (Gmail, Outlook, Apple Mail) — **light and dark
  mode checked on a real device**, since the React Email preview shows
  light only.
- Confirm and unsubscribe links work from a real inbox, not just curl.
- Unsubscribe genuinely stops sending (assert on `status`, and re-run the
  blast to prove suppression).
- SPF, DKIM and DMARC all pass (check raw headers on a received message).
- Send path is idempotent under retry.
- No new pip dependency added (or, if boto3 is chosen instead, a
  risk-register row for the added surface).
- Backend tests: consent transitions, token single-use and expiry,
  suppression respected, `require_admin` on every new admin route, and
  the authz inventories in `test_clerk_authz.py` updated.

## Open questions for the founder

1. **Sender identity** — `hello@marketworks.in`? `research@`? And the
   display name. Needs to be a real monitored mailbox, not a black hole.
2. **Physical postal address** for the email footer (a legal requirement
   for bulk mail).
3. **Cadence** — weekly, fortnightly, or "when there is something worth
   saying"? The welcome mail should state it, so it should not be
   invented later.
4. **Double opt-in confirmed?** (§1 recommendation.)
5. **Does the existing beta-user list get folded in**, or does the
   waitlist stay separate? They consented to different things, so the
   safe default is separate.
