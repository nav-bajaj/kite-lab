# Task 8: Implement NextAuth.js with Google OAuth

**Status**: `completed`
**Blocked By**: #6 (Next.js Setup)
**Blocks**: #11

## Objective

Set up authentication with NextAuth.js using Google OAuth and email whitelist validation.

## Tasks

- [x] Install next-auth
- [x] Create auth route handler
- [x] Configure Google OAuth provider
- [x] Implement email whitelist validation
- [x] Set up session handling
- [x] Create middleware for protected routes
- [x] Create login page

## Install Dependencies

```bash
cd kite-dashboard
npm install next-auth
```

## Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Navigate to APIs & Services → Credentials
4. Create OAuth 2.0 Client ID
5. Configure authorized redirect URIs:
   - Development: `http://localhost:3000/api/auth/callback/google`
   - Production: `https://kite-dashboard.vercel.app/api/auth/callback/google`
6. Copy Client ID and Client Secret

## src/app/api/auth/[...nextauth]/route.ts

```typescript
import NextAuth, { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";

const ALLOWED_EMAILS = (process.env.ALLOWED_EMAILS || "").split(",").map(e => e.trim());

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async signIn({ user }) {
      // Check email whitelist
      if (!user.email || !ALLOWED_EMAILS.includes(user.email)) {
        return false; // Reject sign in
      }
      return true;
    },
    async jwt({ token, user, account }) {
      // Initial sign in
      if (account && user) {
        return {
          ...token,
          accessToken: account.access_token,
          email: user.email,
          name: user.name,
          picture: user.image,
        };
      }
      return token;
    },
    async session({ session, token }) {
      // Send properties to the client
      session.user = {
        ...session.user,
        email: token.email as string,
        name: token.name as string,
        image: token.picture as string,
      };
      // Include token for API calls
      (session as any).accessToken = token.accessToken;
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: {
    strategy: "jwt",
    maxAge: 24 * 60 * 60, // 24 hours
  },
};

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
```

## src/app/login/page.tsx

```tsx
"use client";

import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (session) {
      router.push("/");
    }
  }, [session, router]);

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-[400px]">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Kite-Lab Dashboard</CardTitle>
          <CardDescription>
            Sign in to access your portfolio dashboard
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            className="w-full"
            onClick={() => signIn("google", { callbackUrl: "/" })}
          >
            <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              />
            </svg>
            Sign in with Google
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
```

## src/app/layout.tsx (Update)

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Kite-Lab Dashboard",
  description: "Momentum Portfolio Management Dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

## src/app/providers.tsx

```tsx
"use client";

import { SessionProvider } from "next-auth/react";
import { ThemeProvider } from "next-themes";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        {children}
      </ThemeProvider>
    </SessionProvider>
  );
}
```

Install next-themes:
```bash
npm install next-themes
```

## src/middleware.ts

```typescript
import { withAuth } from "next-auth/middleware";

export default withAuth({
  pages: {
    signIn: "/login",
  },
});

export const config = {
  matcher: [
    // Protect all routes except login, api/auth, and static files
    "/((?!login|api/auth|_next/static|_next/image|favicon.ico).*)",
  ],
};
```

## Environment Variables

```bash
# .env.local
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=generate-32-character-random-string

GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

ALLOWED_EMAILS=your-email@gmail.com
```

Generate NEXTAUTH_SECRET:
```bash
openssl rand -base64 32
```

## Type Augmentation (optional)

Create `src/types/next-auth.d.ts`:

```typescript
import { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session extends DefaultSession {
    accessToken?: string;
    user: {
      email: string;
      name: string;
      image: string;
    } & DefaultSession["user"];
  }
}
```

## Verification

1. Start the development server:
   ```bash
   npm run dev
   ```

2. Visit http://localhost:3000
   - Should redirect to /login

3. Click "Sign in with Google"
   - Should redirect to Google OAuth
   - After sign in, should redirect back to dashboard

4. Test unauthorized email:
   - Sign in with an email NOT in ALLOWED_EMAILS
   - Should be rejected

## Notes

- Only emails in ALLOWED_EMAILS can sign in
- Session lasts 24 hours by default
- JWT strategy means no database required for sessions
- The accessToken can be used for API calls to the backend

---

*Last updated: February 2026*
