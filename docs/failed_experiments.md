# Backtest Experiments Log

Experiments tested against the production baseline (NSE 500, L6, weekly rebalance, top-24, vol_floor=0.05).

**Baseline reference (2020-2026):** 56.2% CAGR | -27.7% max DD | 1.87 Sharpe | 2,492 trades | 47.6% hit rate | 39d avg hold

---

## 1. Volume-Weighted Scoring

**Branch:** `momentum-volume`

**Hypothesis:** Blending a volume signal into the momentum score would improve stock selection by favouring liquid, actively-traded names.

### 1a. Dollar-Volume Rank Blend

**Method:** `final_score = (1 - alpha) * momentum_z + alpha * avg_dollar_volume_z`

Rolling average dollar volume (close * volume) over a window, cross-sectionally z-scored, blended with momentum z-scores. Single parameter: `--volume-alpha`.

| Config | CAGR | Max DD | Sharpe |
|---|---|---|---|
| baseline (alpha=0) | 58.2% | -27.7% | 1.92 |
| dvol alpha=0.2 w63 | 44.1% | -30.0% | 1.57 |

**Result:** -14% CAGR, worse on all metrics. Dollar-volume rank favours large-caps, diluting the mid-cap momentum alpha that drives the NSE 500 strategy.

### 1b. OBV Momentum Blend

**Method:** Same blend formula but using On-Balance Volume momentum as the volume signal. OBV accumulates signed volume (+ on up days, - on down days). The signal is net signed volume over a rolling window, normalized by average volume, then z-scored.

| Config | CAGR | Max DD | Sharpe |
|---|---|---|---|
| baseline (alpha=0) | 58.2% | -27.7% | 1.92 |
| OBV alpha=0.05 w63 | 55.3% | -28.6% | 1.85 |
| OBV alpha=0.10 w63 | 55.4% | -29.3% | 1.84 |
| OBV alpha=0.20 w63 | 54.3% | -30.7% | 1.81 |
| OBV alpha=0.20 w126 | 52.9% | -31.2% | 1.78 |

**Result:** OBV is much better than dollar-volume but still trails pure momentum at every alpha tested. Monotonically worse with more volume weight. The momentum signal alone is sufficient; volume adds noise.

**Conclusion:** Volume does not improve this momentum strategy. Abandoned.

---

## 2. PnL-Hold Exit Filter

**Branch:** `fix-pnl-hold-logic`

**Hypothesis:** Holding positions that are still profitable (or only slightly negative) when they drop out of the top-24 ranking would reduce the short-hold churn that produces negative expected value.

**Method:** On rebalance day, if a stock leaves the top-24 but has unrealized PnL above a threshold, keep it. New stocks do NOT enter to replace held positions (total holdings capped at 24).

| Config | CAGR | Max DD | Sharpe | Trades | Avg Hold |
|---|---|---|---|---|---|
| baseline | 56.2% | -27.7% | 1.87 | 2,492 | 39d |
| pnl-hold >= 0% | 39.6% | -31.6% | 1.62 | 90 | 77d |
| pnl-hold >= -3% | 34.9% | -28.4% | 1.53 | 68 | 243d |

**Result:** The filter is too aggressive - most positions are profitable at any given time, so almost nothing exits. The portfolio freezes and can't rotate into new momentum leaders. Hit rate is 0% by construction (only exits are losses). Fundamentally conflicts with momentum strategy logic.

**Bug fixed during testing:** The original implementation allowed holdings to exceed top_n when pnl-held stocks weren't exited but new stocks were still added. Fixed by capping entrants to `max(0, top_n - len(holdings))`.

**Conclusion:** PnL-based exit filtering kills momentum rotation. Abandoned.

---

## 3. Consecutive Weeks Entry Filter

**Branch:** `fix-pnl-hold-logic`

**Hypothesis:** Requiring a stock to appear in the top-24 for N consecutive weeks before buying would filter out "flash-in-the-pan" entries that briefly spike into the ranking and then fall out, causing short-hold losses.

