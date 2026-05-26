# Nifty Trader — long/short directional strategy from market breadth

## Why

Every existing production portfolio (OM25, TL25, L6, COMBO) is **long-only
stock-picking** on the NSE 500 / Nifty 250. Their return source is
cross-sectional stock selection. They have nothing to say about *market
direction* — they just hold the top-N momentum names and ride.

This initiative explores a **complementary return source**: directional
positioning on the Nifty 50 driven by market breadth signals. The bet is
that *aggregate participation* (how many stocks are advancing, % above
their moving averages, sector dispersion, vol regime) provides predictive
information about the index that single-stock momentum can't capture.

If it works, the strategy provides:
- **Diversification** — uncorrelated returns to the long-only book
- **Downside protection** — can profit from (or sidestep) major drawdowns
- **Capital efficiency** — futures allow notional exposure with margin only,
  freeing capital for the existing long book

## Mental model

Breadth leads price. When the index is making new highs but only a handful of
stocks are participating, the rally is fragile. When the index is grinding
lower but the proportion of stocks above their 50-DMA stops falling,
something has shifted. The signals are *aggregate behavior* — robust to
single-stock noise — and theoretically more stable than price alone.

We've already proven a piece of this in the breadth_atlas research: the
NIFTY 100 close-vs-100DMA + 3-day-confirm regime gate works as an allocation
overlay (COMBO Defensive). We're extending the idea from *allocation* to
*direction*.

## Outcome

A reproducible HTML report demonstrating either:
- (a) **A validated alpha-generating strategy** — meets the acceptance criteria
  below; can be deployed (or at least papertraded) as a 5th portfolio; OR
- (b) **A defensible "doesn't work" finding** — with evidence for *why* (e.g.,
  signals decay, costs eat the alpha, no robustness across sub-windows).

Both outcomes are valuable. (a) buys us a diversifier. (b) buys us a closed
research line so we stop wondering.

## Spec — initial

### Instrument
- **Backtest proxy:** NIFTY 50 index close prices (`indices_data_full/NIFTY_50.csv`,
  2010-01-04 → 2026-05-12, 16.4 years).
- **Cost model:** apply Nifty-futures-equivalent costs to all trades on the
  index proxy. See "Cost model" below.
- **Phase 2 (if alpha validates):** import NIFTY F1 (front-month futures)
  history, re-run with real futures prices and roll costs.

### Position structure — REVISED post Phase 1 EDA

**Pivot: long-bias stress-buyer with filtered shorts.**

Original plan: symmetric long/short (±100%). Phase 1 EDA showed pure
breadth signals don't generate stable short-side alpha — sign instability
between IS (2010-18) and OOS (2019-26) is severe. The robust alpha is
mean-reversion off stress signals (VIX, 52w lows, cumulative A/D).

New design:
- **Long signal:** primary driver = VIX high (z-score > threshold) OR
  cumulative_ad sharply declining (panic). Position sized by signal
  strength.
- **Short signal:** requires MULTIPLE bearish signals to align —
  e.g., VIX rising + sector breadth deteriorating + cumulative A/D
  rolling over. Conservative because the data says short alpha is rare;
  we only take shorts with high specificity.
- **Default state:** cash (no position). The strategy is "off" most of
  the time, "on" during identifiable stress or overheating.
- **Position range:** continuous in [-50%, +100%]. Asymmetric ceiling
  reflects Indian market's structural long-drift.

### Capital scale — LOCKED
**₹25L starting capital.** Above the ~₹6L single-lot threshold for Nifty
futures, allows clean lot sizing in Phase 6. The index-proxy phase (Phases
2-5) uses fractional notional, so this only matters for the futures-data
phase. ₹10L would also work; ₹25L is more realistic for someone actually
considering deploying this.

### IS/OOS split — LOCKED
**IS:** 2010-01-04 → 2018-12-31 (9 years — post-GFC recovery, 2011 taper,
2013 tantrum, 2014 election rally, 2016 demonetisation, 2017 melt-up,
2018 NBFC crisis).
**OOS:** 2019-01-01 → 2026-05-12 (7.4 years — pre-COVID, COVID crash + rally,
2022 rate-shock bear, 2023 mid-cap rally, 2024-25 rate-cycle, recent
correction). Diverse regimes in both windows.

### Cost model — Nifty futures equivalent

Round-trip cost on Nifty futures (current NSE rates):

| Component | Side | Rate | Notes |
|---|---|---|---|
| STT (futures) | Sell | 0.0125% | New rate post Oct 2024 |
| Stamp duty | Buy | 0.002% | Maharashtra rate |
| Exchange transaction | Both | 0.0019% | NSE F&O |
| SEBI charge | Both | ₹10 / cr | Trivial at our scale |
| Brokerage | Both | ₹20 / order | Discount-broker flat |
| GST (on brokerage + exchange) | Both | 18% | Applied to charges only |
| Slippage (1-2 ticks) | Both | ~0.005% | Nifty futures liquid |

