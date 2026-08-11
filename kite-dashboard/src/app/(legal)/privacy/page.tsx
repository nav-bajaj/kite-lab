export const metadata = {
  title: "Privacy Policy — Marketworks",
};

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-12 prose prose-neutral dark:prose-invert">
      <h1>Privacy Policy</h1>

      <p className="text-sm text-muted-foreground">
        Last updated: <strong>11 August 2026</strong>
      </p>

      <h2>What we collect</h2>
      <p>
        When you sign up we collect your email address and (if you choose to
        sign in via Google) your name and profile picture from your Google
        account. Authentication is delegated to{" "}
        <a href="https://supabase.com">Supabase</a>; sign-in is passwordless
        (one-time email codes or Google), so we never store a password.
      </p>

      <h2>What we do with it</h2>
      <p>
        We use your account identity solely to authenticate you to the
        dashboard. We do not sell, share, or use your personal data for
        advertising or marketing purposes.
      </p>

      <h2>Third parties</h2>
      <ul>
        <li>
          <strong>Supabase</strong> — authentication, session management,
          account profile storage.
        </li>
        <li>
          <strong>Amazon Web Services (SES)</strong> — delivery of sign-in
          code emails.
        </li>
        <li>
          <strong>Vercel</strong> — frontend hosting.
        </li>
        <li>
          <strong>Railway</strong> — backend hosting and database.
        </li>
        <li>
          <strong>Google</strong> — OAuth provider when you sign in with
          Google.
        </li>
        <li>
          <strong>Cloudflare (Turnstile)</strong> — bot protection on the
          sign-in form.
        </li>
      </ul>

      <h2>Cookies</h2>
      <p>
        We use only the cookies strictly required to keep you signed in (set
        by Supabase Auth). No analytics or advertising cookies.
      </p>

      <h2>Data retention</h2>
      <p>
        Your account data is retained while your account is active. To delete
        your account, email{" "}
        <a href="mailto:navdeep@marketworks.in">navdeep@marketworks.in</a>{" "}
        from your registered address; the underlying record is removed from
        Supabase and from our database within 30 days.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about this policy can be sent to{" "}
        <a href="mailto:navdeep@marketworks.in">navdeep@marketworks.in</a>.
      </p>
    </div>
  );
}
