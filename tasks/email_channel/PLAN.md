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

### Live DNS audit (dug 2026-08-26) — two real gaps

| Record | State |
|---|---|
| `MX marketworks.in` | `smtp.google.com` → **mail is on Google Workspace** |
| `TXT mail.marketworks.in` | `v=spf1 include:amazonses.com ~all` — SES MAIL FROM SPF is live |
| `TXT marketworks.in` (SPF) | **MISSING** — only a google-site-verification string |
| `TXT _dmarc.marketworks.in` | **MISSING — no DMARC policy at all** |

What this means:

- **SES sending will pass SPF** — SPF authenticates the envelope
  (Return-Path) domain, which SES sets to `mail.marketworks.in`, and that
  subdomain is correctly configured. Good.
- **But there is no root SPF**, so anything sent from Google Workspace as
  `@marketworks.in` (a reply, manual outreach) is not SPF-authorised.
  Needs `v=spf1 include:_spf.google.com ~all` at the root — and note the
  two must be reconciled into ONE root record if SES is ever used with
  the root as MAIL FROM. A domain may have only one SPF record.
- **There is no DMARC record.** DKIM and SPF are meaningless to a
  receiver without a policy telling it what to do. Publish at least
  `v=DMARC1; p=none; rua=mailto:...` before the first send, monitor the
  aggregate reports, then tighten to `quarantine`. This is Phase 3 work
  but the record should go up in Phase 2 so reports accumulate.

**SES sends but does not receive.** The `From:` identity must be a real
monitored Google Workspace mailbox, or replies vanish. This is why the
sender-identity decision in Phase 0 is not cosmetic.

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

### Status of this section — read before relying on it

A dedicated compliance research pass was started and **stopped without
reporting**, so nothing above was verified against a current primary
source. What is written here is the **strict reading**, assembled from
general practice. Strict is the safe direction to be wrong in: every item
is either a genuine requirement or good practice regardless, so building
to it cannot get us into trouble — it can only cost effort we might have
saved.

Specifically **unverified**, and worth a lawyer or a proper check before
the first newsletter (not before the welcome mail, which is
transactional and lower risk):

- DPDP Act 2023 — which provisions are actually **in force** in 2026 and
  what the notified rules require for marketing consent, withdrawal
  mechanics, and whether a named grievance officer is mandatory at our
  size.
- The current Gmail/Yahoo **bulk-sender thresholds** — the commonly cited
  figure is 5,000/day to a single provider, which our list will sit well
  under for a long time. Below that threshold one-click unsubscribe and
  DMARC are strongly recommended rather than strictly required. We are
  building them anyway.
- The **SEBI advertisement code** as it applies to an applicant whose RA
  registration is pending — the constraints listed above are the
  conservative reading (no recommendations, no performance claims, no
  implying registration). Whether *any* market commentary is permissible
  pre-registration is the specific question worth professional advice,
  because it decides what the newsletter can contain at all.

Do not treat this section as researched. Treat it as a safe default that
still needs a check before Phase 4.

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

## 3a. Personalisation — do the letters carry the reader's name?

**Today: no. We only collect an email address** — the coming-soon form
has one field. There is no name to greet anyone with.

To change that, add an **optional** first-name field to the waitlist
form. Optional matters: a required field measurably reduces signups, and
this list's whole job is to be easy to join.

Handle the fallback **in Python, before substitution** — pick the whole
greeting string (`"Hi Navdeep,"` vs `"Hi there,"`) and substitute one
token. Do NOT put a conditional in the template. `"Hi ,"` reaching a real
inbox is worse than never using the name at all, and it is exactly the
kind of bug that survives review because the happy path looks fine.

This does not weaken the §3 architecture: a name is one more escaped
token, the same class of thing as the unsubscribe URL. The tripwire is
loops and conditionals, not tokens.

Honest note: name personalisation is weak signal at best, and a research
brand can sound *more* credible with a clean "Hi there" than with
machine-inserted first names. Worth doing because we may want it later
for segmentation; not worth doing for its own sake.

## 3b. Typography — Fraunces and Outfit will NOT render

Being Google Fonts is irrelevant. Google Fonts is a hosting service; the
blocker is that email clients refuse `@font-face` regardless of who
serves the file. Verified against caniemail today: **24.39% overall
support**, and specifically **Gmail does not support custom fonts on any
platform** — desktop webmail, iOS, Android, mobile webmail — it renders
only Roboto and Google Sans because those are embedded in its own
stylesheet. Apple Mail also does not support it. Outlook for Windows
2003–2019 falls back to **Times New Roman**.

So the site's brand faces cannot come along. Design decisions that follow:

- Pick the **fallback stack deliberately** — that is what recipients
  actually see. Georgia is the closest web-safe match for Fraunces'
  warmth; Helvetica/Arial for Outfit.
- Set `mso-generic-font-family` / `mso-font-alt` or old Outlook silently
  serves Times New Roman.
- The email will not look identical to the site, and chasing that is
  wasted effort. Carry the brand through **colour, spacing, layout and
  the wordmark image** instead — those do survive.
- If the wordmark must be the real typeface, ship it as a
  transparent-background PNG (transparent so dark-mode auto-inversion
  does not box it in white).

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