**Round-trip ≈ 0.05% of notional** for the explicit costs + roll spread.

**Monthly roll cost** (next-month minus front-month spread): typically
0.05-0.15% per roll, depending on cash-futures basis. **Annualised: 0.6-1.8%**
— this is the dominant cost and must be modelled accurately.

### Backtest engine
Purpose-built (single-instrument directional, not portfolio FIFO). Tracks:
- Position state at each rebalance
- Notional exposure × index return = period P&L
- Per-trade explicit costs (deducted from P&L)
- Roll cost on monthly rolls (deducted)
- Equity curve in ₹ terms

### Signal universe

**Tier 1 — Standard breadth (well-known, baseline):**
1. NSE 500 % above 50-DMA / 100-DMA / 200-DMA
2. Daily advance/decline ratio + cumulative A/D line
3. McClellan Oscillator (EMA(advancers−decliners))
4. Net new 52-week highs vs lows
5. NIFTY 100 close vs N-DMA (our existing regime gate)

**Tier 2 — Novel angles (the "be innovative" mandate):**
6. **Breadth divergence:** index momentum minus breadth momentum — fades narrow
   rallies, buys broad sell-offs
7. **Breadth thrust** (Whaley-style): %-advancers persistently >80% over N days
8. **Sector breadth term structure:** % of sector indices above N-DMA, plus
   short-term vs long-term sector-breadth divergence (rotation signal)
9. **Cross-sectional dispersion:** stdev of daily NSE 500 returns — high =
   stress/opportunity, low = trend/complacency. Combined with breadth level
   yields a richer 2D classifier
10. **Vol regime conditioning:** India VIX z-score modulates signal magnitude
    — same breadth reading has different forward expectation at VIX=15 vs VIX=30
11. **Cross-asset confirmation:** USDINR rate of change, gold (MCXGOLDEX),
    BharatBond yield-proxy
12. **Vol-of-vol:** VIX rate of change — vol expansion vs contraction signals
13. **Asymmetric thresholds:** require stronger breadth for short than for
    long (long-term equity drift means short alpha is rarer)
14. **Signal-strength position sizing:** scale exposure by breadth conviction
    (continuous), not just on/off

### Out of scope (deferred for v1)

- Intraday signals / data
- Sector-level long/short pairs trades
- Options strategies (puts/calls)
- Per-stock breadth weighting (we treat NSE 500 stocks equally)
- Auto-tuning / ML model fitting on the signals
- Live deployment infrastructure

### Acceptance criteria (proposed — confirm in questionnaire)

To call this "alpha-generating":
1. **Sharpe ≥ 0.8** over the full 16y; **Sharpe ≥ 0.6** in each 4-year sub-window
2. **Max drawdown ≤ 25%** (compares against Nifty B&H ~35%)
3. **CAGR ≥ Nifty B&H + 5 pp** post-cost (Nifty B&H is ~11.5% pre-tax over T10y)
4. **Correlation with each of OM25/TL25/L6/COMBO < 0.40** — otherwise it's
   just a leveraged long-beta proxy, not a true diversifier
5. **Parameter robustness:** ≥80% of a reasonable parameter grid passes (1) + (3)

If we miss (1)+(3) but pass (4)+(5), it's still a defensible "doesn't beat
buy-and-hold even with breadth alpha, but uncorrelated" finding — close as
research, save trees.

### Critical files

| File | Role |
|---|---|
| `breadth_signals.py` | Build all breadth metrics from NSE 500 panel |
| `macro_signals.py` | VIX, sector indices, cross-asset transforms |
| `cost_model.py` | Futures-equivalent cost simulation (STT, stamp, GST, brokerage, slippage, roll) |
| `backtest.py` | Single-instrument directional engine (position state + costs) |
| `signal_lab.py` | EDA, signal selection, ablation, robustness grids |
| `build_report.py` | HTML report orchestrator |
| `report.html` | Output |

## Risks & adversarial considerations (pre-mortem)

1. **Survivorship in NSE 500 panel** — same risk as other strategies. May
   inflate breadth signals. Acknowledged; not fixable in v1.
2. **Look-ahead in breadth** — % above DMA computed at end-of-day is fine for
   next-day signals; intraday breadth would be look-ahead.
3. **Regime stationarity** — breadth-vs-price relationships may have shifted
   pre/post-COVID. Sub-window stability test is the guardrail.
4. **The "everything correlates in a crash" problem** — short alpha may
   evaporate during fast crashes (positions can't be unwound fast enough; gap
   risk). Backtest assumes continuous execution, which is optimistic for the
   short side.
5. **Roll cost in steep contango** — historical Nifty futures roll cost has
   varied; if we go from index-proxy to real futures and the strategy's
   high-frequency trading style accumulates rolls, costs could compound.
6. **Cherry-picking signals on full sample** — must use IS/OOS split with
   honest holdout: tune on 2010-2018, validate on 2019-2026.