**Motivation:** Trades held <=30 days have -1.59% avg PnL (38% win rate, -1,320% total PnL), while trades held >30 days have +25.2% avg PnL (70% win rate, +10,234% total PnL).

**Method:** Track consecutive appearances in the top-N. Only buy a stock once its streak reaches the minimum threshold.

| Config | CAGR | Max DD | Sharpe | Trades | Avg Hold |
|---|---|---|---|---|---|
| baseline (1w) | 56.2% | -27.7% | 1.87 | 2,492 | 39d |
| consec 2w | 53.7% | -44.4% | 1.61 | 1,619 | 49d |
| consec 3w | 54.6% | -47.2% | 1.59 | 1,207 | 56d |
| consec 4w | 69.4% | -56.0% | 1.73 | 981 | 61d |

**Result:** Holding periods increase as intended, trades decrease, but drawdowns explode (-44% to -56% vs -28%). After market corrections, the filter delays re-entry into new momentum leaders (they haven't built up N weeks of streak yet), leaving the portfolio stuck with stale holdings during recovery. The 4w result (69% CAGR) is an artifact of extreme path dependency given the -56% drawdown.

**Conclusion:** Delays genuine momentum rotations more than it filters noise. Abandoned.

---

## 4. Entry Rank Threshold

**Branch:** `fix-pnl-hold-logic`

**Hypothesis:** Requiring stocks to be in the top-K (e.g., top-12) to enter but allowing them to stay until they leave the top-24 would filter marginal entries (rank 20-24) that are most likely to quickly fall out.

**Method:** `--entry-rank K`: only buy stocks ranked <= K; existing holdings stay until they exit the top-N band via normal rank-based exit.

| Config | CAGR | Max DD | Sharpe | Trades | Avg Hold |
|---|---|---|---|---|---|
| baseline (enter 24) | 56.2% | -27.7% | 1.87 | 2,492 | 39d |
| enter top-16 | 54.1% | -31.1% | 1.68 | 1,313 | 58d |
| enter top-12 | 40.6% | -44.1% | 1.29 | 940 | 70d |
| enter top-8 | 86.2% | -52.9% | 1.64 | 570 | 88d |

**Result:** Tighter entry thresholds increase holding periods and reduce trades, but worsen drawdowns significantly because the portfolio can't fill all 24 slots quickly. The top-8 result (86% CAGR) is unreliable — extreme concentration with -53% drawdown and 33% hit rate indicates path dependency, not a real edge. Short-hold drag improves (top-12: -712% vs -1,320%) but total gains also drop because good entries are blocked too.

**Conclusion:** Prevents good entries as much as bad ones. Abandoned.

---

## Key Insight from Failed Experiments

All four approaches above attempt to reduce the ~1,320% of negative PnL from short-hold trades (<=30 days). However, every mechanism that slows entry or prevents exit reduces the strategy's ability to quickly rotate into new momentum leaders — which is the source of its returns.

The short-hold losses are not a bug; they are the cost of maintaining high sensitivity to momentum shifts. The 47.6% hit rate with strong positive skew (avg winner >> avg loser) is the characteristic signature of a trend-following/momentum strategy.

---

## 5. Minimum Holding Period (SUCCESS)

**Branch:** `fix-pnl-hold-logic`

**Hypothesis:** The 0-7 day holding bucket (389 trades, -2.7% avg PnL, 28% win rate, -1,061% total PnL) consists of stocks that enter the portfolio and are immediately exited on the very next weekly rebalance. Forcing a minimum hold of 8 days (one full rebalance cycle) would eliminate this bucket without disrupting broader momentum rotation.

**Method:** `--min-hold-days N`: if a stock has been held for fewer than N days, it cannot be exited regardless of rank. Entries are unrestricted — all top-24 stocks enter normally. This is the lightest possible intervention: it doesn't filter entries, doesn't change position sizing, and doesn't prevent exits after the minimum period.

| Config | CAGR | Max DD | Sharpe | Trades | Hit Rate | Avg Hold |
|---|---|---|---|---|---|---|
| baseline | 56.2% | -27.7% | 1.87 | 2,492 | 47.6% | 39d |
| **min-hold 8d** | **59.4%** | -30.0% | **1.92** | 2,352 | **49.3%** | 43d |
| min-hold 15d | 50.9% | -29.1% | 1.71 | 2,196 | 50.8% | 49d |

**Holding period breakdown (min-hold 8d):**

| Period | Count | Avg PnL | Win Rate | Total PnL |
|---|---|---|---|---|
| 0-7d | 0 | — | — | — |
| 8-14d | 523 | -2.3% | 37% | -1,205% |
| 15-21d | 129 | -1.3% | 45% | -164% |
| 22-30d | 87 | +2.2% | 53% | +192% |
| 31-60d | 183 | +4.8% | 63% | +882% |
| 61-90d | 74 | +8.2% | 55% | +606% |
| 91-180d | 124 | +24.0% | 78% | +2,973% |
| 181-365d | 43 | +132.0% | 100% | +5,676% |

**Why it works:**
- Eliminates the worst bucket entirely (0-7d: 389 trades, -1,061% PnL → 0 trades)
- Only 140 fewer total trades — momentum rotation stays intact
- The 8-14d bucket absorbs some of the former 0-7d trades but at better PnL (-2.3% vs -2.7%)
- Long-hold gains are preserved (+10,415% vs +10,234% baseline for >30d)

**Why 8 days and not more:**
- 15 days goes too far: CAGR drops to 50.9%, Sharpe to 1.71
- 8 days is the natural minimum — it ensures a stock survives at least one full rebalance cycle before it can be exited, while still allowing fast rotation on the second rebalance

**Result:** +3.2% CAGR, +0.05 Sharpe, +1.7% hit rate improvement. Drawdown slightly worse (-30.0% vs -27.7%) but risk-adjusted return (Sharpe) is the best of all configurations tested.

**Conclusion:** Adopted. Use `--min-hold-days 8` in production backtests.

---

## 6. Bottom-up breadth throttle (RAAM transplant, `tasks/raam_transplant`)

**Hypothesis:** scale L6's exposure by market-wide positive-momentum breadth (a bottom-up version of RAAM's per-slot cash fallback) — deploy less when fewer names are trending.

