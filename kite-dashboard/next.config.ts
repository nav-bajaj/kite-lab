import type { NextConfig } from "next";

// API origin allowed for fetch/SSE. Defaults to the production Railway URL;
// override via NEXT_PUBLIC_API_URL at build time. Read here only to construct
// the CSP — the value itself is intentionally public (it's a URL).
const apiUrl =
  process.env.NEXT_PUBLIC_API_URL ?? "https://kite-lab-production.up.railway.app";

// CSP policy. Closes R-006 in docs/security/risk-register.md.
//
// Notes on the permissive parts:
// - `'unsafe-inline'` on style-src is required by Tailwind (utility-class
//   styles get inlined). When/if we move to a CSS-in-JS approach that
//   supports nonces, this can be tightened.
// - `'unsafe-inline' 'unsafe-eval'` on script-src is required by Next.js +
//   React 19 development mode and by some Next.js features in production
//   (route prefetching). A nonce-based CSP requires significant config
//   changes; tracked as a future tightening in docs/security/risk-register.md.
// - `connect-src` includes the backend API origin and the Google OAuth
//   endpoints; `frame-ancestors 'none'` enforces clickjacking protection
//   (already covered by X-Frame-Options below for older browsers).
// Clerk needs the per-app `*.clerk.accounts.dev` subdomain plus the
// shared `*.clerk.com` API/CDN domain in script-src + connect-src.
// img.clerk.com serves user-uploaded avatars. Clerk also spins up web
// workers from blob URLs for crypto operations.
//
// Cloudflare Turnstile (`challenges.cloudflare.com`) is Clerk's default
// bot-protection on sign-up — it injects an iframe + a script that
// must be CSP-allowed for sign-up to complete.
//
// Reference (Clerk docs, allowed CSP origins):
//   https://clerk.com/docs/security/clerk-csp
const clerkOrigins = "https://*.clerk.accounts.dev https://*.clerk.com";
const turnstileOrigin = "https://challenges.cloudflare.com";

const cspDirectives = [
  `default-src 'self'`,
  `script-src 'self' 'unsafe-inline' 'unsafe-eval' ${clerkOrigins} ${turnstileOrigin} https://accounts.google.com https://*.gstatic.com`,
  `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`,
  `img-src 'self' data: blob: https:`,
  `font-src 'self' data: https://fonts.gstatic.com`,
  `connect-src 'self' ${apiUrl} ${clerkOrigins} ${turnstileOrigin} https://accounts.google.com https://oauth2.googleapis.com https://*.googleapis.com`,
  `frame-src 'self' ${clerkOrigins} ${turnstileOrigin} https://accounts.google.com`,
  `worker-src 'self' blob:`,
  `frame-ancestors 'none'`,
  `form-action 'self' ${clerkOrigins} https://accounts.google.com`,
  `base-uri 'self'`,
  `object-src 'none'`,
  `upgrade-insecure-requests`,
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: cspDirectives },
  // Modern equivalent + legacy fallback for clickjacking.
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), interest-cohort=()",
  },
  // HSTS — applied here so the Vercel-served domain instructs browsers to
  // upgrade. Vercel terminates TLS; both *.vercel.app and custom domains
  // are HTTPS-only, so this is safe.
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  },
  // Cross-origin isolation — defensive defaults; revisit if we ever embed
  // third-party widgets that need to be cross-origin-accessible.
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
];

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        // Apply to every route — both static and dynamic.
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
