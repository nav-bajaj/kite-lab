# email_channel — research findings

Verified 2026-08-26 against live sources (npm registry, GitHub API, vendor
docs). Recorded here because several findings contradict what most guides
and model training data say — re-verify before trusting anything below if
you are reading this months later.

## React Email

The founder asked about "an open-source React email stack" — this is it:
`react-email`, MIT, built by Resend but **not** coupled to Resend.

| Fact | Value |
|---|---|
| Package | `react-email` **6.9.3** (published 2026-08-25) |
| License | MIT, all packages |
| Health | 19.6k stars, ~2M weekly downloads, weekly releases, last push 2026-08-25 |
| Peer deps | react `^18 \|\| ^19` — our React 19.2.3 / Next 16.1.6 qualifies |
| Renderer | `@react-email/render` 2.1.0 |

### Two corrections that would otherwise bite us

1. **`@react-email/components` is DEPRECATED.** Verified directly on the
   npm registry — the package carries the flag "Package no longer
   supported", last published 2026-04-09 at 1.0.12. React Email 6.0
   (April 2026) folded the components and the preview server into the
   `react-email` package itself (plus `@react-email/ui`). Every tutorial
   and every model trained before mid-2026 will tell you to
   `import { Button } from '@react-email/components'`. That is stale.
   Correct: `import { Button } from 'react-email'`.
2. **`renderAsync` no longer exists.** Removed; `render()` is itself
   async. Missing the `await` renders the literal string
   `[object Promise]` into the message body — and SES will send it.

### It renders, it does not send

`render()` takes a React element and returns an HTML string. No network
calls, no API key, no provider coupling. Official integration guides
cover SES, Nodemailer/SMTP, Postmark, SendGrid, Mailgun and others — the
breadth is the proof. **We do not need a Resend account and nothing
degrades without one.**

Note the official AWS SES guide shows `@aws-sdk/client-ses`, which is the
**v1** API. v2 is `@aws-sdk/client-sesv2`. Irrelevant if we send from
Python (see PLAN §3).

### Hard limits to design around, not code around

- **Web fonts effectively do not work.** `@font-face` support across
  email clients is ~24%. Gmail ignores it. Outlook for Windows falls back
  to Times New Roman unless `mso-generic-font-family` / `mso-font-alt`
  are set. React Email's `<Font>` takes a `fallbackFontFamily` — **that
  fallback is what most recipients actually see, so it is the real
  typographic decision.** Fraunces/Outfit will not render for most of the
  list. Beauty has to come from layout, spacing, colour and imagery.
- **Dark mode is unsolved and React Email does not solve it.** Some
  clients auto-invert with no opt-out; Gmail strips `<style>` blocks in
  some contexts so a `prefers-color-scheme` media query may never run.
  Inline styles are the only guaranteed floor. Choose colours that
  survive inversion, avoid pure `#000`/`#fff`, use transparent-background
  PNGs. The preview server shows light mode ONLY — dark must be tested on
  a real device. (Same conclusion we reached for the coming-soon page.)
- **Still tables underneath.** Classic Outlook renders via the Word HTML
  engine: no flexbox, no grid. React Email emits nested tables + MSO
  conditionals for you — it does not make Outlook modern, it makes us not
  need modern.
- **Tailwind component caveats:** pinned to tailwindcss 4.1.12; `prose`
  and `space-*` do not work; `hover:` is not inlined.

### Alternatives considered

- **MJML** (5.4.0, MIT) — most battle-tested; XML rather than React;
  would be the pick if Python owned templates (it has Python bindings).
- **Maizzle** (6.1.2, MIT) — HTML + Tailwind with a build pipeline; best
  raw control, smaller community, still a Node build step.
- **Plain HTML + `juice` inliner** — lightest, but we absorb every
  Outlook quirk by hand.

Verdict: React Email, because the team already writes React daily and the
alternative is becoming email-rendering experts.

## Sending transport

SES is already production-ready for `marketworks.in` (see PLAN §2), so
the transport is settled. One implementation note discovered while
scoping: **`boto3` is NOT currently a dependency** of kite-api, and R-018
(dependency CVE surface) is an open High row in the risk register.
Python's stdlib `smtplib` + `email.message` can send through the SES SMTP
endpoint with **zero new dependencies**. See PLAN §3 for the tradeoff
against boto3's better error handling and suppression-list API.

## Sources

- https://react.email/docs/introduction · /docs/utilities/render · /docs/cli
- https://resend.com/blog/react-email-6 (the v6 unification)
- https://react.email/docs/components/tailwind · /docs/components/font
- https://github.com/resend/react-email
- https://www.caniemail.com/features/css-at-font-face/
- npm registry queried directly for version + deprecation status
