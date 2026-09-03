"use client";

import Link from "next/link";
import { useState } from "react";

import styles from "./coming-soon.module.css";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type State = "idle" | "working" | "done" | "error";

/**
 * Confirms before unsubscribing rather than acting on page load. A GET
 * that mutates state gets triggered by link scanners and mail-security
 * prefetchers, which would silently unsubscribe people who never clicked.
 * One-click (RFC 8058) is the exception and POSTs straight to the API.
 */
export function UnsubscribeCard({ token }: { token: string }) {
  const [state, setState] = useState<State>("idle");

  async function handleUnsubscribe() {
    if (state === "working") return;
    setState("working");
    try {
      const resp = await fetch(
        `${API_BASE_URL}/api/waitlist/unsubscribe?token=${encodeURIComponent(token)}`,
        { method: "POST" }
      );
      setState(resp.ok ? "done" : "error");
    } catch {
      setState("error");
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.dots} aria-hidden />

      <header className={styles.top}>
        <Link href="/" className={styles.wordmark}>
          marketworks
        </Link>
      </header>

      <main className={styles.main}>
        <section className={styles.hero}>
          {state === "done" ? (
            <>
              <p className={styles.eyebrow}>Unsubscribed</p>
              <h1 className={styles.h1}>You&rsquo;re off the list.</h1>
              <p className={styles.lede}>
                We won&rsquo;t email you again. If this was a mistake, you can
                rejoin from the home page any time.
              </p>
            </>
          ) : (
            <>
              <p className={styles.eyebrow}>Unsubscribe</p>
              <h1 className={styles.h1}>Leave the waitlist?</h1>
              <p className={styles.lede}>
                You&rsquo;ll stop receiving updates from Marketworks. This
                takes effect immediately.
              </p>
              <div className={styles.form}>
                <button
                  type="button"
                  onClick={handleUnsubscribe}
                  disabled={state === "working" || !token}
                  className={styles.submit}
                >
                  {state === "working" ? "Removing…" : "Unsubscribe"}
                </button>
              </div>
              {!token && (
                <p className={styles.error} role="status">
                  This link is missing its token. Use the unsubscribe link
                  from one of our emails, or reply and we&rsquo;ll remove you.
                </p>
              )}
              {state === "error" && (
                <p className={styles.error} role="status">
                  Something went wrong. Try again in a minute, or reply to any
                  of our emails and we&rsquo;ll remove you by hand.
                </p>
              )}
            </>
          )}
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
