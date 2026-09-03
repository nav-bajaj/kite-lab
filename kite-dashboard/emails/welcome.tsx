import { Layout } from "./_components/layout";
import { Callout, Divider, Eyebrow, H1, P } from "./_components/blocks";

/**
 * Sent once, immediately, when someone joins the waitlist from the
 * under-development page (tasks/email_channel Phase 2).
 *
 * Copy notes:
 *  - No name: we collect only an email address (founder decision), so the
 *    greeting is generic by design.
 *  - States the WEEKLY product update only. The daily market update is
 *    flagged in PLAN §2a and stays out until resolved — this email is
 *    where a cadence becomes a promise.
 *  - No SEBI registration claim, no performance or return claims.
 */
export default function Welcome() {
  return (
    <Layout
      preview="You're on the Marketworks waitlist — here's what happens next."
      kicker="Waitlist confirmed"
    >
      <Eyebrow>Welcome</Eyebrow>
      <H1>You&rsquo;re on the list.</H1>

      <P>
        Thanks for joining the Marketworks waitlist. We&rsquo;ll email you as
        soon as we open access &mdash; you don&rsquo;t need to do anything
        until then.
      </P>

      <Callout accent="acc1">
        <strong>Process over prediction.</strong> Decisions come from data,
        analytics and repeatable frameworks &mdash; not from calls on where
        the market goes next.
      </Callout>

      <P>
        Marketworks is a research platform for Indian equities, currently
        under development. We&rsquo;re building it at the intersection of
        technology, finance and education.
      </P>

      <Divider />

      <Eyebrow>What to expect</Eyebrow>
      <P muted>
        About once a week we&rsquo;ll send a short product update: what
        we&rsquo;ve shipped, what we&rsquo;re working on, and what we&rsquo;re
        learning along the way. Nothing you need to act on, and you can leave
        the list at any time.
      </P>

      <P muted>
        If you didn&rsquo;t sign up, ignore this email or unsubscribe below
        and we won&rsquo;t contact you again.
      </P>
    </Layout>
  );
}
