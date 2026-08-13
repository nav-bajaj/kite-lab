import type { Metadata } from "next";
import {
  Geist,
  Geist_Mono,
  Libre_Baskerville,
  Outfit,
  IBM_Plex_Mono,
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

// Brand fonts (loop 25, tasks/design_studies/brand/): Libre Baskerville =
// display serif (variable 400-700; 500 is the working display weight),
// Outfit = sans body/UI, IBM Plex Mono = the data voice (figures, labels,
// captions, tickers, axes — never body text). Self-hosted by next/font
// (CSP-safe; no CDN). Used by `.mw-brand` surfaces; the app shell keeps
// Geist until the dashboard port.
const libreBaskerville = Libre_Baskerville({
  variable: "--font-libre-baskerville",
  subsets: ["latin"],
  style: ["normal", "italic"],
});

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
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
          className={`${geistSans.variable} ${geistMono.variable} ${libreBaskerville.variable} ${outfit.variable} ${plexMono.variable} antialiased`}
        >
          <Providers>{children}</Providers>
          <SpeedInsights />
        </body>
      </html>
    </ClerkProvider>
  );
}
