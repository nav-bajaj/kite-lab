import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

// Skip auth in development mode when SKIP_AUTH is set
const SKIP_AUTH = process.env.SKIP_AUTH === "true";

export default auth((req) => {
  const { pathname } = req.nextUrl;

  // Skip auth entirely in dev mode
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
