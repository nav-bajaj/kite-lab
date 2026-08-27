import {
  Body,
  Container,
  Head,
  Hr,
  Html,
  Link,
  Preview,
  Section,
  Text,
} from "react-email";

/**
 * Shared brand shell for every Marketworks email (tasks/email_channel).
 *
 * Design constraints, all verified — see tasks/email_channel/RESEARCH.md:
 *  - NO web fonts. @font-face is ~24% supported and Gmail honours it on no
 *    platform, so Fraunces and Outfit cannot travel. Georgia carries the
 *    serif warmth; a system sans stack carries the body. The fallback IS
 *    the design, not a degradation.
 *  - No pure #000/#fff. Several clients auto-invert with no opt-out, and
 *    near-tones survive that far better than absolutes.
 *  - Inline styles only. Gmail strips <style> blocks in some contexts, so
 *    a media query may simply never run. React Email inlines these for us.
 *
 * Directories prefixed `_` are ignored by the react-email CLI, so this
 * file is a partial rather than a previewable template.
 */

// v2 single-green palette, nudged off the absolutes for dark-mode safety.
export const c = {
  ground: "#f4f7f5",
  card: "#ffffff",
  ink: "#141a17",
  grey: "#5c6663",
  greySoft: "#79837f",
  green: "#0b7e52",
  greenDeep: "#0a3b28",
  line: "#e3e8e5",
} as const;

export const serif = "Georgia, 'Times New Roman', Times, serif";
export const sans =
  "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif";

// Substituted by Python at send time (see PLAN §3). Defaulting the prop to
// the literal token means `email export` emits placeholders straight into
// the static HTML, so there is no second templating language in the file.
export const UNSUBSCRIBE_TOKEN = "{{unsubscribe_url}}";

export interface LayoutProps {
  preview: string;
  unsubscribeUrl?: string;
  children: React.ReactNode;
}

export function Layout({
  preview,
  unsubscribeUrl = UNSUBSCRIBE_TOKEN,
  children,
}: LayoutProps) {
  return (
    <Html lang="en">
      <Head />
      <Preview>{preview}</Preview>
      <Body
        style={{
          margin: 0,
          padding: "32px 12px",
          backgroundColor: c.ground,
          fontFamily: sans,
          color: c.ink,
          WebkitFontSmoothing: "antialiased",
        }}
      >
        <Container
          style={{
            maxWidth: "560px",
            margin: "0 auto",
            backgroundColor: c.card,
            borderRadius: "12px",
            border: `1px solid ${c.line}`,
            padding: "40px 36px 32px",
          }}
        >
          {/* Wordmark as text, not an image: images are blocked by default
              in several clients, and this must always render. */}
          <Text
            style={{
              margin: "0 0 28px",
              fontFamily: sans,
              fontSize: "20px",
              fontWeight: 700,
              letterSpacing: "-0.02em",
              color: c.green,
            }}
          >
            marketworks
          </Text>

          {children}
        </Container>

        {/* Footer sits outside the card, in the quieter grey — the legally
            required parts (postal address, unsubscribe) plus the risk
            disclaimer. Deliberately NO claim of SEBI registration: the
            application is pending, and stating otherwise would be false. */}
        <Container style={{ maxWidth: "560px", margin: "0 auto" }}>
          <Section style={{ padding: "24px 36px 8px" }}>
            <Text
              style={{
                margin: "0 0 12px",
                fontFamily: sans,
                fontSize: "12px",
                lineHeight: "1.6",
                color: c.greySoft,
              }}
            >
              Marketworks publishes educational research on Indian equities.
              Nothing in this email is investment advice or a recommendation
              to buy or sell any security. Markets carry risk; past behaviour
              is not a guarantee of future results.
            </Text>
            <Hr style={{ borderColor: c.line, margin: "16px 0" }} />
            <Text
              style={{
                margin: "0 0 6px",
                fontFamily: sans,
                fontSize: "12px",
                lineHeight: "1.6",
                color: c.greySoft,
              }}
            >
              Marketworks Research · SCO 185-187, First Floor, Sector 9-C,
              Madhya Marg, Chandigarh, India
            </Text>
            <Text
              style={{
                margin: 0,
                fontFamily: sans,
                fontSize: "12px",
                lineHeight: "1.6",
                color: c.greySoft,
              }}
            >
              You are receiving this because you joined the waitlist at
              marketworks.in.{" "}
              <Link
                href={unsubscribeUrl}
                style={{ color: c.grey, textDecoration: "underline" }}
              >
                Unsubscribe
              </Link>
              .
            </Text>
          </Section>
        </Container>
      </Body>
    </Html>
  );
}

export const heading = {
  margin: "0 0 18px",
  fontFamily: serif,
  fontSize: "26px",
  lineHeight: "1.25",
  fontWeight: 400,
  color: c.ink,
} as const;

export const paragraph = {
  margin: "0 0 16px",
  fontFamily: sans,
  fontSize: "15px",
  lineHeight: "1.65",
  color: c.ink,
} as const;

export const quiet = {
  ...paragraph,
  color: c.grey,
} as const;
