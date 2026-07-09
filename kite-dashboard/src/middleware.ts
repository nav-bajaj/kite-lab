import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import { INSIGHTS_ACCESS } from "@/lib/flags";

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

// Insights surface access is a tri-state (see src/lib/flags.ts):
//   off   → bounce /insights* to /dashboard (data-provisioning launch gate).
//   admin → require an admin-role session, mirroring isAdminRoute below;
//           non-admins bounce to /dashboard.
//   all   → any signed-in user (the default auth.protect() gate applies).
const isInsightsRoute = createRouteMatcher(["/insights(.*)"]);

function roleFromClaims(sessionClaims: unknown): string | undefined {
  return (sessionClaims as { metadata?: { role?: string } } | null)
    ?.metadata?.role;
}

export default clerkMiddleware(async (auth, req) => {
  if (isInsightsRoute(req)) {
    if (INSIGHTS_ACCESS === "off") {
      const url = req.nextUrl.clone();
      url.pathname = "/dashboard";
      return NextResponse.redirect(url);
    }
    if (INSIGHTS_ACCESS === "admin") {
      // Signed-in enforcement first (throws to sign-in when absent), then the
      // admin-role check — same shape as isAdminRoute below.
      await auth.protect();
      const { sessionClaims } = await auth();
      if (roleFromClaims(sessionClaims) !== "admin") {
        const url = req.nextUrl.clone();
        url.pathname = "/dashboard";
        return NextResponse.redirect(url);
      }
    }
  }

  if (!isPublicRoute(req)) {
    await auth.protect();
  }

  if (isAdminRoute(req)) {
    const { sessionClaims } = await auth();
    const role = roleFromClaims(sessionClaims);
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
