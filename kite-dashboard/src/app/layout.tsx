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