**Method:** diagnostic first — bucket market-wide breadth (share of the eligible universe with positive 126d momentum) against forward 20/40/60d return and drawdown, 2017-2026.

**Result — REFUTED before backtest.** The breadth→forward-outcome relation is **U-shaped, not monotone**: low breadth (washed-out market) has the *best* forward returns, mid-breadth is the danger zone (worst returns + deepest drawdowns), high breadth is healthiest. A linear "cut exposure when breadth is low" throttle would cut risk exactly at the bullish lows. The only viable form is a non-linear mid-breadth regime flag, which duplicates the already-rejected `tasks/breadth_atlas/combo_3state`.

**Conclusion:** Do not build a linear breadth throttle for Indian stock momentum. Low breadth is a contrarian-bullish signal here, not a risk-off one.

## 7. Trend as an additive score — ATR/Donchian breakout state (RAAM transplant)

**Hypothesis:** add the paper's trend/breakout state to L6's score (`final = L6_z + w·trend`) to de-rank high-momentum names that are rolling over.

**Method:** 42-day Donchian breakout state (+1 in uptrend since last 42d-high, −1 since last 42d-low), grid `w`, judged OOS.

| w | OOS mean ΔCAGR | worst window |
|---|---|---|
| 0.5 | −1.79pp | OOS-B −5.0 |
| 1.0 | −3.07pp | OOS-B −9.2 |
| 2.0 | −3.41pp | OOS-B −12.3 |

**Result — FAILS at every weight**, worst in the strong-trend OOS-B (2020-22). A "must be making fresh highs" state ejects *consolidating* winners, which is brutal in a bull market. (A gentler 200-DMA-distance trend tilt at w≈0.25 was modestly positive — see `tasks/raam_transplant/TASKS.md` E-T — but overlaps momentum and was not productized.)

**Conclusion:** Do not use a breakout-state trend term on a stock momentum book. If a trend contributor is ever wanted, use a smooth 200-DMA-distance measure at a gentle weight, not an ATR/Donchian breakout state.

