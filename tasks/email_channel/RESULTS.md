# email_channel — results

**Phases 1 and 2 shipped 2026-08-27.** The waitlist now confirms, welcomes
and lets people leave. Phase 3 (bounce/complaint handling) and Phase 4
(newsletter) remain.

## What is live

| Piece | State |
|---|---|
| Consent schema (migration `0007_waitlist_consent`) | live |
| Admin waitlist panel + CSV export | live |
| Admin list management (delete / promote / send-welcome) | live |
| Welcome email, sent automatically on signup | **live and sending** |
| Unsubscribe (page + RFC 8058 one-click endpoint) | live |
| Confirm endpoint + page | live but inert (single opt-in) |
| Newsletter | not built — parked |

Consent mode is **single opt-in** (`WAITLIST_DOUBLE_OPT_IN=false`). The
double opt-in path is built and tested; flipping the env var is the whole
change.

## Verified end to end on production

- Public signup → row committed → welcome sent, logged
  `sent "You're on the Marketworks waitlist"`.
- Email **landed in the Gmail inbox, not spam**, on the first send from a
  sending reputation with no history. SPF, DKIM and DMARC are working.
- Unsubscribe link opens the page correctly.
- The page **asks before acting**, verified: after the founder followed
  the link the row was still `confirmed`. That is the intended
  asymmetry — a GET that mutates state gets fired by link scanners and
  mail-security prefetchers, which would unsubscribe people who never
  clicked. One-click (RFC 8058) is the exception and POSTs directly.
- Site gate survived: `/unsubscribe` and `/confirm` return 200 while
  `/library`, `/dashboard`, `/insights` still 307 to `/`.
- List state: 3 rows, all confirmed, all mailable. The deploy-probe row
  is deleted.

## Two production-only failures the seed test caught

Neither was reachable by unit tests. Both are the reason we sent to a real
inbox before letting signups mail anyone.

### Railway blocks outbound SMTP on port 587

The first send failed with a bare `TimeoutError` on `socket.connect` —
the connection hangs and dies with **nothing in the SES console**, because
it never arrives. Very easy to misdiagnose as bad credentials.

Confirmed platform-side: from a local machine all five SES ports
(25/465/587/2465/2587) are open, so host and credentials were never at
fault. SES also listens on **2587**, which Railway leaves open. Same
STARTTLS protocol, different port.

The code default is now 2587, not just the env var — 587 is what anyone
would reach for, and the failure gives no hint.

### SES click tracking broke the unsubscribe link

The delivered email's unsubscribe link had been rewritten through
`awstrack.me` as a double-encoded redirect, which Gmail then wrapped
again in `google.com/url`. Two layers of rewriting on a URL carrying a
token; it did not resolve.

The endpoint was never broken — the unwrapped URL returned 200 and
unsubscribed correctly. Fixed with `ses:no-track` on the anchor, with a
regression test asserting the attribute sits on the same anchor as the
unsubscribe href.

**Still open (founder, AWS console):** click tracking remains enabled on
the configuration set and will keep rewriting every other link.
Recommend disabling it outright — `awstrack.me` URLs read as phishing,
which is the wrong signal for a brand asking to be trusted with money.

## Architecture as built

React Email authors the templates; `npm run emails:export` renders them
to static HTML committed under `kite-api/app/emails/`; Python substitutes
a **closed set** of HTML-escaped tokens and sends via stdlib `smtplib`.

No Node in production, no boto3, no templating language over exported
HTML. `react-email` is a devDependency only. The tripwire stands: the
first template needing a loop or conditional is the signal to move
rendering to a Node service, not to grow a dialect.

## Open items

1. **Cadence undecided.** The welcome mail promises a *weekly product
   update* only. The founder also asked for daily market updates; that
   is flagged in PLAN §2a as the content category most likely to look
   like regulated research while the RA registration is pending. The
   email is where a cadence becomes a promise, so it stays out until
   resolved.
2. **Disable SES click tracking** (above).
3. **Phase 3** — bounce and complaint events into `status`, suppression,
   tighten DMARC from `p=none` to `quarantine` once reports look clean.
4. **Phase 4** — parked deliberately until there is a list worth writing
   to, and until the SEBI question about pre-registration commentary has
   a real answer.
5. Privacy policy should state waitlist collection and
   deletion-on-request (R-027).

## Notes for whoever picks this up

- Railway CLI: always `--service kite-lab`; the linked default is the
  options worker.
- An admin token for API checks: `await window.Clerk.session.getToken()`
  in the console of a signed-in browser.
- `EMAIL_ENABLED` is now **true** in production. It defaults false in
  code so no other environment starts mailing people by accident.
