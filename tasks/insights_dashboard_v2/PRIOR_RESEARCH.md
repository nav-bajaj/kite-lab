# Prior research inventory — breadth & indicator work we can surface

Compiled 2026-08-14 on branch `insights_dashboard_v2`. Question answered:
what breadth-related and indicator research already exists in this repo's
history that the mission-control dashboard (`DASHBOARD_DESIGN.md`) could
surface as indicators or historical studies?

Sources audited: `tasks/breadth_atlas/` (REPORT.md + combo_3state +
experiments), the BV3 / Value-Zone line (commit `2953504`, archived
`tasks/MM-tuning/VALUE_ZONE_REGIME.md` on `repo-snapshot-2026-05-20`),
`tasks/insight_engine/` (validity protocol + pattern studies + analog
retirement), `tasks/insights_v2/VALIDITY/`, `tasks/donchian_channel/`,
`tasks/stress_reversal_calls/`, `tasks/nifty_trader/`, `tasks/om25_alt/`,
`kite-api/app/insights/`, and the committed indicator panels.

Everything below is quoted from the repo's own reports; nothing is
re-derived. Where the repo is inconclusive, that is stated.

---

## 0. The governing rule (applies to every candidate)

`tasks/insight_engine/VALIDITY_PROTOCOL.md` — any surfaced forward-return
claim needs: n ≥ 100 (200 preferred), ≥ +1.0pp 20d excess vs the matched
unconditional baseline, positive direction lift, sign consistency across
5/20/60d, survivorship hygiene, and persistence across panel halves.
Three tiers: Validated (green badge) / Names-only (amber, no fwd-return
copy) / Not surfaced. **Descriptive state statements ("breadth is at the
5th percentile of 16 years") are explicitly out of scope for the
protocol** — so all the "reference band" charts below can ship without
new studies as long as copy stays descriptive. Harness for any new claim:
`tasks/insight_engine/pattern_validity_study.py`.

---

## Tier 1 — ready to surface now

### 1.1 Additional breadth-atlas metrics with empirical bands

**What:** `tasks/breadth_atlas/REPORT.md` profiles 14 NSE 500 breadth
metrics over 2010-06-24 → 2026-05-08 (3,932 trading days). The dashboard
currently plans `pct_above_200dma` (p5 22% / median 59% / p95 94%),
`net_new_highs_pct`, and `mcclellan_osc`. The atlas gives ready-made
p5/median/p95 bands for every metric, plus dwell-times, half-lives, and
concurrent-drawdown context.

**Where:** report + section CSVs in `tasks/breadth_atlas/`
(`section1_distribution_stats.csv`, `section2_dwell_times.csv`,
`section3_extremes.csv`, `section4_mean_reversion.csv`,
`section5_conditional.csv`, `section6_*.csv`). Panel:
`data/breadth/breadth_daily.csv`. Live engine:
`kite-api/app/insights/breadth.py` (`compute_breadth_panel`), API
`GET /api/insights/breadth/timeseries`.

**Reference values (Section 1, full-period):**

| Metric | p05 | median | p95 | Half-life (d) | Live engine? |
|---|---|---|---|---|---|
| pct_above_200dma | 0.222 | 0.588 | 0.937 | 130.3 | yes (surfaced) |
| pct_above_100dma | 0.169 | 0.593 | 0.895 | 68.8 | yes |
| pct_above_50dma | 0.157 | 0.578 | 0.882 | 35.7 | yes |
| pct_above_21dma | 0.148 | 0.549 | 0.851 | 13.1 | **no** |
| avg_dist_from_200dma | -0.110 | +0.051 | +0.292 | 162.7 | **no** |
| net_new_highs_pct | -0.100 | +0.024 | +0.132 | 4.3 | yes |
| pct_at_52w_high | 0.000 | 0.032 | 0.133 | 4.2 | yes (`new_52w_highs_pct`) |
| pct_at_52w_low | 0.000 | 0.006 | 0.106 | 2.8 | yes (`new_52w_lows_pct`) |
| mcclellan_osc | -0.068 | +0.001 | +0.067 | 5.6 | yes |
| mcclellan_sum | 1.541 | 2.518 | 3.332 | 267.7 | **no** |
| ad_net_pct | -0.672 | +0.004 | +0.582 | 0.37 | yes (`ad_diff_pct`) |
| ad_ratio | 0.193 | 1.008 | 3.856 | 0.28 | **no** |
| up_vol_ratio | 0.129 | 0.559 | 0.895 | 0.33 | **no** (volume reliable 2020+ only) |
| ad_line | -69.07 | -40.53 | -8.48 | 1417.8 | yes (`cumulative_ad`) — "a chart, not a signal" |

`mcclellan_osc` σ = 0.041, so the design's ±1σ/±2σ bands are ±0.041 /
±0.082; atlas: 76% of days inside ±1σ, only 4.6% outside ±2σ. The live
engine also computes `dispersion` (cross-sectional daily-return std) —
not in the atlas, so it has **no** reference bands; profile it before
drawing bands on it.

**Redundancy / which to pick (Section 6 PCA):** the 14-metric panel is a
clean two-factor structure — PC1 48.3% = slow trend-participation
(`net_new_highs_pct`, `pct_above_100/50/200dma`, `mcclellan_sum`), PC2
20.8% = daily flow (`ad_net_pct`, `ad_ratio`, `up_vol_ratio`,
`mcclellan_osc`); 6 PCs cover ~94%. Redundant pairs (|ρ| ≥ 0.85):
pct_above_200dma↔avg_dist_from_200dma **0.97**;
pct_above_50dma↔mcclellan_sum 0.90; ad_net_pct↔up_vol_ratio 0.89;
pct_above_100dma↔mcclellan_sum 0.89; pct_above_200dma↔pct_above_100dma
0.86; pct_above_100dma↔pct_above_50dma 0.86. Complementary (kept
deliberately): net_new_highs_pct vs pct_above_200dma at ρ = 0.73 — below
the cutoff, carries independent information. DASHBOARD_DESIGN's "one
headline chart per factor + selector" rule is exactly the atlas's own
recommendation.

**The one genuinely missing metric: `avg_dist_from_200dma`.** The atlas
repeatedly flags it as the statistically stronger deep-panic gauge than
the binary pct_above_200dma: its <−2σ bucket has 47 days at −27.3% mean
concurrent NIFTY 100 drawdown, vs the 0–10% pct_above_200dma bucket's 11
days at −32.8% (too rare to band reliably; 1.0% of days, avg visit ~11
days, longest 19 — COVID). combo_3state T5 additionally found it "the
most consistent breadth metric across windows." It is not computed by
the live engine — adding it to `compute_breadth_panel` is a ~5-line
change.

**Validity status:** descriptive state display — protocol does not apply
(no forward claims). Bands are the atlas's own percentiles.
**Recommendation: surface now.** Add `avg_dist_from_200dma` (and
optionally `mcclellan_sum`, `pct_above_21dma`) to the live engine; use
the table above for the metric-selector bands; keep copy descriptive.

### 1.2 Extreme-event catalog as a historical regime annotation layer

**What:** Section 3 of the atlas logs 1,962 extreme events (every day
beyond the 5th/95th percentile per metric) with entry/exit dates,
duration, and concurrent NIFTY 100 drawdown. The report confirms the
catalog "is a credible historical regime tagger": COVID = 78-day
pct_above_200dma-low (2020-03-12 → 2020-05-29), the current correction =
158-day ad_line-low (2025-12-01 → 2026-05-08), 2011 and 2023 also
visible. Concurrent-DD ranking per bucket (usable as chart-band copy):
pct_above_200dma 0–10% → −32.8% (n=11); avg_dist_from_200dma <−2σ →
−27.3% (47); pct_above_100dma 0–10% → −20.5% (73); mcclellan_sum <−2σ →
−20.3% (76); pct_above_50dma 0–10% → −20.6% (77); net_new_highs_pct
<−2σ → −16.0% (139). Known quirk to encode in copy: mcclellan_osc >+2σ
days average −13.1% concurrent DD — high oscillator readings are
panic-bounce flow, not euphoria.

**Where:** `tasks/breadth_atlas/section3_extremes.csv` (+
`section5_conditional.csv` for per-decile concurrent-DD tables).

**Validity status:** descriptive/historical; no forward claims.
**Recommendation: surface now** — as shaded "historically rare
territory" episodes on the breadth detail charts (COVID, 2011, 2018,
2020, 2025 labels), the exact "one click from how we got here" the
design asks for.

