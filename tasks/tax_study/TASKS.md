# Tax Study — task list

Owners: 🤖 = Claude does it, 👤 = user reviews / decides.
Risk tags: 🔴 high (can invalidate the report), 🟡 medium (changes numbers but not direction), 🟢 low (cosmetic / nice-to-have).

## Phase 1 — Regenerate backtests at 30 bps slippage

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 1.0 | Add `--slippage` CLI flag to `run_combo_defensive_portfolio.py` (the other 3 runners already have it) | 🤖 | 🟡 | ✅ |
| 1.1 | Re-run `run_om25_v3_portfolio.py` `--slippage 0.003 --start 2009-09-01 --output-dir tasks/tax_study/runs/om25_v3` | 🤖 | 🟡 | ✅ |
| 1.2 | Same for `run_tl25_v3_portfolio.py` | 🤖 | 🟡 | ✅ |
| 1.3 | Same for `run_l6_v2_portfolio.py` | 🤖 | 🟡 | ✅ |
| 1.4 | Same for `run_combo_defensive_portfolio.py` | 🤖 | 🟡 | ✅ |
| 1.5 | Verify slippage column in trades.csv averages ≈ 0.3% × notional | 🤖 | 🔴 | ✅ |
| 1.6 | Compare live-window CAGRs vs dashboard. L6 / COMBO must reconcile to ~100 bps. OM25 / TL25 expected to diverge due to warm-start advantage; document, do not gate. | 🤖 | 🔴 | ✅ |

## Phase 2 — Per-trade tax engine

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 2.1 | Build `tax_engine.py` with FIFO lot matcher (per-symbol BUY→SELL pairing) | 🤖 | 🔴 | ✅ |
| 2.2 | Realized P&L per matched lot uses effective prices (notional ± slippage) | 🤖 | 🔴 | ✅ |
| 2.3 | Classify each realized P&L as STCG or LTCG by `(sell_date - buy_date) > 365`-day threshold | 🤖 | 🔴 | ✅ |
| 2.4 | Aggregate STCG / LTCG per FY (Apr 1 → Mar 31) | 🤖 | 🔴 | ✅ |
| 2.5 | Apply 8-year FIFO loss carry-forward: STCL offsets STCG-or-LTCG; LTCL offsets LTCG only | 🤖 | 🔴 | ✅ |
| 2.6 | Apply ₹1.25L FY LTCG exemption | 🤖 | 🟡 | ✅ |
| 2.7 | Apply rates: STCG 20%, LTCG 12.5% on the net taxable amount | 🤖 | 🔴 | ✅ |
| 2.8 | Sanity check passes for all 4 strategies (diff < 0.02% on all; ≪ 0.5% threshold) | 🤖 | 🔴 | ✅ |

## Phase 3 — Forced-sale-for-tax simulation

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 3.1 | At each Apr 1, compute tax owed for prior FY (from Phase 2 results) | 🤖 | 🔴 | ✅ |
| 3.2 | Simplified to: assume cash << tax (fully-invested strategies) — entire tax requires forced sale. Documented in caveats. | 🤖 | 🔴 | ✅ |
| 3.3 | Apply 30 bps slippage: forced_slippage = tax × 0.003 / 0.997 (gross-up to net the tax). Verified = 0.301% on all 4. | 🤖 | 🟡 | ✅ |
| 3.4 | Realized gain from forced sales NOT propagated to next FY (deferred — propagation error bounded to a few bps of CAGR/yr per analysis in `forced_sale.py` docstring) | 🤖 | 🟡 | 🟡 |
| 3.5 | Multiplicative scale on equity curve at each tax event (matches "investor pays tax from portfolio account") | 🤖 | 🔴 | ✅ |
| 3.6 | Step-down at each Apr 1 with tax owed — verified on all 4 strategies (gate 3.6 PASS) | 🤖 | 🟢 | ✅ |

## Phase 4 — Nifty 50 buy-and-hold benchmark

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 4.1 | NIFTY 50 historical (`indices_data_full/NIFTY_50.csv`) covers 2010-01-04 → 2026-05-12 ✓ | 🤖 | 🟢 | ✅ |
| 4.2 | `benchmark.py` synthesises a 2-row trades.csv (one BUY, one SELL) + equity curve | 🤖 | 🟢 | ✅ |
| 4.3 | B&H runs through `tax_engine` → single LT realized event (5972-day hold) ✓ | 🤖 | 🟢 | ✅ |
| 4.4 | Deferred-tax handling added so B&H comparison is apples-to-apples (final FY tax provisioned on last equity day instead of silently dropped) | 🤖 | 🔴 | ✅ |

## Phase 5 — Year-by-year breakdown

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 5.1 | Per-FY data already exposed by `tax_engine.compute_tax_per_fy` (FYTax dataclass) — reused in build_report | 🤖 | 🟢 | ✅ |
| 5.2 | Stacked bar chart (per-FY STCG + LTCG × 4 strategies) embedded in report | 🤖 | 🟢 | ✅ |
| 5.3 | FY2023-24 identified as largest realization year across all 4 strategies — noted in chart caption | 🤖 | 🟢 | ✅ |

## Phase 6 — HTML report

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 6.1 | `build_report.py` written — loads strategies + B&H, runs full engine, renders charts, writes HTML | 🤖 | 🟡 | ✅ |
| 6.2 | Full-period table (5 rows) + per-strategy window table (8 rows) + B&H sub-window table (4 rows) | 🤖 | 🟡 | ✅ |
| 6.3 | Three charts: CAGR bars, equity-curve small multiples, per-FY stacked tax bars | 🤖 | 🟢 | ✅ |
| 6.4 | Caveats block — covers warm-start, forced-sale-propagation, advance-tax timing, surcharge/cess, money-market cash, capital scale, survivorship | 🤖 | 🟢 | ✅ |
| 6.5 | L6 v2 / COMBO live-window CAGRs reconcile with dashboard ±100 bps. OM25 / TL25 warm-start gap documented in caveats. | 👤 + 🤖 | 🔴 | ✅ |

## Phase 7 — Close out

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 7.1 | Commit + push to `tax-study` branch (commit `a435210`, pushed) | 🤖 | 🟢 | ✅ |
| 7.2 | Open PR back to main — `gh pr create` or via https://github.com/nav-bajaj/kite-lab/pull/new/tax-study | 👤 | 🟢 | ☐ |
| 7.3 | `RESULTS.md` written; `_meta.yml` status → `shipped` | 🤖 | 🟢 | ✅ |
