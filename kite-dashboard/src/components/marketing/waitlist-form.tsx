"use client";

import { useState } from "react";

import styles from "./coming-soon.module.css";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type FormState = "idle" | "submitting" | "done" | "error";

/**
 * Waitlist email capture for the under-development page (tasks/site_gate).
 * POSTs to the public kite-api waitlist endpoint. The hidden "website"
 * field is a honeypot — real users never see or fill it. Styled by
 * coming-soon.module.css: pill input + green pill button side by side on
 * desktop, stacked full-width on mobile.
 */
export function WaitlistForm() {
  const [email, setEmail] = useState("");
  const [website, setWebsite] = useState("");
  const [state, setState] = useState<FormState>("idle");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (state === "submitting") return;
    setState("submitting");
    try {
      const resp = await fetch(`${API_BASE_URL}/api/waitlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, source: "coming_soon", website }),
      });
      if (resp.ok) {
        setState("done");
      } else {
        setState("error");
      }
    } catch {
      setState("error");
    }
  }

  if (state === "done") {
    return (
      <p className={styles.done} role="status">
        You&apos;re on the list. We&apos;ll email you when we launch.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
      <label htmlFor="waitlist-email" className="sr-only">
        Email address
      </label>
      <input
        id="waitlist-email"
        className={styles.input}
        type="email"
        inputMode="email"
        autoComplete="email"
        required
        maxLength={320}
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
      />
      {/* Honeypot — hidden from real users, bots fill it. */}
      <input
        type="text"
        name="website"
        value={website}
        onChange={(e) => setWebsite(e.target.value)}
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
        style={{
          position: "absolute",
          left: "-9999px",
          height: 0,
          width: 0,
          opacity: 0,
        }}
      />
      <button
        type="submit"
        className={styles.submit}
        disabled={state === "submitting"}
      >
        {state === "submitting" ? "Joining…" : "Notify me"}
      </button>
      {state === "error" && (
        <p className={styles.error} role="status">
          Something went wrong — please try again in a minute.
        </p>
      )}
    </form>
  );
}
