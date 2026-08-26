"use client";

import { useState } from "react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type FormState = "idle" | "submitting" | "done" | "error";

/**
 * Waitlist email capture for the under-development page (tasks/site_gate).
 * POSTs to the public kite-api waitlist endpoint. The hidden "website"
 * field is a honeypot — real users never see or fill it.
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
      <p className="text-base font-medium text-foreground" role="status">
        You&apos;re on the list. We&apos;ll email you when we launch.
      </p>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex w-full max-w-[440px] flex-col gap-3 sm:flex-row"
    >
      <label htmlFor="waitlist-email" className="sr-only">
        Email address
      </label>
      <input
        id="waitlist-email"
        type="email"
        required
        maxLength={320}
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
        className="h-12 flex-1 rounded-full border border-border bg-surface-base px-5 text-base text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-primary/40"
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
        className="absolute left-[-9999px] h-0 w-0 opacity-0"
      />
      <button
        type="submit"
        disabled={state === "submitting"}
        className="h-12 rounded-full bg-primary px-6 text-base font-semibold text-primary-foreground transition-[transform,box-shadow] duration-200 ease-expo hover:-translate-y-px hover:shadow-md disabled:opacity-60"
      >
        {state === "submitting" ? "Joining…" : "Notify me"}
      </button>
      {state === "error" && (
        <p className="text-sm text-muted-foreground sm:basis-full" role="status">
          Something went wrong — please try again in a minute.
        </p>
      )}
    </form>
  );
}
