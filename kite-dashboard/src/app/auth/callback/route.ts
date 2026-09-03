import { NextResponse } from "next/server";

import { getSupabaseServerClient } from "@/lib/supabase/server";

/**
 * OAuth code exchange (PKCE) — Google sign-in redirects here with a
 * one-time `code`; we exchange it for a session (cookies are writable in
 * route handlers) and forward to the app. Kept public in middleware.
 */
export async function GET(request: Request) {
  const { searchParams, origin: requestOrigin } = new URL(request.url);
  // Prefer a fixed site URL over the Host-derived origin so a
  // host-manipulating intermediary can't steer the redirect
  // (security-reviewer 2026-08-11 #8).
  const origin = process.env.NEXT_PUBLIC_SITE_URL ?? requestOrigin;
  const code = searchParams.get("code");
  // Only ever redirect within our own origin — `next` is caller-supplied.
  const next = searchParams.get("next") ?? "/dashboard";
  const safeNext = next.startsWith("/") && !next.startsWith("//")
    ? next
    : "/dashboard";

  if (code) {
    const supabase = await getSupabaseServerClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${safeNext}`);
    }
  }

  return NextResponse.redirect(`${origin}/sign-in?error=oauth`);
}