## 8. EWMA/GARCH volatility over realized vol (RAAM transplant, low-vol sleeve)

**Hypothesis:** the paper's RiskMetrics EWMA(λ=0.94) volatility estimator improves a low-vol ranking over plain 252d realized std.

**Result — EWMA UNDERPERFORMS.** On the low-vol sleeve, realized-252d vol beat EWMA(0.94) on every trend-gate variant (realized+trend: CAGR 16.5% / DD −26.4% / Sharpe 0.91 vs EWMA 15.4% / −31.6% / 0.82), and at lower turnover.

**Conclusion:** Use plain realized volatility, not EWMA/GARCH, for vol-ranking in this universe. (Consistent with the broader raam_transplant finding: the paper's fancier instruments lose to simpler ones here.)

## 9. RC25 full ranked composite as a standalone portfolio (RAAM transplant)

**Hypothesis:** the paper's full weighted-rank composite (M momentum + C per-name residual crowding + T 200-DMA distance, top-25, per-slot cash) forms a differentiated 5th momentum portfolio.

**Result — REFUTED.** IS-tuned weights 0.4/0.3/0.3. Overall ≈ L6 (FULL CAGR 37.0 vs 37.9, Sharpe 1.41 vs 1.40) but fails the differentiation bar decisively: **daily corr to L6 0.97** (bar <0.7), **holdings overlap 66%** (bar <25%). Helps choppy/recent windows but gives up 11pp in the strong OOS-B bull (C+T pull off the momentum leaders when they run hardest).

**Conclusion:** No standalone 5th *momentum* portfolio. The crowding/trend value belongs as tweaks to L6 (E1), not a new book. The only genuinely different book is the low-vol sleeve (not a momentum strategy).

## 10. Crowding index as an exposure-timing lever (RAAM transplant)

**Hypothesis:** throttle a momentum strategy's gross exposure down when the Momentum Crowding Index is in an extreme percentile (crowding weakly predicts near-term drawdown).

**Result — FAILS on both L6 and OM25.** Every threshold/floor lost OOS CAGR (L6 −5 to −14pp; OM25 −4.8 to −14.7pp), worst in the OOS-B bull. High crowding coincides with strong momentum rallies, so cutting exposure sits out the continuation — confirmed by the conditional distribution (top crowding quintile had the *highest* forward returns). On OM25 the lever is additionally redundant with its built-in 20% trailing DD stop (OOS-B drawdown unchanged).

**Conclusion:** Crowding is a *selection* signal, not an *exposure/timing* signal, for any momentum-family strategy. Do not build a crowding exposure throttle.

## 11. Crowding selection nudge on Quality Momentum (OM25) — universe study

**Hypothesis:** the E1 de-crowding selection nudge (which works on L6) should help OM25, and help *more* on the broader, more-crowded NSE 500 than on Nifty 250.

**Result — mixed, and the hypothesis about *why* is wrong.** On Nifty 250 the nudge passes the E1 gate but is tiny (λ*=0.5, +0.2pp OOS mean, 96% overlap). On **NSE 500 it flips negative** (OOS CAGR −3.7/−1.8/−0.2pp, Calmar 0/3, gate fails). Broadening the universe made it *worse*, not better.

**Why:** the nudge's value depends on the *base score*, not the universe. L6's score is pure momentum, whose top names crowd into themes → de-crowding helps. OM25's capture-ratio score is a quality tilt that already selects structurally-diversified, downside-protected names → the penalty is redundant (Nifty 250) or fights the quality factor (NSE 500, where quality has more room to express).

**Conclusion:** Apply the crowding selection nudge to momentum-purity strategies (L6) only; do not layer it on quality-momentum (OM25).

---

*Last updated: July 2026*
*Sections 1-5 (2020-2026 window); sections 6-11 from `tasks/raam_transplant` (IS 2009-2016 / OOS 2017-2026, 20bps slippage, net of costs). Full write-up: `tasks/raam_transplant/RESULTS.md`.*
