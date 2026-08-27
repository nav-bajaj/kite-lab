import { Layout } from "./_components/layout";
import {
  ArticleRow,
  Button,
  Divider,
  Eyebrow,
  H1,
  P,
  StatRow,
} from "./_components/blocks";

/**
 * The weekly product update — and the shape any future market note takes.
 * Exists to prove the block set composes into a real multi-item send, not
 * just a one-off welcome mail.
 *
 * CONTENT BELOW IS PLACEHOLDER, written to exercise the layout. The
 * figures are invented and must not ship. A real issue is authored through
 * the content OS and passes the review gate before it goes anywhere near a
 * list — and while the RA registration is pending it stays inside the
 * PLAN §2 constraints: no recommendations, no performance claims, nothing
 * implying registration.
 */
export default function ProductUpdate() {
  return (
    <Layout
      preview="What we shipped this week, and what's next."
      kicker="Product update · No. 1"
    >
      <Eyebrow>This week</Eyebrow>
      <H1>Building in the open.</H1>

      <P>
        A short note on what moved this week. Nothing here is a
        recommendation &mdash; it&rsquo;s a look at what we&rsquo;re
        building and why.
      </P>

      {/* Figures render in mono so numbers look like numbers. Two or three
          per row; more than that cramps on a phone. PLACEHOLDER DATA. */}
      <StatRow
        stats={[
          { label: "Universe tracked", value: "NSE 500", note: "daily" },
          { label: "Signals rebuilt", value: "7", note: "portfolios" },
          { label: "Years validated", value: "9", note: "out-of-sample" },
        ]}
      />

      <Divider space={24} />

      <ArticleRow
        eyebrow="Shipped"
        title="A cleaner read on market breadth"
        blurb="Breadth now reads from the full NSE 500 panel rather than a sampled subset, so a narrow rally is visible on the day it narrows."
        href="https://marketworks.in/library"
        cta="Read the note"
      />

      <Divider space={24} />

      <ArticleRow
        eyebrow="In progress"
        title="Corporate actions, handled properly"
        blurb="Splits, bonuses and demergers quietly corrupt a price history if they are adjusted late. We rebuilt that pipeline so the adjustment happens before any signal reads the panel."
      />

      <Divider space={24} />

      <ArticleRow
        eyebrow="From the library"
        title="Why process beats prediction"
        blurb="The case for rules you can restate a year later, and what that discipline costs you in the months it underperforms."
        href="https://marketworks.in/library"
        cta="Read the article"
      />

      <Divider space={26} />

      <Eyebrow>Coming next</Eyebrow>
      <P muted>
        We&rsquo;re opening access in stages. If you&rsquo;re on the
        waitlist, you&rsquo;ll hear from us before anyone else.
      </P>

      <Button href="https://marketworks.in">See what we&rsquo;re building</Button>
    </Layout>
  );
}
