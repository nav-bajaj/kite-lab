# Production Portfolios

Detailed specifications for the 4 production portfolios and the 3
legacy alt-universe variants. This is the long-form reference that
used to live inline in `CLAUDE.md`.

For a one-line summary of each, see `CLAUDE.md`. For client-facing
display names, see `kite-dashboard/src/lib/universes.ts`.

---

## The 4 production portfolios (built daily)

All four run from `scripts/update_all_portfolios.py`, which is invoked
by the daily pipeline (`scripts/run_daily_pipeline.py`) and exposed to
the dashboard via the `update_portfolios` job command.

### OM25 v3 — "Quality Momentum"

**Internal ID:** `om25_v3` · **Universe:** Nifty 250 (250 stocks) · **Cadence:** bi-weekly entry + weekly exit checks

**Score:**
- Bull regime: `0.5 × pct_rank(upside_capture) + 0.5 × pct_rank(capture_ratio)`
- Bear regime: `pct_rank(capture_ratio)` only — defensive tilt
- Regime signal: NIFTY 100 close vs 100-day MA, 3-day confirmation hysteresis

**Risk controls:**
- Lookback 252 days, ≥220 obs required
- Top-N 25 stocks, exit-buffer 20 (drop below rank 45)
- Drawdown stop: 20% from running peak (weekly check)
- Sizing: equal 1/N, max 7.5%, drift after entry
- Slippage: 0.2% (20 bps, OHLC/4 next-day)

**OOS performance (2017–2026, 9.3y):** CAGR 44.78% · Sharpe 1.86 · MaxDD −36.6% · sub-window pass: 1.57 / 2.10 / 1.80

**Spec source:** `scripts/om25_v3.py` · **Runner:** `scripts/run_om25_v3_portfolio.py` · **Evidence trail:** on the archive branch under `tasks/oos_retune_2026/RESULTS.md`

### TL25 v3 — "Trend Leaders"

**Internal ID:** `tl25_v3` · **Universe:** NSE 500 (499 stocks) · **Cadence:** bi-weekly entry + weekly rank-exit + weekly DD-stop

**Score (equal-weighted three-component):**
- 0.40 × Persistence (% of 252d where Close > 100 DMA)
- 0.20 × Drawdown-Control (`(Close / 126d rolling high)²`)
- 0.40 × Momentum (63-day return, percentile-ranked among eligible)

**Eligibility (pre-filter):** Close > 200 DMA AND 50 DMA > 200 DMA AND 200 DMA rising over 20d

**Risk controls:**
- Top-N 25, exit-buffer 20
- Drawdown stop: 20% from peak (no 200-DMA exit)
- Sizing: equal 1/N, max 7.5%
- Slippage: 0.2%

**Regime tilt:** None (single config; distinguishes from OM25 v3)

**OOS performance (2017–2026, 9.3y):** CAGR 34.86% · Sharpe 1.53 (rf=0) · MaxDD −39.00% · sub-window pass: 1.18 / 2.16 / 1.18

**Spec source:** `scripts/tl25_v3.py` · **Runner:** `scripts/run_tl25_v3_portfolio.py` · **Evidence trail:** archive branch `tasks/oos_retune_2026/RESULTS.md` (TL25 v3 section)

### L6 v2 — "Core Momentum"

**Internal ID:** `l6_v2` · **Universe:** NSE 500 (499 stocks) · **Cadence:** weekly Thursday signal → Friday OHLC/4 execution

**Score:** `momentum_6m / max(realized_vol, 0.05)^1.0`, cross-sectional z-score

**Risk controls:**
- Top-N 24, equal-weight 1/24, max 7.5%
- Min hold 8 days, exit buffer 0 (immediate exit when out of top-24)
- Slippage 0.2%, skip days 0
- **No** drawdown stop, **no** regime overlay (those live in COMBO Defensive)

**Performance (2020-07-10 to 2026-02-02, IS-only tune):** CAGR 59.4% · Sharpe 1.92 · MaxDD −30.0% · turnover 123% · hit rate 49.3%

**Engine:** `scripts/_momentum_engine.py` atop `scripts/_clean_engine.run_strategy()`. Calibrated within 0.4pp CAGR / 0.01 Sharpe of the legacy L6 (verified during MM-tuning calibration).

**Spec source:** uses `_momentum_engine.py` defaults · **Runner:** `scripts/run_l6_v2_portfolio.py` · **Evidence trail:** archive branch `tasks/MM-tuning/PRODUCTIONIZATION.md`

