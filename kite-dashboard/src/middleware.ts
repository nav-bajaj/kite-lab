import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

// SECURITY: SKIP_AUTH is ONLY for local development
// It is NEVER allowed in production, regardless of env var
const IS_PRODUCTION = process.env.NODE_ENV === "production";
const SKIP_AUTH = !IS_PRODUCTION && process.env.SKIP_AUTH === "true";

// Log warning if someone tries to enable SKIP_AUTH in production
if (IS_PRODUCTION && process.env.SKIP_AUTH === "true") {
  console.error(
    "SECURITY WARNING: SKIP_AUTH=true is ignored in production. Authentication is enforced."
  );
}

export default auth((req) => {
  const { pathname } = req.nextUrl;

  // Skip auth ONLY in development mode (never in production)
  if (SKIP_AUTH) {
    return NextResponse.next();
  }

  // Public routes that don't require auth
  const publicRoutes = ["/login", "/api/auth"];
  const isPublicRoute = publicRoutes.some((route) => pathname.startsWith(route));

  if (isPublicRoute) {
    return NextResponse.next();
  }

  // Check if user is authenticated
  if (!req.auth) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
});

export const config = {
  matcher: [
    // Match all routes except static files and api routes (except auth)
    "/((?!_next/static|_next/image|favicon.ico|api/(?!auth)).*)",
  ],
};
