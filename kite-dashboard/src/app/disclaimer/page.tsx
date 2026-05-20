export const metadata = {
  title: "Disclaimer — Marketworks",
};

export default function DisclaimerPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-12 prose prose-neutral dark:prose-invert">
      <h1>Investment Disclaimer</h1>

      <div className="rounded-md border border-amber-300/40 bg-amber-50 p-4 text-sm dark:bg-amber-950/30 not-prose">
        <p className="m-0 font-medium">
          Marketworks is in <strong>Private Beta</strong>. SEBI Research
          Analyst registration is currently applied for. All content,
          features, and portfolio data on the platform are made available
          for <strong>testing, research, and educational purposes only</strong>.
          Nothing on this site is investment advice or a recommendation to
          buy or sell any security.
        </p>
      </div>

      <h2>Not investment advice</h2>
      <p>
        The model portfolios Marketworks publishes are outputs of
        rules-based quantitative strategies. They are exposed to invited
        users to demonstrate the system and to gather feedback during the
        beta period. They are not personalised to your financial situation,
        risk tolerance, or tax position.
      </p>

      <h2>No broker linkage</h2>
      <p>
        Marketworks does not place trades on your behalf and does not
        connect to your brokerage account. Any decision to act on the
        platform&apos;s outputs is solely your own and executed entirely
        through your own broker.
      </p>

      <h2>Past performance ≠ future returns</h2>
      <p>
        Backtest results and historical metrics shown here are derived
        from published market data and our own strategy implementations.
        They are not guarantees of future performance. The Indian equity
        market is volatile; loss of capital is possible and expected in
        adverse periods.
      </p>

      <h2>Regulatory status</h2>
      <p>
        Application for registration as a SEBI Research Analyst is in
        progress. Until the registration is granted and announced on this
        page, Marketworks should not be relied upon as a SEBI-regulated
        research or advisory service. By using the platform during the
        beta you acknowledge this position.
      </p>

      <h2>Your responsibility</h2>
      <p>
        Evaluate every model portfolio against your own situation. Consider
        consulting a SEBI-registered investment adviser before acting on
        any portfolio decision.
      </p>
    </div>
  );
}
