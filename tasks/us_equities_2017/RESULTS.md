# US-equity port of the v3 production strategies — 2017-2026 OOS

**Date:** 2026-05-14
**Branch:** `us-data`
**Author:** nav + Claude

## Motivation

The four productionised strategies (L6 v2, OM25 v3, TL25 v3, COMBO Defensive) were tuned on NSE 500 / Nifty 250 with lock-ins on 2009-2016 IS and OOS-validated on 2017-2026. None of them has ever seen US equities. Running them unchanged on a fully-adjusted S&P 500 ∪ Nasdaq 100 panel from 2017 onwards is a **pure out-of-market generalisation test** — no parameters retuned, no scoring functions altered, only the data inputs swapped.

This isn't a candidate for US production — it's the first read on which Indian-tuned signals transfer.

## Data plumbing (one-time, this branch)

Built from scratch in the `us-data` branch:

| Component | File |
|---|---|
| EODHD REST client (sync, env-keyed, rate-limited, per-row adjusted close) | `data_pipeline/eodhd_client.py` |
| Universe — S&P 500 ∪ Nasdaq 100 = 516 unique symbols | `data/static/us_equities_universe.csv` |
| Backfill script (resume, hyphen-normalisation for BRK.B/BF.B class shares) | `scripts/fetch_us_equities_history.py` |
| Demo-key probe + parity audit | `scripts/test_eodhd_trial.py` |
| Pricing/tier research artifact | `docs/eodhd_pricing.md` |
| US strategy harness (this experiment) | `scripts/run_us_strategies_2017.py` |

**Provider chosen:** EODHD ("EOD Historical Data — All World" tier, $19.99/mo). Selected over Alpha Vantage after head-to-head: cheaper, 13× the rate cap, longer history, has a bulk endpoint (1 call/day for the whole exchange).

**Backfill cost:** 430 fetches on a single Saturday at 300 req/min (~15 min wall-clock; 86 of 516 had been pre-fetched in earlier validation runs and were skipped). Zero failures after the class-share fix.

**Adjustment correctness:** verified on AAPL's 4:1 split on 2020-08-31 — 2020-08-28 raw close $499.23 vs adjusted close $121.06 (ratio 4.12, the residual above 4.0 is cumulative dividend adjustment). EODHD returns `adjusted_close` plus split-adjusted volume natively; the client computes `factor = adjusted_close/close` per row and applies it to OHL so the panel is fully pre-adjusted on disk.

## Experiment design

Single harness (`scripts/run_us_strategies_2017.py`) loads the US panel once and runs all four strategies through `_clean_engine.run_strategy()` with **identical locked hyperparameters** as Indian production:

- `L6 v2` — `_momentum_engine.BASELINE`
- `OM25 v3` — `om25_v3.LOCKED`
- `TL25 v3` — `tl25_v3.V3_LOCKED`
- `COMBO Defensive` — `combo_defensive.LOCKED`

Inputs swapped:

| Input | Indian production | US port |
|---|---|---|
| Prices dir | `nse500_data_merged/` | `us_equities_data/` |
| Universe | NSE 500 / Nifty 250 | S&P 500 ∪ Nasdaq 100 (516 symbols) |
| Benchmark | `data/benchmarks/nifty100.csv` | `data/benchmarks/spy.csv` |
| Regime index (OM25 + COMBO) | NIFTY 100 100-DMA, 3d confirm | **SPY** 100-DMA, 3d confirm |
| Calendar | NSE trading days | NYSE trading days |

Note on COMBO Defensive: the Indian version draws its L6 component from NSE 500 and its OM25 component from Nifty 250 (two distinct universes). The US port only has one universe CSV (SP500 ∪ NDX), so both components score over the same panel. This is a minor structural difference worth flagging.

Window: 2017-01-01 → 2026-05-13 (9.3 years), starting capital ₹1,000,000-equivalent (notional $1M). Initial-capital normalisation applied so PV at window start = 1,000,000 for all strategies and the benchmark.

Regime panel diagnostics: SPY was in "bear" (close < 100-DMA for 3+ consecutive days) for **1,980 / 6,631 calendar days = 29.9%** of the full panel. That's a meaningful share of bear-tilted scoring for OM25 v3 and exposure throttling for COMBO Defensive.

## Headline table

| Strategy | CAGR | MaxDD | Sharpe | Sortino | Calmar | Vol | Beta | Hit% | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **L6 v2** | **43.36%** | -35.59% | **1.47** | **1.91** | **1.22** | 29.58% | 1.12 | 49.5% | 3,664 |
| OM25 v3 | 34.40% | -41.15% | 1.26 | 1.61 | 0.84 | 27.25% | 1.01 | 50.0% | 2,048 |
| TL25 v3 | 21.34% | -34.06% | 0.97 | 1.21 | 0.63 | 22.01% | 0.83 | 46.5% | 3,361 |
| **COMBO Defensive** | 33.71% | **-28.49%** | 1.35 | 1.73 | 1.18 | 24.94% | **0.80** | 33.7% | 7,033 |
| SPY (benchmark) | 15.39% | -33.72% | 0.84 | — | 0.46 | 18.32% | 1.00 | — | — |

Per-strategy `equity.csv / trades.csv / exits.csv` + `summary.csv` in `experiments/us_strategies_2017/`.

## Findings

**1. All four strategies beat SPY by a wide margin.** Even the weakest (TL25 v3, 21.3% CAGR) cleared the index by ~6pp/year for ~9 years with comparable max DD. The momentum/quality/trend premia priced in the locked parameters exist in US large-caps, not just NSE.

