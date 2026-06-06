import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import { INSIGHTS_ENABLED } from "@/lib/flags";

// Public routes — no auth required. Anything not in this list (and not in
// `config.matcher` exclusions below) requires a signed-in Clerk session.
//
// `/` is the public marketing landing page (the authenticated dashboard
// moved to `/dashboard`). Unauthenticated visitors see the landing; signed-in
// users are sent to `/dashboard` post-auth (ClerkProvider fallback redirects).
const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/terms",
  "/privacy",
  "/disclaimer",
  "/library(.*)",
]);

// Insight engine pages: behind Clerk login but available to ALL signed-in
// users including free tier — no paid-subscription / admin gate. Acquisition
// flow becomes: visitor → free signup → /insights → optional upgrade.
// (Listed for clarity; no explicit matcher needed since these pages are
// neither in isPublicRoute nor in isAdminRoute, so the default auth.protect()
// gate applies and that's exactly what we want.)

// Admin-only routes. Checked against publicMetadata.role exposed via the
// session token's `metadata` claim (configured in Clerk dashboard).
const isAdminRoute = createRouteMatcher(["/admin(.*)"]);

// Insights surface is gated off until the insight-engine data is provisioned
// on the production backend (otherwise /insights 500s in prod). When disabled,
// bounce /insights* to /dashboard so a direct URL doesn't hit the broken page.
// Flip NEXT_PUBLIC_INSIGHTS_ENABLED=true to re-enable. See src/lib/flags.ts.
const isInsightsRoute = createRouteMatcher(["/insights(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (!INSIGHTS_ENABLED && isInsightsRoute(req)) {
    const url = req.nextUrl.clone();
    url.pathname = "/dashboard";
    return NextResponse.redirect(url);
  }

  if (!isPublicRoute(req)) {
    await auth.protect();
  }

  if (isAdminRoute(req)) {
    const { sessionClaims } = await auth();
    const role = (sessionClaims as { metadata?: { role?: string } } | null)
      ?.metadata?.role;
    if (role !== "admin") {
      // Not an admin → push them back to the dashboard root rather than
      // throwing a 404. Clerk's auth.protect() above already enforced auth.
      const url = req.nextUrl.clone();
      url.pathname = "/";
      return NextResponse.redirect(url);
    }
  }
});

export const config = {
  matcher: [
    // Skip Next internals and static assets
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
