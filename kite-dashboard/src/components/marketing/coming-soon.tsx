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
 * PLACEHOLDER COPY: the founder writes the final wording. Keep the register
 * neutral — say the platform is under development; do not make affirmative
 * claims about SEBI registration status.
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
          <h1 className={styles.h1}>Something calm is taking shape.</h1>
          <p className={styles.lede}>
            Marketworks is a research platform for Indian equities, currently
            under development.
          </p>
        </section>

        <section className={styles.band}>
          <div className={styles.bandIn}>
            <p className={styles.bandKicker}>
              <u>&gt;</u> The waitlist
            </p>
            <h2 className={styles.bandTitle}>Be the first to know.</h2>
            <p className={styles.bandSub}>
              Leave your email and we&apos;ll let you know when we launch.
            </p>
            <WaitlistForm />
            <p className={styles.privacy}>
              We&apos;ll only email you about the launch. See our{" "}
              <a href="/privacy">Privacy Policy</a>.
            </p>
          </div>
        </section>
      </main>

      <div className={styles.footWrap}>
        <footer className={styles.foot}>
          <div className={styles.hatch} aria-hidden />
          <div className={styles.footIn}>
            <p className={styles.footNote}>
              Marketworks publishes educational research on Indian equities.
              Markets carry risk; past behaviour is not a guarantee of future
              results.
            </p>
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
    </div>
  );
}