### COMBO Defensive — "Defensive Blend"

**Internal ID:** `combo_defensive` · **Universe:** NSE 500 · **Cadence:** bi-weekly Friday signal → Monday OHLC/4 execution

**Composite:** 50% L6 v2 ranks + 50% OM25 v3 ranks, priority dedup

**Regime overlay:** NIFTY 100 close vs 100-DMA, 3-day confirmation. **50% allocation cut in bear regime.**

**Risk controls:** inherits Top-N / sizing / slippage from L6 and OM25 component specs.

**Purpose:** drawdown-reduction sibling of L6 v2. The 50% bear-regime cut sacrifices some upside for materially lower max DD.

**Spec source:** `scripts/combo_defensive.py` (LOCKED config) · **Runner:** `scripts/run_combo_defensive_portfolio.py` · **Evidence trail:** archive branch `tasks/MM-tuning/DD_REDUCTION_RESEARCH.md`

---

## Legacy L6 — alt-universe variants (admin-only)

Three additional portfolios run the legacy L6 momentum algorithm via
`scripts/run_final_momentum_portfolio.py --universe <name>`. These are
admin-only in the client portal (visible in the dashboard's universe
selector only for users with `publicMetadata.role = "admin"`).

| Internal ID | Display name | Universe | Notes |
|---|---|---|---|
| `nse500` | Broad Momentum | NSE 500 (499) | Legacy L6 on the same universe as L6 v2. Performance matches L6 v2 ±0.4pp CAGR. |
| `nifty250` | Mid-Cap Momentum | Nifty 250 (250) | CAGR ~46% / DD ~−24% — between NSE 500 and Nifty 100. |
| `nifty100` | Large-Cap Momentum | Nifty 100 (100) | CAGR 44.86% / DD −19.11% (2020-07 to 2026-01). Lowest DD, lowest CAGR. |

These predate the v3 family and are kept for backtest comparison and
the legacy Thursday/Friday rebalance helper. They're not exposed to
client-role users.

---

## Performance benchmarks

### Momentum L6-1W family (IS-only tuning, 2020–2026)

| Portfolio | CAGR | MaxDD | Sharpe | Turnover | Use case |
|---|---|---|---|---|---|
| NSE 500 L6-1W (min-hold 8d) | 59.4% | −30.0% | 1.92 | 123% | Growth investors |
| Nifty 100 L6-1W | 44.86% | −19.11% | 1.69 | 58% | Risk-averse |

### OOS-validated v3 strategies (tuned 2009–2016, validated 2017–2026)

| Portfolio | OOS CAGR | OOS MaxDD | OOS Sharpe | Signal type |
|---|---|---|---|---|
| OM25 v3 (Nifty 250) | 44.78% | −36.6% | 1.86 (rf=0) | Capture asymmetry + regime tilt |
| TL25 v3 (NSE 500) | 34.86% | −39.0% | 1.53 (rf=0) | 3-component trend quality |

**Read:** Momentum L6-1W is IS-tuned and shows the highest raw CAGR.
OM25 v3 + TL25 v3 are OOS-validated against tuning on a held-out 2009–2016
training window — pick these for "doesn't break on regime shifts"
robustness, pick L6 for highest recent CAGR.

---

## Parameter insights (what works / doesn't)

### Proven
- Lookback: 6 months (L6) optimal for NSE momentum
- Rebalance: weekly captures momentum best (for L6 family)
- Vol floor: 0.05 (clips all stocks → pure momentum ranking) — see `docs/vol_floor_optimization.md`
- Skip days: 0 (no skip window needed)
- Top-N: 24 stocks (diversification vs concentration balance)
- Universe: full NSE 500 captures mid-cap alpha
- Min hold days: 8 (eliminates 0–7d churn, +3.2% CAGR, +0.05 Sharpe)

### Tested and rejected
- Longer lookbacks (L9 / L12): underperforms L6
- Lower frequency (bi-weekly L6): lower returns, higher DD
- Restricted universe (Nifty 100): sacrifices ~13% CAGR
- Volatility targeting (dynamic position sizing): disrupts momentum strategy — see `docs/volatility_targeting_experiments.md`
- Volume-weighted scoring: dollar-volume + OBV blends both trail pure momentum
- PnL-hold exit filter: freezes portfolio, kills rotation
- Consecutive-weeks entry filter: delays re-entry after corrections, explodes drawdowns

Full negative-result log: `docs/failed_experiments.md`.
