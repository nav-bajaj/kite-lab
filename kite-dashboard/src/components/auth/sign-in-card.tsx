"use client";

/**
 * Sign-in card (auth_stack_v2 F2.3) — replaces Clerk's <SignIn/> widget.
 *
 * Two methods, one passwordless flow shared by sign-in AND sign-up
 * (Supabase creates the user on first verification):
 *   1. Google SSO — PKCE redirect through /auth/callback.
 *   2. Email OTP — send a 6-digit code, verify it here.
 *
 * Styling: role tokens only (no literal hexes), so the card follows the
 * six-palette system + Midnight dark. Sits inside the `.mw-brand` shell.
 * A phone tab (WhatsApp/SMS OTP via MSG91) slots in as a third method in
 * Phase 5 — keep the method list top-level.
 */

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";

import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { GoogleMark } from "./google-mark";

const RESEND_COOLDOWN_S = 30;

type Step = "methods" | "code";

export function SignInCard() {
  const searchParams = useSearchParams();
  const [step, setStep] = React.useState<Step>("methods");
  const [email, setEmail] = React.useState("");
  const [code, setCode] = React.useState("");
  const [busy, setBusy] = React.useState<"google" | "send" | "verify" | null>(
    null,
  );
  const [error, setError] = React.useState<string | null>(
    searchParams.get("error") === "oauth"
      ? "Google sign-in didn't complete. Please try again."
      : null,
  );
  const [cooldown, setCooldown] = React.useState(0);

  React.useEffect(() => {
    if (cooldown <= 0) return;
    const id = setInterval(() => setCooldown((c) => c - 1), 1000);
    return () => clearInterval(id);
  }, [cooldown]);

  const signInWithGoogle = async () => {
    setBusy("google");
    setError(null);
    const { error: err } = await getSupabaseBrowserClient().auth.signInWithOAuth(
      {
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback?next=/dashboard`,
        },
      },
    );
    // On success the browser navigates away; only errors land here.
    if (err) {
      setError("Could not start Google sign-in. Please try again.");
      setBusy(null);
    }
  };

  const sendCode = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!email.trim()) return;
    setBusy("send");
    setError(null);
    const { error: err } = await getSupabaseBrowserClient().auth.signInWithOtp({
      email: email.trim(),
      options: { shouldCreateUser: true },
    });
    setBusy(null);
    if (err) {
      setError(
        err.status === 429
          ? "Too many attempts — please wait a minute and try again."
          : "Couldn't send the code. Check the address and try again.",
      );
      return;
    }
    setStep("code");
    setCode("");
    setCooldown(RESEND_COOLDOWN_S);
  };

  const verifyCode = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (code.length !== 6) return;
    setBusy("verify");
    setError(null);
    const { error: err } = await getSupabaseBrowserClient().auth.verifyOtp({
      email: email.trim(),
      token: code,
      type: "email",
    });
    if (err) {
      setBusy(null);
      setError("That code didn't match (or expired). Try again or resend.");
      setCode("");
      return;
    }
    // Full navigation (not router.push) so the fresh session cookies are
    // present on the server render of the destination.
    window.location.assign("/dashboard");
  };

  return (
    <div className="w-full max-w-[400px] rounded-card border border-border bg-card p-6 shadow-card sm:p-8">
      {step === "methods" ? (
        <div className="flex flex-col gap-5">
          <Button
            variant="outline"
            size="lg"
            className="w-full justify-center"
            onClick={signInWithGoogle}
            disabled={busy !== null}
          >
            {busy === "google" ? (
              <Loader2 className="animate-spin" />
            ) : (
              <GoogleMark className="size-4" />
            )}
            Continue with Google
          </Button>

          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
              or
            </span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <form className="flex flex-col gap-3" onSubmit={sendCode}>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="signin-email">Email</Label>
              <Input
                id="signin-email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                aria-invalid={error !== null && step === "methods"}
              />
            </div>
            <Button
              type="submit"
              size="lg"
              className="w-full"
              disabled={busy !== null || !email.trim()}
            >
              {busy === "send" ? <Loader2 className="animate-spin" /> : null}
              Send sign-in code
            </Button>
          </form>
          <p className="text-center text-[13px] leading-[1.5] text-muted-foreground">
            No password needed — we&apos;ll email you a one-time code. New
            here? The same code creates your account.
          </p>
        </div>
      ) : (
        <form className="flex flex-col gap-4" onSubmit={verifyCode}>
          <div className="flex flex-col gap-1 text-center">
            <p className="text-sm text-muted-foreground">
              We sent a 6-digit code to
            </p>
            <p className="truncate text-sm font-medium text-foreground">
              {email}
            </p>
          </div>
          <Input
            autoFocus
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]*"
            maxLength={6}
            placeholder="••••••"
            value={code}
            onChange={(e) => {
              const digits = e.target.value.replace(/\D/g, "").slice(0, 6);
              setCode(digits);
            }}
            aria-label="6-digit sign-in code"
            aria-invalid={error !== null}
            className="h-12 text-center text-xl font-medium tracking-[0.4em] [font-feature-settings:'tnum']"
          />
          <Button
            type="submit"
            size="lg"
            className="w-full"
            disabled={busy !== null || code.length !== 6}
          >
            {busy === "verify" ? <Loader2 className="animate-spin" /> : null}
            Verify and continue
          </Button>
          <div className="flex items-center justify-between text-[13px]">
            <button
              type="button"
              className="text-muted-foreground transition-colors hover:text-foreground"
              onClick={() => {
                setStep("methods");
                setError(null);
                setCode("");
              }}
            >
              Use a different email
            </button>
            <button
              type="button"
              className="font-medium text-primary transition-opacity disabled:opacity-50"
              disabled={cooldown > 0 || busy !== null}
              onClick={() => sendCode()}
            >
              {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}
            </button>
          </div>
        </form>
      )}

      {error ? (
        <p role="alert" className="mt-4 text-center text-[13px] text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
