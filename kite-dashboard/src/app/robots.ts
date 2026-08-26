import type { MetadataRoute } from "next";

import { siteMode } from "@/lib/site-mode";

// Evaluated at build time; SITE_MODE is present at build on Vercel and
// every flip of the var is a redeploy, so this stays consistent with the
// middleware gate (tasks/site_gate).
export default function robots(): MetadataRoute.Robots {
  if (siteMode() === "under_development") {
    // Deliberately crawlable while gated: crawlers must be able to re-visit
    // the previously-indexed pages to see the 307s and the sitewide
    // X-Robots-Tag: noindex (next.config.ts) and drop them from the index.
    // Disallow: / would freeze the old index entries in place.
    return {
      rules: { userAgent: "*", allow: "/" },
    };
  }
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard", "/admin", "/account"],
    },
  };
}
