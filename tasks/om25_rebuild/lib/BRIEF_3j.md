# §3j — momentum-strength overlay (exploration brief)

## The question
The book (capture-ratio momentum, one regime, top 25 / exit buffer 20,
lookback 252, return filter on, fully invested) does 23.7% / Sharpe 1.50 /
MaxDD -17% on Nifty 250 monthly and 22.7% / 1.35 / -15.5% on NSE 500
biweekly over 2010-2015. It loses ~65% in 2008. A price-regime overlay
(ROC of NIFTY 100 with confirm-day hysteresis, cutting gross exposure in
bear) fixes 2008 but costs 5-15pp of CAGR a year in every other regime and
never beats the fully invested book on 2010-2015 (0 of 96 cells).

The founder's idea: measure the **strength of momentum being displayed by
the stocks in the index** ("momentum gravity"). When that strength is
falling, or sits below a threshold, momentum-the-factor is not working
and the book should cut exposure. Explore whether such an indicator
exists that (a) would have cut 2008 materially and (b) costs little on
2010-2015.

## Acceptance (report against these; do not tune to them after the fact)
- Cost on 2010-2015 (the in-sample window, start 2010-01-01): within
  ~2pp CAGR and ~0.10 Sharpe of the fully invested book on each universe.
- Protection on 2006-02-01 → 2009-12-31 (a fresh run started 2006-02-01;
  this window is *before* in-sample, it is not out-of-sample): MaxDD no
  worse than about -40% against -65% fully invested, without giving up
  the 2009 recovery entirely (report CAGR over the same window).
- Parameter count: the overlay may add at most 3 parameters (indicator
  length, threshold/percentile, confirm days) — the gate G6 is ≤ 10 all-in
  and the base book already uses 7.
- **Never touch 2016 or later.** Out-of-sample is closed. Do not compute,
  print or look at any statistic past 2015-12-31.

## Candidate indicators (explore, do not limit yourself to these)
1. Breadth of momentum: fraction of universe members with positive
   trailing 12-month (252-day) return, or above their 200-DMA.
2. The factor's own momentum: trailing 1-3 month return of an
   equal-weight top-decile minus bottom-decile spread ranked by 12-1
   momentum (long-short momentum factor return); sign, level, or its
   slope.
3. Cross-sectional dispersion of trailing returns (momentum needs spread
   to work; collapsing dispersion + falling breadth is the classic tell).
4. Persistence: rank correlation of momentum scores between t and t-21
   (or t-63). Low persistence = momentum crashing/rotating.
5. The harness's own score: mean or median capture ratio of the current
   top 25, or of the whole universe, and its trend.
Thresholds must be point-in-time: absolute, or expanding-window /
trailing-window percentiles computed only from data ≤ t. Use confirm-day
hysteresis like the ROC regime (`_confirm` in lib/regime.py). Exposure
levels to test: 50%, 25%, 0% in the weak state (75% is barely an overlay).

## Harness (read these first; ~2-8 s per run)
- `lib/run.py`: `run_candidate(**cfg)` runs one config, writes
  `runs/<id>/{config.json,equity.csv,trades.csv}`, reuses a completed run.
  DEFAULTS shows every key. The overlay is `overlay=True` + a boolean
  regime series over the calendar (`overlay_panel`, True = normal, False
  = cut) + `bear_exposure`. Today that series comes from `regime_kind`
  "roc" or "ma" via `lib/regime.py`. **Add a new `regime_kind`
  ("strength") with its own parameters** rather than changing the
  existing ones; do not change the cadence / exit_cadence code that was
  just added.
- `lib/windows.py`: `equity(path)`, `stats(eq, start, end)` (CAGR, Sharpe
  rf 5%, MaxDD), `register(cfg, id, stats, phase)` — **register every
  trial you run with phase "3j"**, including failures; the registry is
  the deflation denominator.
- Data: `run.py`'s `panels()` returns the close/trade panels (price
  return, aligned calendar, NaN outside membership), `p["bench"]`;
  `resolve_universe(...)` gives point-in-time membership. NIFTY 100 index
  at `REGIME_INDEX`. Build any breadth/dispersion measure from the
  harness panels and the universe membership, not from
  `~/Documents/stock_data` (a different adjustment vintage).
- Lookahead traps: pct_change over an unfilled panel; rolling windows on
  gappy series; a threshold from full-sample percentiles. Compute
  everything from data ≤ t.
- Budget: ≤ ~300 trials, ≤ ~60 minutes of compute. Run from
  `/Users/navdeep/kite-lab` with the repo `.venv` python
  (`.venv/bin/python`), scripts in `tasks/om25_rebuild/lib/phase3j*.py`.

## Deliverables
1. `lib/regime.py` gains the indicator(s); `lib/run.py` gains the
   `regime_kind` hook and any new DEFAULTS keys (defaults must leave every
   existing config's id unchanged — add keys with defaults, and confirm
   `cfg_id` of an old config is unchanged, otherwise every prior run
   reruns).
2. `runs/3j_summary.csv` — one row per trial with the indicator, its
   parameters, exposure, and CAGR/Sharpe/MaxDD on 2010-2015 and on
   2006-2009.
3. A section appended to `RESULTS.md`, "## §3j — momentum-strength
   overlay (agent, N trials)", in the style of the existing sections:
   what was tried, a table of the best cells per indicator against the
   fully invested book on both windows, the acceptance verdict, and a
   plain statement of what did not work. Report numbers exactly as
   measured; no rounding up; flag anything approximate.
Do not commit. Do not open OOS. If nothing meets acceptance, say so.