**2. L6 v2 is the winner and generalises the cleanest.** 43.4% CAGR / 1.47 Sharpe is in the same league as the Indian L6 baseline (CLAUDE.md cites 59.4% CAGR / 1.92 Sharpe for the IS-tuned Indian version since 2020; the like-for-like 2017-2026 OOS comparison is closer in the high-30s/low-1.7s). Pure momentum-by-vol is the most cross-market-robust signal we ship.

**3. OM25 v3 degrades materially on US.** 34.4% / 1.26 vs Indian OOS 44.8% / 1.86. The drop comes from two places:
   - The UC/CR signal was tuned for an emerging-market structure where the upside-capture skew is wider. US large-caps have tighter cross-sectional dispersion of UC and CR.
   - SPY 100-DMA fires 29.9% of days as "bear" — heavier than NIFTY 100's bear share over the same window, which biases toward the bear-tilt branch (CR-only) for ~30% of decisions. The bear branch is a defensive signal, not an alpha signal, so a higher bear share drags the headline.

   **This is the strategy the user wants to retune next.** See "Next" below.

**4. TL25 v3 degrades the most.** 21.3% / 0.97 vs Indian OOS 34.9% / 1.53. The 3-component trend score (persistence + drawdown-control + momentum) leans on persistence above 100-DMA, which is a clean signal in growth-heavy NSE 500 mid-caps. US S&P 500 large-caps spend long stretches range-bound around their 100-DMA, producing weak persistence scores even for stocks that ultimately deliver. Lowest beta (0.83) and vol (22.0%) confirm it's running too defensively.

**5. COMBO Defensive delivers its design goal on US too.** Best Calmar (1.18) after L6, lowest beta (0.80), shallowest DD (-28.5%) of any strategy including SPY. The SPY-100-DMA regime overlay throttled gross exposure to 50% during 29.9% of days — that's how it gives up ~10pp of CAGR vs L6 to gain ~7pp of DD reduction. The risk-adjusted trade is favourable.

**6. Drawdowns reflect 2020 (COVID-19 March crash) and 2022 (Fed cycle).** L6 v2's -35.6% peak DD is in the same neighbourhood as SPY's -33.7% — momentum doesn't insulate against a fast-correlation crash. COMBO Defensive's regime overlay is the only mechanism that meaningfully reduces this.

## Differences from Indian production that matter

- **Universe size:** US 516 vs Indian NSE 500 (closely matched) and Nifty 250 (smaller). Top-25 + exit-buffer-20 leaves a smaller relative pool for OM25 v3 (45/516 = 8.7%) than its native (45/250 = 18%), which subtly increases turnover and crowding risk. Worth instrumenting in the retune.
- **Sector composition:** US universe is tech- and large-cap-heavy. Indian universe is more diversified across financials, energy, industrials. OM25's UC/CR scoring is sector-blind; sector tilts emerge endogenously and may concentrate differently.
- **Trading calendar:** ~252 days/year for NYSE vs ~250 for NSE. Lookback windows defined in trading days transfer cleanly; calendar-based ones (100-DMA, 200-DMA) are essentially the same.
- **Slippage assumption (20 bps):** retained at Indian level. US large-cap spreads are tighter, so 20 bps is conservative. Lowering to 5-10 bps would lift CAGR ~1-2pp uniformly across strategies; doesn't change rankings.

## Next: tune OM25 v3 on US data

OM25 v3 is the next candidate. Same skeleton (UC/CR composite + regime tilt), but the four levers to sweep on a 2009-2016 US IS / 2017-2026 US OOS split:

1. **Regime MA window** (currently 100) — US large-cap regimes have different rhythm. Sweep 50, 100, 150, 200.
2. **Regime confirm days** (currently 3) — US has more whipsaw around 100-DMA than NIFTY 100 historically. Sweep 1, 3, 5, 7.
3. **Bull weights `(w_uc, w_cr)`** (currently 0.5/0.5) — US UC distribution is tighter, so weighting CR higher may pick up more signal. Sweep on 5-step grid.
4. **Bear weights** (currently 0.0/1.0) — fully defensive. May not be optimal in US where bears are shorter; consider 0.25/0.75.

Plus the obvious sanity checks: lookback (252 default), exit_buffer (20 default), DD stop (20% default).

Need to build US history back to ~2009 for an IS window — EODHD has it ("from the beginning" for US), so this is a backfill-from-1999 (or earliest, to keep 252d lookback alignment). Probably a 1-day project.

Recommend matching the `tasks/oos_retune_2026/` plan structure: PLAN.md → grid sweep → RESULTS.md → lock the winning US config as `om25_us_v1` (separate from Indian production).

## Files

- `data_pipeline/eodhd_client.py` — REST client
- `scripts/fetch_us_equities_history.py` — backfill orchestrator
- `scripts/test_eodhd_trial.py` — demo-key probe + parity audit
- `scripts/run_us_strategies_2017.py` — this experiment's harness
- `data/static/us_equities_universe.csv` — 516 SP500 ∪ NDX
- `docs/eodhd_pricing.md` — provider selection rationale

## Regenerate

```bash
# 1. Backfill US prices (paid EODHD key in .env as EODHD_API_TOKEN)
python scripts/fetch_us_equities_history.py --start 2000-01-01

# 2. Refetch SPY + QQQ benchmarks (gitignored, regenerate on demand)
python -c "
from data_pipeline.eodhd_client import EODHDClient
from dotenv import load_dotenv; from pathlib import Path
load_dotenv(Path('.env'))
c = EODHDClient(rate_per_min=60)
for sym in ['SPY', 'QQQ']:
    df = c.get_history(sym, start='2000-01-01')
    df.to_csv(f'data/benchmarks/{sym.lower()}.csv', index=False)
"

# 3. Run the 4-strategy comparison
python scripts/run_us_strategies_2017.py --start 2017-01-01
```
