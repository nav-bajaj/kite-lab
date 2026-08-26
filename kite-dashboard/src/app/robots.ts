import type { MetadataRoute } from "next";

import { siteMode } from "@/lib/site-mode";

// Evaluated at build time; SITE_MODE is present at build on Vercel and
// every flip of the var is a redeploy, so this stays consistent with the
// middleware gate (tasks/site_gate).
export default function robots(): MetadataRoute.Robots {
  if (siteMode() === "under_development") {
    return {
      rules: { userAgent: "*", disallow: "/" },
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
