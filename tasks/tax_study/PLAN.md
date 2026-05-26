# Tax Study — proper per-trade Indian CG tax model

## Why

An initial flat-25% mark-to-market sketch was rejected on adversarial review:

- Real Indian CG tax only applies to **realized** gains, not annual MTM.
- 25% flat is wrong — current law is STCG 20% / LTCG 12.5% above ₹1.25L.
- No holding-period split (STCG vs LTCG).
- No annual exemption.
- No loss carry-forward.
- The cost of *raising cash to pay tax* (forced sale, slippage) wasn't modelled.

This study fixes all of those and adds two diagnostic views: a year-by-year tax
breakdown, and a Nifty 50 buy-and-hold post-tax benchmark for comparison.

## Outcome

A reproducible HTML report at `tasks/tax_study/report.html` that, for each of
the 4 production strategies, shows:

- Pre-tax and post-tax CAGR over each strategy's IS / OOS / live-track window
- Per-FY tax bills (STCG + LTCG breakdown)
- Total tax as % of pre-tax final value
- Comparison to a Nifty 50 buy-and-hold post-tax baseline
- All numbers reconcile with the dashboard's live-track CAGRs to within 50 bps

## Spec — locked

### Slippage

**30 bps** (0.003) on all trades, including forced-sale-for-tax trades.
Backtests at this slippage live in `tasks/tax_study/runs/<strategy>/`.

### Tax rates (current Indian law, applied throughout 2009–2026)

| Bucket | Rate | Holding period |
|---|---|---|
| STCG (equity) | 20% | ≤ 12 months |
| LTCG (equity) | 12.5% above ₹1.25L FY exemption | > 12 months |

The exemption is per-FY-per-investor; we model one investor per strategy.

### Lot accounting

**FIFO** — the standard for Indian equity-tax computation. For each symbol,
match each SELL against the oldest unmatched BUY lots. Realized P&L per lot:
`(sell_price - buy_price) × shares_matched`. Holding period determines bucket.

### Loss carry-forward

8-year FIFO carry-forward, per Indian CG rules.
- Short-term losses offset short-term *or* long-term gains.
- Long-term losses offset long-term gains only.
- Unused losses carry forward up to 8 FYs.

### Tax-payment mechanics

- Tax for FY-N is paid on **Apr 1 of FY-(N+1)** (single annual debit — not
  modelling quarterly advance tax in v2; see "deferred" below).
- On tax day, if idle cash < tax owed, the engine sells the **smallest** open
  positions (by notional) until cash ≥ tax owed.
- Each forced sale incurs the 30 bps slippage and triggers its own realized
  gain → adds to next FY's tax base (one-shot, not iterated within same FY).
- The forced sale modifies the equity curve from that date onward.

### Window labels

Per-strategy by tuning history (carried over from v1):

| Strategy | Window 1 | Window 2 |
|---|---|---|
| OM25 v3 | IS (2009-09-01 → 2016-12-31) | OOS (2017-01-01 → 2026-05-08) |
| TL25 v3 | IS (2009-09-01 → 2016-12-31) | OOS (2017-01-01 → 2026-05-08) |
| L6 v2 | Pre-IS (2009-09-01 → 2019-12-31) | IS (2020-01-01 → 2026-05-08) |
| COMBO | Pre-IS (2009-09-01 → 2019-12-31) | IS (2020-01-01 → 2026-05-08) |

### Initial capital

₹10L per strategy (matches the runner default). The ₹1.25L LTCG exemption is
∼12.5% of starting capital — large early, negligible at scale. Note this in
caveats; do not bias the analysis to a particular wealth level.

### Nifty 50 buy-and-hold benchmark

Buy at window start with ₹10L, hold to window end, single sell at end →
single LTCG event. Apply the same rates and exemption.

## Out of scope (deferred)

| Deferred item | Why |
|---|---|
| Quarterly advance-tax timing | Materially complex; annual-debit is a small optimism but order-of-magnitude correct. |
| Money-market return on idle cash | User opted out — would lift COMBO's pre-tax CAGR by ~100 bps. |
| STT, brokerage, GST on brokerage | Already partially captured in slippage; itemising is a separate study. |
| Surcharge & cess on high incomes | Investor-specific (depends on total income); out of scope for portfolio-level analysis. |
| Survivorship-bias audit on price panel | Separate task — would re-derive `nse500_data_merged` from point-in-time membership. |
| Historical rate regimes (15% / 10% pre-July-2024) | User chose current-rates-throughout. |

## Critical files

| File | Role |
|---|---|
| `scripts/run_<strat>_portfolio.py` | Runners — invoked at 30 bps to regenerate trades.csv |
| `tasks/tax_study/runs/<strat>/<strat>_trades.csv` | Per-trade record — the input to the tax engine |
| `tasks/tax_study/runs/<strat>/<strat>_equity.csv` | Daily PV — for charting and CAGR |
| `tasks/tax_study/tax_engine.py` | NEW — FIFO lot matcher + tax calculator |
| `tasks/tax_study/forced_sale.py` | NEW — tax-day cash-raise simulator |
| `tasks/tax_study/build_report.py` | NEW — entry point, runs engine + writes HTML |
| `tasks/tax_study/report.html` | Output |

## Verification gates

The report cannot be considered done until:

1. **Backtests internally consistent.** Trades CSV reproduces the equity CSV's
   total return when applied as a sequence of cash flows (within ±0.5%).
2. **Each strategy's total realized P&L** (sum across all matched lots) plus
   unrealised P&L on positions held at the final date equals the equity curve's
   total return (within ±0.5%).
3. **Carry-forward losses** at any point ≤ 8-FY rolling window.
4. **Forced-sale dates** produce visible step-down in the equity curve.
5. **L6 v2 and COMBO live-window CAGRs reconcile with the dashboard** to within
   ~100 bps (allows for the 30→20 bps slippage delta plus minor data-panel diffs).
   OM25 v3 and TL25 v3 are *not* gated against the dashboard because their
   long-history backtest sits on years of accumulated positions at the start of
   the dashboard's live window — a warm-start advantage worth several pp in CAGR.
   This is expected behaviour, not a bug.
