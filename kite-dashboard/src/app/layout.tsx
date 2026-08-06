import type { Metadata } from "next";
import {
  Geist,
  Geist_Mono,
  Fraunces,
  Outfit,
  Schibsted_Grotesk,
} from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { SpeedInsights } from "@vercel/speed-insights/next";
import "./globals.css";
import { Providers } from "./providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Brand fonts (DESIGN.md §3) — self-hosted by next/font (CSP-safe; no CDN).
// Used by the `.mw-brand` marketing/library surfaces. The rest of the app
// keeps Geist. Fraunces = display serif, Outfit = sans body/UI.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
});

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

// design_studies loop 7: heading sans under study (founder: two sans faces —
// Outfit for content, a slightly stylized one for headings). Schibsted
// Grotesk is the shortlist pick; swap here to trial alternatives.
const schibsted = Schibsted_Grotesk({
  variable: "--font-schibsted",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Marketworks Dashboard",
  description: "Momentum Portfolio Management Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider
      signInFallbackRedirectUrl="/"
      signUpFallbackRedirectUrl="/"
    >
      <html lang="en" suppressHydrationWarning>
        {/* Stack Sans Text (design_studies heading trial) predates this Next
            version's next/font data, so it loads via the Google Fonts
            stylesheet (CSP already allows these origins; React hoists the
            links). Self-host via next/font after the next Next.js upgrade. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        {/* eslint-disable-next-line @next/next/no-page-custom-font -- rule
            targets the pages router; this is the App Router ROOT layout, so
            the stylesheet applies to every route */}
        <link
          rel="stylesheet"
          precedence="default"
          href="https://fonts.googleapis.com/css2?family=Stack+Sans+Text:wght@500;600;700&display=swap"
        />
        <body
          className={`${geistSans.variable} ${geistMono.variable} ${fraunces.variable} ${outfit.variable} ${schibsted.variable} antialiased`}
        >
          <Providers>{children}</Providers>
          <SpeedInsights />
        </body>
      </html>
    </ClerkProvider>
  );
}
