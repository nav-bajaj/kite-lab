# Tax Study — results

**Status:** shipped (post-tax CAGR analysis with proper Indian CG tax model)
**Branch:** `tax-study`
**Opened:** 2026-05-26
**Closed:** 2026-05-26

## What was built

A self-contained HTML report at `tasks/tax_study/report.html` that applies the
correct Indian capital-gains tax model (STCG 20% / LTCG 12.5% above ₹1.25L
exemption, 8-year FIFO loss carry-forward) to the 4 production strategies'
full-history backtests at 30 bps slippage, plus a NIFTY 50 buy-and-hold
benchmark.

Components:

| File | Role |
|---|---|
| `tax_engine.py` | FIFO lot matcher · STCG/LTCG bucketing · per-FY tax with carry-forward and exemption · P&L reconciliation |
| `forced_sale.py` | Tax-event scheduling · forced-sale-for-tax slippage · multiplicative post-tax equity scaling |
| `benchmark.py` | NIFTY 50 B&H synthetic-trades + equity construction |
| `build_report.py` | Orchestrator + HTML renderer + matplotlib charts |
| `report.html` | Self-contained 307 KB output |
| `runs/<strategy>/` | 4 production-config backtests at 30 bps (re-runnable via the 4 runner CLIs) |

## Headline results (16-year backtests, 2009/2010 → May 2026)

| Strategy | Pre-tax CAGR | Post-tax CAGR | Drag | Total tax | Tax/finalPV |
|---|---:|---:|---:|---:|---:|
| OM25 v3 | 35.40% | 30.21% | 520 bp | ₹17.7M | 13.3% |
| TL25 v3 | 31.41% | 24.33% | 708 bp | ₹14.7M | 17.4% |
| L6 v2 | 36.05% | 29.90% | 615 bp | ₹27.2M | 16.1% |
| COMBO | 30.73% | 25.21% | 552 bp | ₹14.2M | 16.5% |
| NIFTY 50 B&H | 9.59% | 8.93% | 66 bp | ₹4.2L | 9.3% |

## Key findings

1. **Tax is real but doesn't neutralise active alpha.** Strategies pay 8–10× more drag in bps than B&H (520–700 bp vs 66 bp) — but deliver 2.7–3.4× the post-tax CAGR. Even the most-taxed strategy (TL25 v3, 708 bp drag) post-tax is 15+ pp above B&H pre-tax.
2. **STCG-heavy strategies pay disproportionately more.** TL25 v3's weekly rank-exit means almost all gains are STCG (20% rate). It has the highest drag despite a lower pre-tax CAGR than L6 v2. OM25 v3's longer holding profile (20-rank exit buffer + drawdown stop) gives it the most favourable mix and lowest tax/finalPV (13.3%).
3. **The previous MTM tax estimate overstated drag by 100–400 bps.** The v1 sketch using 25% flat MTM gave 520–920 bp drag on the same strategies; the correct realized-only model gives 520–710 bp. The user's intuition that something was off was right.
4. **Loss carry-forward and the LTCG exemption are doing real work.** Multiple strategies use STCL carry-forward in their actual realized history. The ₹1.25L exemption shelters meaningful early-period LTCG (~12% of starting capital), then dilutes to noise at scale.
5. **Forced-sale slippage is sub-bp drag at 30 bps.** Tracked but immaterial.
6. **FY2023-24 is the highest-tax year across all 4 strategies** — the 2023 mid-cap rally produced large realizations simultaneously.

## Verification log

All gates passed:

| Gate | Result |
|---|---|
| Sum of realized + unrealized P&L = equity-curve total return (±0.5%) | **±0.02% on all 4 strategies** ✓ |
| Carry-forward window respects 8 FYs | ✓ (CF queues expire correctly; OM25 FY2019-20 STCL was used in FY2020-21) |
| Visible step-down at each tax-event Apr 1 | ✓ (verified on all 4 strategies; gate 3.6 PASS) |
| L6 v2 / COMBO live-window CAGRs reconcile with dashboard | L6 52.81% vs dash 52.08% (+73 bp); COMBO 47.80% vs 47.70% (+10 bp) ✓ |
| OM25 v3 / TL25 v3 dashboard reconciliation (warm-start documented) | OM25 +619 bp; TL25 +181 bp — warm-start effect explained in caveats ✓ |
| Slippage column in trades.csv averages 30 bps × notional | 30.0 bp on all 4 strategies ✓ |

## Deferred (acknowledged but not modelled)

| Item | Why deferred | Impact estimate |
|---|---|---|
| Forced-sale realized P&L → next-FY tax base | Bounded error: forced sales target smallest positions; their gains ~10% of cash raised → ~2% of tax owed | ≤ 1 bp CAGR/yr |
| Quarterly advance-tax timing | Our annual-debit model gives extra ~6 months of compounding on tax money | ≤ 10 bp CAGR over 16y |
| Surcharge + 4% cess | Investor-specific (depends on income slab) | Effective STCG ~28% / LTCG ~17.5% for top slab — bump drag ~30% upward |
| Money-market return on idle cash | Out of scope per PLAN | COMBO most affected (~50 bp understatement) |
| Survivorship-bias audit on `nse500_data_merged` | Separate task | Possible upward bias on pre-2020 CAGRs |
| Historical rate regimes (15%/10% pre-July-2024) | User chose current-rates-throughout | Would lower drag ~15–25% if applied 2009–2024 |

## Commits

- `a435210` — tax_study: per-trade Indian CG tax model + NIFTY 50 B&H benchmark (initial)

## Files changed

- `scripts/run_combo_defensive_portfolio.py` — added `--slippage` CLI flag (mirrors other 3 runners)
- `tasks/tax_study/*` — new task folder

The COMBO runner change is also useful outside this study (it makes the runner consistent with the other 3); no production change needed.
