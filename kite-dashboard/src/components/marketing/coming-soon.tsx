import { IBM_Plex_Mono, Libre_Baskerville } from "next/font/google";

import { WaitlistForm } from "@/components/marketing/waitlist-form";
import styles from "./coming-soon.module.css";

// Design language v2 faces (guide: Libre Baskerville serif, IBM Plex Mono).
// Loaded here, not in the root layout — only this page uses them until the
// planned site-wide design update.
const serif = Libre_Baskerville({
  weight: ["400", "700"],
  subsets: ["latin"],
  variable: "--cs-serif",
});
const mono = IBM_Plex_Mono({
  weight: ["400", "500"],
  subsets: ["latin"],
  variable: "--cs-mono",
});

/**
 * The under-development home page (tasks/site_gate), restyled to the v2
 * single-green design language (marketworks-design/design-language-guide-v2):
 * dot texture ground, centered serif wordmark in brand green, centered hero,
 * and the email capture as a guide-§06 banded section (near-white field,
 * hairline top and bottom). This is the ONLY page a non-admin visitor can
 * see while SITE_MODE=under_development. No nav, no sign-in link.
 *
 * Copy register stays neutral — the platform is under development; do not
 * make affirmative claims about SEBI registration status.
 */
export function ComingSoon() {
  return (
    <div className={`${styles.page} ${serif.variable} ${mono.variable}`}>
      <div className={styles.dots} aria-hidden />

      <header className={styles.top}>
        <span className={styles.wordmark}>marketworks</span>
      </header>

      <main className={styles.main}>
        <section className={styles.hero}>
          <p className={styles.eyebrow}>Under development</p>
          <h1 className={styles.h1}>Process over prediction.</h1>
          <p className={styles.lede}>
            Marketworks aims to publish equity research, market statistics,
            and stock baskets grounded in its own research. We operate at the
            intersection of technology, finance, and education. Every decision
            is driven by data, analytics, and repeatable frameworks &mdash;
            not by predicting where the market goes next.
          </p>
        </section>

        <section className={styles.band}>
          <div className={styles.bandIn}>
            <p className={styles.bandKicker}>
              <u>&gt;</u> The waitlist
            </p>
            <h2 className={styles.bandTitle}>Be the first to know.</h2>
            <p className={styles.bandSub}>
              We are currently &ldquo;invite only&rdquo; and in Private Beta
              testing.
            </p>
            <p className={styles.bandSub}>
              Please leave your email to be added to our waitlist and we will
              reach out to you.
            </p>
            <WaitlistForm />
            <p className={styles.privacy}>
              We&apos;ll only email you important updates about our
              development and launch. See our{" "}
              <a href="/privacy">Privacy Policy</a>.
            </p>
          </div>
        </section>
      </main>

      <footer className={styles.foot}>
        <div className={styles.hatch} aria-hidden />
        <div className={styles.footIn}>
          <nav className={styles.footLinks}>
            <a href="/terms">Terms</a>
            <a href="/privacy">Privacy</a>
            <a href="/disclaimer">Disclaimer</a>
          </nav>
          <p className={styles.giant} aria-hidden>
            marketworks
          </p>
          <div className={styles.footBase}>
            <span>&copy; 2026 Marketworks Research</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
