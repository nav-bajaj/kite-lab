"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import styles from "./coming-soon.module.css";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type State = "working" | "done" | "error";

/**
 * Completes a double opt-in signup. Unlike /unsubscribe this confirms on
 * load rather than asking again — the click in the email IS the consent,
 * and making someone confirm twice loses people for no benefit. The
 * asymmetry is deliberate: confirming is additive, unsubscribing is not.
 */
export function ConfirmCard({ token }: { token: string }) {
  const [state, setState] = useState<State>(token ? "working" : "error");

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const resp = await fetch(
          `${API_BASE_URL}/api/waitlist/confirm?token=${encodeURIComponent(token)}`
        );
        if (!cancelled) setState(resp.ok ? "done" : "error");
      } catch {
        if (!cancelled) setState("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

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
              <p className={styles.eyebrow}>Confirmed</p>
              <h1 className={styles.h1}>You&rsquo;re on the list.</h1>
              <p className={styles.lede}>
                Thanks for confirming. We&rsquo;ll email you as soon as we
                open access.
              </p>
            </>
          ) : state === "working" ? (
            <>
              <p className={styles.eyebrow}>Confirming</p>
              <h1 className={styles.h1}>One moment.</h1>
            </>
          ) : (
            <>
              <p className={styles.eyebrow}>Link problem</p>
              <h1 className={styles.h1}>That link didn&rsquo;t work.</h1>
              <p className={styles.lede}>
                It may have already been used, or the address was cut short by
                your email client. Try signing up again from the home page.
              </p>
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
