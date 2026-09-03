import {
  Column,
  Hr,
  Link,
  Row,
  Section,
  Text,
} from "react-email";

import { color, font, NO_TRACK } from "./theme";

/**
 * Reusable email blocks — the pieces a welcome mail, a product update and a
 * market note are all assembled from.
 *
 * Everything here is inline-styled and table-backed via React Email's
 * Row/Column, because classic Outlook renders through the Word HTML engine:
 * no flexbox, no grid. Nothing depends on a <style> block, since Gmail
 * strips those in some contexts.
 */

/* ── type ─────────────────────────────────────────────────────────────── */

export function H1({ children }: { children: React.ReactNode }) {
  return (
    <Text
      style={{
        margin: "0 0 16px",
        fontFamily: font.serif,
        fontSize: "30px",
        lineHeight: "1.2",
        fontWeight: 400,
        letterSpacing: "-0.01em",
        color: color.ink,
      }}
    >
      {children}
    </Text>
  );
}

export function H2({ children }: { children: React.ReactNode }) {
  return (
    <Text
      style={{
        margin: "0 0 12px",
        fontFamily: font.serif,
        fontSize: "20px",
        lineHeight: "1.3",
        fontWeight: 400,
        color: color.ink,
      }}
    >
      {children}
    </Text>
  );
}

export function P({
  children,
  muted = false,
}: {
  children: React.ReactNode;
  muted?: boolean;
}) {
  return (
    <Text
      style={{
        margin: "0 0 16px",
        fontFamily: font.sans,
        fontSize: "15px",
        lineHeight: "1.65",
        color: muted ? color.grey : color.ink,
      }}
    >
      {children}
    </Text>
  );
}

/** Mono eyebrow — the guide's section-meter voice, the one place the
 *  brand's typographic character survives, since mono has real fallbacks. */
export function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <Text
      style={{
        margin: "0 0 10px",
        fontFamily: font.mono,
        fontSize: "11px",
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        color: color.green,
      }}
    >
      {children}
    </Text>
  );
}

/* ── structure ────────────────────────────────────────────────────────── */

export function Divider({ space = 28 }: { space?: number }) {
  return (
    <Hr
      style={{
        borderColor: color.line,
        borderTopWidth: "1px",
        margin: `${space}px 0`,
      }}
    />
  );
}

/** Tinted panel with a coloured left rule — the guide's accent triad as a
 *  block. Carries emphasis without needing a typeface to do it. */
type AccentName = "acc1" | "acc2" | "acc3" | "acc4";

// Switch, not color[accent]: a keyed lookup trips eslint-plugin-security
// (R-007) and would render undefined if an accent name ever drifted.
function accentTriad(name: AccentName) {
  switch (name) {
    case "acc2":
      return color.acc2;
    case "acc3":
      return color.acc3;
    case "acc4":
      return color.acc4;
    default:
      return color.acc1;
  }
}

export function Callout({
  accent = "acc1",
  children,
}: {
  accent?: AccentName;
  children: React.ReactNode;
}) {
  const a = accentTriad(accent);
  return (
    <Section
      style={{
        backgroundColor: a.bg,
        borderLeft: `3px solid ${a.line}`,
        borderRadius: "4px",
        padding: "16px 18px",
        margin: "0 0 20px",
      }}
    >
      <Text
        style={{
          margin: 0,
          fontFamily: font.sans,
          fontSize: "14px",
          lineHeight: "1.6",
          color: a.fg,
        }}
      >
        {children}
      </Text>
    </Section>
  );
}

/** Solid green button. Padding on the <a>, not the cell, so the whole
 *  shape is clickable in Outlook. */
export function Button({ href, children }: { href: string; children: string }) {
  return (
    <Section style={{ margin: "4px 0 24px" }}>
      <Link
        {...NO_TRACK}
        href={href}
        style={{
          display: "inline-block",
          backgroundColor: color.green,
          color: "#ffffff",
          fontFamily: font.sans,
          fontSize: "15px",
          fontWeight: 600,
          textDecoration: "none",
          padding: "13px 26px",
          borderRadius: "6px",
        }}
      >
        {children}
      </Link>
    </Section>
  );
}

/** One item in a newsletter — the block a product update or a library
 *  piece is rendered as. Repeat it; that is the whole newsletter. */
export function ArticleRow({
  eyebrow,
  title,
  blurb,
  href,
  cta = "Read more",
}: {
  eyebrow?: string;
  title: string;
  blurb: string;
  href?: string;
  cta?: string;
}) {
  return (
    <Section style={{ margin: "0 0 8px" }}>
      {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
      <Text
        style={{
          margin: "0 0 8px",
          fontFamily: font.serif,
          fontSize: "19px",
          lineHeight: "1.3",
          fontWeight: 400,
          color: color.ink,
        }}
      >
        {title}
      </Text>
      <Text
        style={{
          margin: "0 0 10px",
          fontFamily: font.sans,
          fontSize: "14.5px",
          lineHeight: "1.6",
          color: color.grey,
        }}
      >
        {blurb}
      </Text>
      {href ? (
        <Text style={{ margin: 0 }}>
          <Link
            {...NO_TRACK}
            href={href}
            style={{
              fontFamily: font.sans,
              fontSize: "14px",
              fontWeight: 600,
              color: color.green,
              textDecoration: "none",
            }}
          >
            {cta} &rarr;
          </Link>
        </Text>
      ) : null}
    </Section>
  );
}

/** Figure row for a market note. Mono numerals, tabular — the one place
 *  numbers should look like numbers. Two or three per row, no more:
 *  columns get cramped below ~180px on a phone. */
export function StatRow({
  stats,
}: {
  stats: { label: string; value: string; note?: string }[];
}) {
  return (
    <Section
      style={{
        backgroundColor: color.soft,
        borderRadius: "8px",
        padding: "18px 16px",
        margin: "0 0 22px",
      }}
    >
      <Row>
        {stats.map((s) => (
          <Column key={s.label} style={{ verticalAlign: "top" }}>
            <Text
              style={{
                margin: "0 0 6px",
                fontFamily: font.sans,
                fontSize: "11.5px",
                lineHeight: "1.3",
                color: color.greySoft,
              }}
            >
              {s.label}
            </Text>
            <Text
              style={{
                margin: 0,
                fontFamily: font.mono,
                fontSize: "20px",
                lineHeight: "1.2",
                color: color.ink,
              }}
            >
              {s.value}
            </Text>
            {s.note ? (
              <Text
                style={{
                  margin: "4px 0 0",
                  fontFamily: font.sans,
                  fontSize: "11px",
                  color: color.greySoft,
                }}
              >
                {s.note}
              </Text>
            ) : null}
          </Column>
        ))}
      </Row>
    </Section>
  );
}
