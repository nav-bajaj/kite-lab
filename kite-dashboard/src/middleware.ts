import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { INSIGHTS_ACCESS } from "@/lib/flags";
import { siteMode, isGateOpenPath } from "@/lib/site-mode";

// Public routes — no auth required. Anything not matched here (and not in
// `config.matcher` exclusions below) requires a signed-in Supabase session.
//
// `/` is the public marketing landing page (the authenticated dashboard
// lives at `/dashboard`). `/auth/callback` must stay public — it is the
// OAuth code-exchange hop, hit before a session exists. `/sign-up` is a
// real page (same SignInCard, beta CTA copy).
const PUBLIC_EXACT = new Set([
  "/",
  "/auth/callback",
  "/terms",
  "/privacy",
  "/disclaimer",
  "/portfolios",
  // Email consent pages and the metadata route. These must appear here AND
  // satisfy isGateOpenPath — the two lists answer different questions:
  // this one is "does it need a session", that one is "is it visible while
  // gated". Clearing only one leaves the links broken, which is how these
  // pages failed the first time.
  "/unsubscribe",
  "/confirm",
  "/robots.txt",
]);
const PUBLIC_PREFIXES = ["/sign-in", "/sign-up", "/library"];

const atOrUnder = (path: string, base: string) =>
  path === base || path.startsWith(base + "/");

const isPublicRoute = (path: string) =>
  PUBLIC_EXACT.has(path) ||
  PUBLIC_PREFIXES.some((base) => atOrUnder(path, base));

// Admin-only routes. Role comes from the JWT's `app_metadata.role` claim
// (server-controlled; set via the Supabase admin API). This edge check is
// UX-routing only — the FastAPI backend independently verifies the token
// and enforces the real gates (require_admin, R-022).
const isAdminRoute = (path: string) => atOrUnder(path, "/admin");

// Insights tri-state (src/lib/flags.ts): off → bounce to /dashboard;
// admin → signed-in + admin role; all → any signed-in user.
const isInsightsRoute = (path: string) => atOrUnder(path, "/insights");

function roleFromClaims(claims: Record<string, unknown> | null): string {
  const meta = (claims as { app_metadata?: { role?: string } } | null)
    ?.app_metadata;
  return meta?.role === "admin" ? "admin" : "client";
}

export async function middleware(request: NextRequest) {
  // The response we'll return on pass-through. Session-refresh cookies from
  // Supabase get written onto whichever response actually goes out, so a
  // refreshed token is never dropped — including on redirects.
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      // R-032 rolling inactivity window — see src/lib/supabase/client.ts.
      cookieOptions: { maxAge: 30 * 24 * 60 * 60 },
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value),
          );
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  // getClaims verifies the JWT locally against the project JWKS (ES256 —
  // asymmetric signing keys), refreshing the session first if needed. No
  // per-request network round-trip on the happy path.
  const { data } = await supabase.auth.getClaims();
  const claims = data?.claims ?? null;
  const isAuthed = claims !== null;
  const role = roleFromClaims(claims);
  const path = request.nextUrl.pathname;

  const redirectTo = (pathname: string) => {
    const url = request.nextUrl.clone();
    url.pathname = pathname;
    url.search = "";
    const redirect = NextResponse.redirect(url);
    // Carry any refreshed session cookies onto the redirect.
    response.cookies.getAll().forEach((c) => redirect.cookies.set(c));
    return redirect;
  };

  // Under-development gate (tasks/site_gate). While
  // SITE_MODE=under_development everything except isGateOpenPath is
  // invisible unless the session's app_metadata.role is admin. Non-admins —
  // signed-in users included — and anonymous visitors are bounced to "/",
  // never to /sign-in, so the gate does not advertise that a sign-in
  // exists: an unknown path and a real one behave identically.
  //
  // This runs FIRST so it wins over the insights and public-route logic
  // below. The backend enforces the same lockdown independently via
  // PRIVATE_MODE, which is not redundant: /library and /portfolios are
  // prerendered, so for those routes this middleware is the only layer.
  if (siteMode() === "under_development" && !isGateOpenPath(path)) {
    if (role !== "admin") return redirectTo("/");
  }

  if (isInsightsRoute(path)) {
    if (INSIGHTS_ACCESS === "off") return redirectTo("/dashboard");
    if (INSIGHTS_ACCESS === "admin") {
      if (!isAuthed) return redirectTo("/sign-in");
      if (role !== "admin") return redirectTo("/dashboard");
    }
  }

  if (!isPublicRoute(path) && !isAuthed) {
    return redirectTo("/sign-in");
  }

  if (isAdminRoute(path) && role !== "admin") {
    // Authed non-admin → back to the marketing root rather than a 404.
    return redirectTo("/");
  }

  return response;
}

export const config = {
  matcher: [
    // Skip Next internals and static assets
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
