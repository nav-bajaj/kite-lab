import { Suspense } from "react";
import Link from "next/link";

import { SignInCard } from "@/components/auth/sign-in-card";
import { FlowGrid } from "@/components/marketing/flow-grid";

export const metadata = {
  title: "Sign in — Marketworks",
};

export default function SignInPage() {
  return (
    <div className="mw-brand relative flex min-h-screen flex-col overflow-hidden bg-surface-base">
      <FlowGrid />
      <header className="relative z-10 px-6 py-5 sm:px-12">
        <Link
          href="/"
          className="text-2xl font-semibold tracking-tight text-primary"
        >
          marketworks
        </Link>
      </header>
      <div className="relative z-10 flex flex-1 flex-col items-center justify-center gap-8 px-6 pb-20">
        <h1 className="font-serif text-3xl font-medium text-foreground">
          Welcome back
        </h1>
        {/* Suspense: SignInCard reads useSearchParams (oauth error echo). */}
        <Suspense fallback={null}>
          <SignInCard />
        </Suspense>
      </div>
    </div>
  );
}
