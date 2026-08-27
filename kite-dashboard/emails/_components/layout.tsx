import {
  Body,
  Container,
  Head,
  Html,
  Link,
  Preview,
  Section,
  Text,
} from "react-email";

import { color, font, WIDTH, TOKEN } from "./theme";

/**
 * The branded shell every Marketworks email sits in.
 *
 * Brand continuity is deliberate: the site's coming-soon page opens on a
 * green wordmark and closes on a deep-green drench, so the email does the
 * same. Someone who joined the waitlist on that page should recognise this
 * as the same product, and colour + structure are the only carriers that
 * survive across email clients (RESEARCH.md — typography cannot).
 *
 * Files under `_components/` are ignored by the react-email CLI, so this
 * is a partial, not a previewable template.
 */

export interface LayoutProps {
  /** Inbox preview line. Worth writing properly — it is the second thing
   *  a recipient reads, after the subject. */
  preview: string;
  /** Small mono line in the header band, e.g. "Product update · No. 4". */
  kicker?: string;
  unsubscribeUrl?: string;
  children: React.ReactNode;
}

export function Layout({
  preview,
  kicker,
  unsubscribeUrl = TOKEN.unsubscribe,
  children,
}: LayoutProps) {
  return (
    <Html lang="en">
      <Head />
      <Preview>{preview}</Preview>
      <Body
        style={{
          margin: 0,
          padding: "24px 12px 32px",
          backgroundColor: color.page,
          fontFamily: font.sans,
          color: color.ink,
          WebkitFontSmoothing: "antialiased",
        }}
      >
        <Container style={{ maxWidth: `${WIDTH}px`, margin: "0 auto" }}>
          {/* Header band — the deep-green drench, wordmark reversed out.
              Text, not an image: images are blocked by default in several
              clients and the brand must always render. */}
          <Section
            style={{
              backgroundColor: color.greenDeep,
              borderRadius: "12px 12px 0 0",
              padding: "26px 32px",
            }}
          >
            <Text
              style={{
                margin: 0,
                fontFamily: font.sans,
                fontSize: "21px",
                fontWeight: 700,
                letterSpacing: "-0.02em",
                lineHeight: "1.2",
                color: color.greenOnDeep,
              }}
            >
              marketworks
            </Text>
            {kicker ? (
              <Text
                style={{
                  margin: "6px 0 0",
                  fontFamily: font.mono,
                  fontSize: "11px",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: color.greenOnDeep,
                  opacity: 0.7,
                }}
              >
                {kicker}
              </Text>
            ) : null}
          </Section>

          {/* Hairline of vivid green between band and card — a small seam
              that reads as intent rather than a stacking accident. */}
          <Section
            style={{
              backgroundColor: color.greenVivid,
              fontSize: "0px",
              lineHeight: "3px",
              height: "3px",
            }}
          >
            &nbsp;
          </Section>

          <Section
            style={{
              backgroundColor: color.card,
              borderRadius: "0 0 12px 12px",
              padding: "34px 32px 28px",
            }}
          >
            {children}
          </Section>

          {/* Footer outside the card: legally required parts plus the risk
              disclaimer. No SEBI registration claim — the application is
              pending and stating otherwise would be false. */}
          <Section style={{ padding: "22px 32px 0" }}>
            <Text
              style={{
                margin: "0 0 14px",
                fontFamily: font.sans,
                fontSize: "12px",
                lineHeight: "1.6",
                color: color.greySoft,
              }}
            >
              Marketworks publishes educational research on Indian equities.
              Nothing in this email is investment advice or a recommendation
              to buy or sell any security. Markets carry risk; past behaviour
              is not a guarantee of future results.
            </Text>
            <Text
              style={{
                margin: "0 0 6px",
                fontFamily: font.sans,
                fontSize: "12px",
                lineHeight: "1.6",
                color: color.greySoft,
              }}
            >
              Marketworks Research &middot; SCO 185-187, First Floor,
              Sector 9-C, Madhya Marg, Chandigarh, India
            </Text>
            <Text
              style={{
                margin: 0,
                fontFamily: font.sans,
                fontSize: "12px",
                lineHeight: "1.6",
                color: color.greySoft,
              }}
            >
              You are receiving this because you joined the waitlist at
              marketworks.in.{" "}
              {/* ses:no-track keeps SES click-tracking from rewriting this
                  through awstrack.me. Tracking mangled it into a
                  double-encoded redirect that Gmail then wrapped again —
                  and an unsubscribe link is a compliance mechanism, not a
                  marketing metric. It should never be instrumented. */}
              <Link
                {...{ "ses:no-track": "" }}
                href={unsubscribeUrl}
                style={{ color: color.grey, textDecoration: "underline" }}
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
