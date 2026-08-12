import type { NextConfig } from "next";

// API origin allowed for fetch/SSE. Defaults to the production Railway URL;
// override via NEXT_PUBLIC_API_URL at build time. Read here only to construct
// the CSP — the value itself is intentionally public (it's a URL).
const apiUrl =
  process.env.NEXT_PUBLIC_API_URL ?? "https://kite-lab-production.up.railway.app";

// In `next dev` we additionally allow the locally-running backend. Without
// this the CSP `connect-src` blocks calls to localhost:8000 even though
// `src/lib/api-client.ts` falls back to it. NODE_ENV is "development" only
// under `next dev` — production builds (including `next start`) omit it.
const devApiOrigin =
  process.env.NODE_ENV === "development" ? "http://localhost:8000" : "";

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
// Clerk SDK lives on `*.clerk.accounts.dev`; the user-facing accounts portal
// is on the bare `*.accounts.dev`. Both need allowlisting for sign-in flows
// to navigate through cleanly (cross-domain session sync, satellite-domain
// redirects, etc.).
//
// In production Clerk serves the Frontend API + ClerkJS from our custom domain
// (`clerk.marketworks.in`), not `*.clerk.accounts.dev`, so it must be
// allowlisted or ClerkJS fails to load and sign-in silently breaks. The
// `*.accounts.dev` / `*.clerk.accounts.dev` entries are kept so local/dev
// (test instance) still works. See docs/security/risk-register.md R-006.
const clerkOrigins =
  "https://clerk.marketworks.in https://*.clerk.accounts.dev https://*.accounts.dev https://*.clerk.com";
const turnstileOrigin = "https://challenges.cloudflare.com";

// Supabase Auth (auth_stack_v2, register row R-027): the project origin
// serves /auth/v1/* (token, otp, authorize, user). Exact single origin
// derived from the env var — no wildcard. connect-src only: supabase-js
// is bundled (no CDN script), OAuth is a top-level redirect (not a frame
// or form POST), so no other directive needs it. Clerk origins remain
// until the Phase 4 cutover removes the Clerk verification path (C4.5
// narrows this CSP again).
const supabaseOrigin = (() => {
  try {
    return new URL(process.env.NEXT_PUBLIC_SUPABASE_URL ?? "").origin;
  } catch {
    return "";
  }
})();

const cspDirectives = [
  `default-src 'self'`,
  `script-src 'self' 'unsafe-inline' 'unsafe-eval' ${clerkOrigins} ${turnstileOrigin} https://accounts.google.com https://*.gstatic.com`,
  `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`,
  `img-src 'self' data: blob: https:`,
  `font-src 'self' data: https://fonts.gstatic.com`,
  `connect-src 'self' ${apiUrl} ${devApiOrigin} ${supabaseOrigin} ${clerkOrigins} ${turnstileOrigin} https://accounts.google.com https://oauth2.googleapis.com https://*.googleapis.com`,
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
  // Next 16.3 generates AGENTS.md/CLAUDE.md by default — suppressed:
  // this repo manages its own agent context at the root.
  agentRules: false,
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
