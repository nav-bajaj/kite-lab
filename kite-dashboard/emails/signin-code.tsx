import { Section, Text } from "react-email";

import { Layout } from "./_components/layout";
import { color, font } from "./_components/theme";
import { Eyebrow, H1, P } from "./_components/blocks";

/**
 * Supabase Auth sign-in code (tasks/auth_stack_v2 step A7).
 *
 * NOT sent by our Python sender — Supabase sends it. Export this, then
 * paste the HTML into Supabase Dashboard → Authentication → Emails →
 * Magic Link. `{{ .Token }}` is Supabase's own Go-template variable and
 * passes through our export untouched, because our token pattern only
 * matches {{word}} with no spaces or dots.
 *
 * transactional: a login code carries no unsubscribe link. You cannot
 * unsubscribe from your own sign-in, and offering it would be a way to
 * lose someone their account access.
 *
 * SUBJECT LINE (set in the Supabase dashboard, not here):
 *     {{ .Token }} is your Marketworks sign-in code
 * The code leads so it survives notification truncation. This is a
 * deliberate convenience-over-secrecy trade: the code becomes readable
 * from a lock screen, against a large reduction in friction. Acceptable
 * because the code is single-use and expires in 10 minutes. Revisit if
 * the product ever guards something more sensitive than a research
 * dashboard.
 *
 * No copy button: email clients strip JavaScript, so one cannot work.
 * The code is selectable text near the word "code", which is what iOS
 * and macOS one-time-code autofill keys off — faster than a button.
 */
export default function SigninCode() {
  return (
    <Layout preview="This code expires in 10 minutes." transactional>
      <Eyebrow>Sign in</Eyebrow>
      <H1>Your sign-in code</H1>

      <P>Enter this code to finish signing in to Marketworks.</P>

      {/* The code is the whole message. Mono, large, generously spaced so
          it survives being read off a phone — and selectable as text
          rather than an image, which would be blocked by default. */}
      <Section
        style={{
          backgroundColor: color.soft,
          border: `1px solid ${color.line}`,
          borderRadius: "8px",
          padding: "22px 16px",
          margin: "4px 0 22px",
          textAlign: "center" as const,
        }}
      >
        <Text
          style={{
            margin: 0,
            fontFamily: font.mono,
            fontSize: "32px",
            lineHeight: "1.2",
            letterSpacing: "0.18em",
            color: color.ink,
          }}
        >
          {"{{ .Token }}"}
        </Text>
      </Section>

      <P muted>
        It expires in 10 minutes. If you didn&rsquo;t ask to sign in, you
        can ignore this email &mdash; nobody can use the code without it.
      </P>
    </Layout>
  );
}