### 1.3 Conditional forward-return distributions by regime ("buy panic" base rates)

**What:** `conditional_dist.by_regime()` — Nifty forward-return
distributions bucketed by the production 4-state regime. Audited
2026-05-29 in VALIDITY_PROTOCOL.md against the 16-year panel:

| Bucket | n | 20d median | 20d % positive | Tier |
|---|---|---|---|---|
| STRESS | 778 | **+3.00%** | 72% | Validated (the platform's strongest conditional claim; +13pp direction lift) |
| STRETCHED | 177 | +1.69% (60d/120d medians +7.34%/+10.65%) | 72% | Marginal — n<200, needs small-sample caveat (already in copy) |
| TREND_BULL | 1795 | +0.88% | 60% | Validated (mild) |
| DRIFT | 1293 | +0.37% | 54% | Descriptive only — no edge vs drift; copy already tightened |

**Where:** `kite-api/app/insights/conditional_dist.py` (also
`by_stress_quintile`, `by_regime_x_stress`, `get_today_conditional`).
Currently surfaced only as one paragraph in the Daily Quant Note
(`notes/commentary.py::_conditional_paragraph`); **no dedicated API
route, no chart** — this is the biggest untapped display asset in
`app/insights/`.

**Validity status:** passed audit (per-bucket tiers above), with copy
rules already codified and spec-tested.
**Recommendation: surface now** as a "Historical base rates" module on
the regime/stress detail view: distribution strip (median, middle-half,
% positive, n) per regime, reusing the audited numbers and existing
tiered-copy rules. Note stress_reversal_calls' caveat: this is an
INDEX-level distribution statement — never convert it into stock-level
call framing (that conversion was tested and rejected, see 3.2).

### 1.4 Validated stock-list claims (badges already earned)

**What/status:** per `tasks/insight_engine/PATTERN_VALIDITY/` and
`tasks/insights_v2/VALIDITY/` (matched NSE 500 baseline, 165 sample
dates 2012-2025, top-25 per fire-date):

| Pattern / cohort | n | 20d excess | 20d direction lift | Verdict |
|---|---|---|---|---|
| multi_year_breakout | 1,783 | **+1.41pp** | +3.5pp | **PASSED** — fwd-return narrative allowed (60d +4.20pp, 120d +5.96pp) |
| rs_top_decile | — | **+1.19pp** (consistent; 56% vs 54% pos) | +2.3pp | **PASSED** — badge allowed |
| sustained_uptrend | 2,979 | +0.75pp | +4.9pp | MARGINAL — names-only, no fwd-return copy |
| pullback_to_50dma | 3,747 | **−0.28pp** | −0.6pp | **FAILED** — not surfaced (excess negative at every horizon: 5d −0.03, 60d −0.61, 120d −0.57) |
| inflection (21d RS-rank delta) | — | −0.27pp, sign flips | — | Observation-only — no outperformance claim anywhere |
| extension_high | — | +0.79pp | — | Null result — extended names did NOT underperform; "Extended" is a state label, no mean-reversion story |

Original 5 watchlists (breakouts, rs_leaders, coiled_springs, stretched,
recent_breakdowns) are pre-protocol: never validity-tested, acceptable
because they publish names without forward claims.

**Where:** detectors `kite-api/app/insights/watchlists.py`, `rs_rank.py`;
studies in the two VALIDITY folders; harness
`tasks/insight_engine/pattern_validity_study.py`.
**Recommendation: surface now** — DASHBOARD_DESIGN §3 already plans
this; the numbers above are the exact badge copy allowed. Do not let
"Coiled fresh momentum" inherit a forward claim (inflection is
observation-only).

### 1.5 Seasonality + calendar context (built, API live, not in the dashboard IA)

**What:** `calendar_content.py` — `get_seasonality` (historical
calendar-month / ISO-week Nifty profile: median, middle-half range, %
positive years, n), `get_on_this_day` (1/3/5/10y anniversaries annotated
with that date's regime + stress), `get_pre_event` (budget / RBI /
election event-type history from `data/static/historical_events.csv`).
Routes exist: `/api/insights/calendar/{seasonality,on-this-day,pre-event}`.

**Validity status:** permanently descriptive-only by design — with n≈16
per month it can never clear the n≥100 bar; the module docstring and
`commentary._seasonality_note` encode this. Months with n<3 are omitted
rather than reported.
**Recommendation: surface now** as a small "Calendar" card (month
profile bars + on-this-day chips) with the existing descriptive copy
rules; zero backend work. Currently absent from DASHBOARD_DESIGN's IA —
cheap differentiator.

---

## Tier 2 — real candidates, but need a build step or a validity study first

### 2.1 Donchian channel breadth — `net_channel_55` family

**What:** `tasks/donchian_channel/` H3 computed 15 daily Donchian-breadth
series (pct above prior N-day high / fresh crosses / below N-day low /
net / median channel position, N ∈ {20, 55, 252}), 2010-06 → panel now
committed through **2026-07-21** (`donchian_breadth_daily.csv`, 4,302
rows — fresher than `data/breadth/breadth_daily.csv`). Verdict in
RESULTS.md: **mostly redundant** — `net_channel_252` vs
`net_new_highs_pct` ρ = 0.95, `med_chanpos_252` vs `pct_above_200dma`
ρ = 0.97. The only semi-novel slice is the 55-day family:
`net_channel_55` max ρ 0.84, `pct_fresh_high_55` max ρ 0.78,
`med_chanpos_55` max ρ 0.77. Character: net-channel series are fast
(AR1 half-life 1-3d), channel-position medians slow (half-lives 10 / 27
/ 120d for N=20/55/252). Extremes catalog sane (bottoms 2020-03,
2011-12, 2026-03; tops 2014-05, 2023-07-31). Boundary gate: replica of
production net_new_highs_pct correlates 0.998 with the atlas panel.

**Validity status:** "No forward-return claims tested or made (atlas
discipline). If a consumer appears (e.g. an insights tile),
`net_channel_55` is the candidate and must go through
`pattern_validity_study.py` for any claim."
**Recommendation: optional descriptive tile** ("% of NSE 500 breaking
2-month highs") — surfaceable descriptively without a study, but it adds
a third breadth voice to an already 2-factor panel; only include if the
55-day horizon earns a distinct story. Any forward claim: run the
harness first.

### 2.2 Breakout-call journal (donchian H4 → PRODUCT_HANDOFF)

**What:** the surviving momentum-filtered Donchian breakout feed. India
flagship: NSE 500, fresh cross above prior 20-day high, top-quartile
126d-return/vol momentum, cap 100, exit rank < 0.35, no stop — 29.7%
CAGR / 1.40 Sharpe / −35.3% MaxDD full window; ~128 calls/yr, fresh call
in 88% of weeks, median hold ~7 months. US variant 22.2% CAGR / 0.93
Sharpe, monthly correlation with India 0.34.

**Where:** `tasks/donchian_channel/PRODUCT_HANDOFF.md` + RESULTS.md;
engine logic in `h4c/h4f/h4h simulate()`.

**Validity status:** **FAILED the validity gate for forward-return
claims** — direction lift vs same-date baseline is negative
(tail-carried economics). The handoff's hard constraint: ship only as a
transparent trend-following journal with the full loss distribution
shown, or don't ship; also requires effective-dated universe membership
and a re-run of the validity harness + dedup vs multi_year_breakout
before ANY claim.
**Recommendation: separate product decision, not a dashboard indicator.**
If green-lit it is its own feed/ledger build (the handoff has the build
list); do not fold into the indicator dashboard.

### 2.3 Analog dates as historical context (no forward claims)

**What:** the KNN analog finder (5-feature match over 16y). The
forward-return projection was **retired** (ANALOG_STUDY.md): 20d IC
+0.040, direction lift **−2.9pp** at 20d and **−3.4pp** at 60d —
anti-informative because the 20-neighbor median mean-reverts drift while
the market keeps drifting. But the study explicitly preserves the match
component: "Educational/contextual content can use the analog DATES
('this resembles October 2018') without making forward-return claims.
That framing is honest and informative."

**Where:** `kite-api/app/insights/analog_finder.py` (module + tests kept
as research artifact; `/api/insights/analogs` route still exists;
UI page removed).
**Validity status:** forward projection FAILED and is retired; date-only
context is protocol-exempt.
**Recommendation: needs a deliberate reframe** — a "days like today:
Oct-2018, Mar-2023" chip on the regime detail view, dates only, no
numbers. Low effort, but get founder sign-off given the feature's
history.

### 2.4 Breadth 3-state regime (BV3 lineage) as an educational study

**What was concluded (the full BV3 arc):**
1. **2026-05-14, commit `2953504`** (`tasks/MM-tuning/VALUE_ZONE_REGIME.md`,
   archive branch): first 3-state Bull/Bear/Value-Zone regime. BV3 =
   breadth value zone at pct_above_200dma < 20%, sticky (Value exits only
   to Bull). Best variant: OOS (2017-2026) Sharpe 1.92 vs binary 1.85,
   CAGR 39.31%, DD penalty +1.5pp, 85% walk-forward pass, captured the
   Apr-May 2026 rally (YTD 4.35% vs binary 1.47%). V3 (−1.5σ stddev
   trigger) rejected — +11pp drawdown blowout. Status then: "promising,
   pending deeper breadth-metric exploration."
2. **Breadth atlas** (2026-05-15) was built to inform that exploration.
3. **`tasks/breadth_atlas/experiments/RESULTS.md`** (score-tilt 3-state on
   production portfolios): OM25-shaped, not universal — OM25 NSE 500 OOS
   Sharpe 2.19 vs 1.87 baseline, but most of the gain (~+0.44) was the
   universe expansion, not the regime; TL25 +0.00, L6 +0.03; 2025
   underperformance real (−5.4 to −11.4pp). No production change.
4. **`tasks/breadth_atlas/combo_3state/RESULTS.md`** (2026-05-21, CLOSED):
   D_BREADTH (avg_dist_from_200dma 3-state) vs production A_PROD failed
   3 of 4 gates — 66.7% rolling-window Sharpe wins (< 70% bar), 2022
   −16.8pp / 2025 −14.2pp deeper drawdowns, L6 correlation 0.91-0.92
   (> 0.85 bar). Verdict: A_PROD's cash buildup IS both the protection
   and the differentiation. Durable findings: breadth 3-state wins
   V-bottom recoveries (2012/2013/2017/2020), loses slow grinds
   (2016/2022/2025); `avg_dist_from_200dma` is the most consistent
   regime metric; sticky-deep state machine library reusable
   (`combo_breadth_3state.py`).

**Validity status:** as a trading signal — tested thoroughly and NOT
deployed. As dashboard content — never intended; the production 4-state
regime engine (`regime.py`, `/regime/history`) is what ships.
**Recommendation: skip as an indicator** (would compete with the
production regime ribbon and imply a signal we chose not to deploy).
The one transferable nugget: use `avg_dist_from_200dma` (per 1.1) and,
if desired, a Learn explainer on "why washed-out breadth marks
V-bottoms but not slow grinds" citing the V-bottom/slow-grind split —
it is the most subscriber-legible finding of the whole line.

---

## Tier 3 — concluded negatives; skip (documented so nobody re-litigates)

| Line | Where | Conclusion |
|---|---|---|
| Stress-regime reversal calls | `tasks/stress_reversal_calls/RESULTS.md` | REJECTED, pre-registered negative. Selection excess ~0 (−0.6 to +1.0pp, sign-inconsistent); timing excess negative everywhere (−1.1 to −5.1pp); threshold 85 exploratory check same picture. Stress entries forgo bull drift. Explicitly: the index-level STRESS base-rate (1.3) stays valid; the stock-level conversion does not exist. |
| pullback_to_50dma | `tasks/insight_engine/PATTERN_VALIDITY/pullback_to_50dma.md` | FAILED (−0.28pp 20d excess, negative at all horizons). Not surfaced. |
| Analog forward returns | `ANALOG_STUDY.md` | Retired (see 2.3). |
| Nifty swing trading | commit `2ccea3f`, `tasks/nifty_trader/` | 0 of 320 combos beat B&H Sharpe in IS+OOS; Nifty breakout edge is 1-day only, decays by day 5. |
| Panic-bounce (−5% in 10d + VIX>22) | same | Standalone: real per-trade edge, too thin vs drift. As leveraged overlay on B&H: Sharpe 0.745 vs 0.57, MaxDD −23% vs −38% — best of that line, but requires futures leverage; pivoted to the insights product instead. Never productized. |
| OM25 alternatives (ROM25/LV25/MV25/MV25d/OM25d) | `tasks/om25_alt/RESULTS.md` | CLOSED, no production change. Every defensive tilt was either momentum-in-disguise (corr 0.84-0.92 with L6) or too defensive (LV25 Sharpe 0.83). Matches the standing memory: frame portfolio work as diagnostic, not exploratory. |
| Donchian exits / GH 52w-high ranking / stops / mid-caps / cap-widening | `tasks/donchian_channel/RESULTS.md` "rejected" list | All rejected; PRODUCT_HANDOFF says do not re-litigate without new evidence. |

---

## Data freshness & plumbing gaps (for the build plan)

- **`data/breadth/breadth_daily.csv` is stale**: last row 2026-05-08
  (3,932 days). It is the atlas research snapshot, rebuilt manually by
  `scripts/build_breadth_panel.py` (~90s). The **live** breadth API does
  not read it — `breadth.py` recomputes from `nse500_data_merged/` with
  an mtime-signature cache, so `/breadth/timeseries` is fresh daily.
  Implication: the dashboard should draw series from the live engine and
  use the atlas CSVs only for static bands/annotations; if bands are
  ever recomputed, rebuild the panel first.
- **Live engine metric gaps vs atlas** (see 1.1 table): missing
  `avg_dist_from_200dma`, `mcclellan_sum`, `pct_above_21dma`,
  `ad_ratio`, `up_vol_ratio`; has extra `dispersion` (no atlas bands)
  and `n_active`.
- `tasks/donchian_channel/donchian_breadth_daily.csv`: committed through
  2026-07-21 (4,302 rows); no daily refresh job.
- Untapped engines with routes but no dashboard slot: `conditional_dist`
  (no route at all — biggest gap, see 1.3), `calendar/*` (routes live,
  absent from IA, see 1.5), `analogs` (route live, UI removed, see 2.3).
  `concentration`, `subgroups`, `cross-asset`, `regime/history` are
  already accounted for in DASHBOARD_DESIGN.
- Per-stock rank/score history is point-in-time only — the design's §3
  daily cross-section persistence note is the fix; it also unblocks list
  membership-over-time panels.

## Top recommendations (ordered by readiness)

1. Add `avg_dist_from_200dma` to the live breadth engine and the metric
   selector — the atlas's most robust deep-panic gauge (bands −11.0% /
   +5.1% / +29.2%; <−2σ ≈ −27% concurrent DD on 47 days).
2. Ship the atlas band table (1.1) as the reference bands for every
   metric already in the selector; respect the 2-factor curation rule.
3. Ship the extremes catalog (1.2) as labeled historical episodes on
   breadth charts.
4. Build the "Historical base rates by regime" module from
   `conditional_dist` (1.3) — validated content, zero new math, needs
   one API route + one chart.
5. Add the Calendar/seasonality card (1.5) — live API, descriptive-only
   copy rules already written.
6. Everything in Tier 3 stays dead; any new forward-return claim goes
   through `pattern_validity_study.py` first.
