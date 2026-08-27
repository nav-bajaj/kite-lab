import { Text } from "react-email";

import { Layout, heading, paragraph, quiet } from "./_components/layout";

/**
 * Sent once, immediately, when someone joins the waitlist from the
 * under-development page (tasks/email_channel Phase 2).
 *
 * Copy notes:
 *  - No name. We collect only an email address (founder decision), so the
 *    greeting is generic by design — "Hi ," reaching a real inbox is worse
 *    than not using a name at all.
 *  - States the WEEKLY product update only. The founder also asked for
 *    daily market updates; that is flagged in PLAN §2a as the highest-risk
 *    content category while the RA registration is pending, and this
 *    email is where a cadence becomes a promise. Add the daily line here
 *    only once that is resolved.
 *  - Makes no claim about SEBI registration status, and no performance
 *    or return claims of any kind.
 */
export default function Welcome() {
  return (
    <Layout preview="You're on the Marketworks waitlist.">
      <Text style={heading}>You&rsquo;re on the list.</Text>

      <Text style={paragraph}>
        Thanks for joining the Marketworks waitlist. We&rsquo;ll email you as
        soon as we open access.
      </Text>

      <Text style={paragraph}>
        Marketworks is a research platform for Indian equities, currently
        under development. We&rsquo;re building it around one idea: process
        over prediction. Decisions come from data, analytics and repeatable
        frameworks rather than from calls on where the market goes next.
      </Text>

      <Text style={paragraph}>
        While we build, we&rsquo;ll send you a short product update about
        once a week — what we&rsquo;ve shipped, what we&rsquo;re working on,
        and what we&rsquo;re learning along the way. Nothing you need to act
        on.
      </Text>

      <Text style={quiet}>
        If you didn&rsquo;t sign up, you can ignore this email, or
        unsubscribe below and we won&rsquo;t contact you again.
      </Text>

      <Text style={{ ...paragraph, marginTop: "24px", marginBottom: 0 }}>
        &mdash; The Marketworks team
      </Text>
    </Layout>
  );
}
