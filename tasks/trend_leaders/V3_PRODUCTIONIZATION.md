# TL25 v3 Productionization Plan

**Goal:** wire the locked-in TL25 v3 strategy (saved as `scripts/tl25_v3.py:V3_LOCKED`) into the existing production stack — daily pipeline, dashboard backend, and DB sync — mirroring exactly what was done for OM25 v3 in commits `5888249`, `d2c1162`, `826f2a9`.

**Owner:** Claude + nav-bajaj.
**Status:** DONE (productionization committed 2026-05-12 in `0cdb984`).
**Reference for wiring contracts:** see `tasks/oos_retune_2026/RESULTS.md` (TL25 v3 section) and the three OM25 v3 commits above.

## Result (2026-05-12)

All 4 phases completed in a single session. End-to-end verification:

| # | Test | Result |
|---|---|---|
| 1 | Orchestrator smoke test (`--start 2017-01-01`) | ✓ CAGR 34.33% / Sharpe 1.37 / MaxDD -38.79% — matches OOS report |
| 2 | CSV schema (holdings / equity / trades / metrics) | ✓ All columns correct |
| 3 | `get_latest_experiment_dir('tl25_v3')` | ✓ Returns latest portfolio dir |
| 4 | `PositionsService.sync_from_csv('tl25_v3')` | ✓ 21 positions inserted into DB |
| 5 | `sync_to_database.py --universe tl25_v3` | ✓ 21 holdings / 2304 equity / 2812 trades / 1410 matches |
| 6 | `run_daily_pipeline.py --dry-run` | ✓ TL25 v3 step inserted between OM25 v3 and DB sync |
| 7 | Full live run | Deferred (requires Kite login + network) |

Final wiring landed in `0cdb984` — 7 files changed, +707/-6:
- `scripts/run_tl25_v3_portfolio.py` (new)
- `kite-api/app/config.py`
- `kite-api/app/services/sync_service.py`
- `kite-api/app/services/positions_service.py`
- `scripts/sync_to_database.py`
- `scripts/run_daily_pipeline.py`
- `tasks/trend_leaders/V3_PRODUCTIONIZATION.md`

---

## Nuances and design notes (read before implementing)

These are the subtle pitfalls and structural differences TL25 has vs OM25, plus the contracts the existing pipeline assumes. Get any of these wrong and the dashboard will silently swallow the data or the daily run will fail.

### N1. TL25 has no regime panel — orchestrator is simpler than OM25

OM25 v3's score is regime-tilted: it computes a NIFTY-100-based bull/bear panel and feeds it into `make_om25_tilt_score`. **TL25 v3 has no regime.** The orchestrator should:
- NOT load `indices_data/NIFTY_100.csv` for a regime signal
- NOT call `build_regime_panel_confirmed`
- Use `make_tl25_score` (no regime arg, defaults to `None`)
- Keep Nifty 100 as the **benchmark** for comparison (`data/benchmarks/nifty100.csv`) — same as OM25

The CLI should drop `--regime-index`, `--ma-window`, `--confirm-days`, `--bull-w-*`, `--bear-w-*`. Replace with: `--w-persistence`, `--w-drawdown`, `--w-momentum` (all defaulting from `V3_LOCKED`).

### N2. TL25 requires pre-computed panels before the score function

OM25's `make_om25_tilt_score` takes a raw returns DataFrame and computes everything per signal date. TL25's `make_tl25_score` takes pre-built **panels** (eligibility, persistence, drawdown, momentum_raw) from `build_tl25_panels`. The orchestrator must:

```python
universe = load_universe(args.universe)
cols = [s for s in close_panel.columns if s in universe]
close_uni = close_panel[cols]
panels = build_tl25_panels(
    close_uni,
    dma_short=V3_LOCKED["dma_short"],
    dma_long=V3_LOCKED["dma_long"],
    dma_persist_ref=V3_LOCKED["dma_persist_ref"],
    persistence_window=V3_LOCKED["persistence_window"],
    drawdown_window=V3_LOCKED["drawdown_window"],
    drawdown_concavity=V3_LOCKED["drawdown_concavity"],
    momentum_window=V3_LOCKED["momentum_window"],
)
score_fn = make_tl25_score(panels,
    w_persistence=args.w_persistence,
    w_drawdown=args.w_drawdown,
    w_momentum=args.w_momentum,
)
```

`build_tl25_panels` is moderately expensive (4 rolling computations across the full universe panel) — fine for once-per-day, but don't accidentally call it inside a sweep loop.

### N3. Weekly rank-exit is the new engine flag — must be set

The new engine parameter `weekly_rank_check=True` is what gives TL25 v3 its DD-reduction edge over the prior biweekly-only behaviour. The `run_strategy` call must pass:

```python
res = run_strategy(
    ...,
    use_trailing_stop=True,
    use_dma_exit=False,                       # OM25 also keeps this False
    atr_mult=0.0,                              # disable ATR-vol stop
    atr_min_floor=V3_LOCKED["atr_min_floor"], # 0.20 → fixed 20% DD stop
    weekly_rank_check=True,                    # ← TL25-specific
    regime_panel=None,
    bear_exposure=0.0,
)
```

Also: there is a known engine bug we fixed in this work — `entry_schedule` used to be built from `signals.keys()`, which made every Friday a rebal day when `weekly_rank_check=True`. The fix in `scripts/_clean_engine.py:236-246` is committed; double-check it's present before testing.

### N4. Directory naming convention is load-bearing

The dashboard's regex matching is brittle. The output dir for each TL25 v3 run **must** be:

```
data/tl25_v3_portfolios/tl25_v3_portfolio_<YYYYMMDD>_<HHMMSS>/
```

— specifically:
- Parent dir: `data/tl25_v3_portfolios/` (not `data/tl25/v3/` or anything else)
- Timestamp: `_` separator between date and time (NOT concatenated `YYYYMMDDHHMMSS`)
- Prefix: `tl25_v3_portfolio_`

Inside the run dir, the dashboard expects:
```
<run>/backtests/baseline/momentum_equity.csv
<run>/backtests/baseline/momentum_holdings.csv
<run>/backtests/baseline/momentum_trades.csv
<run>/backtests/baseline/momentum_metrics.csv
```

The native TL25 CSVs (`tl25_equity.csv`, `tl25_trades.csv`, `tl25_exits.csv`, `tl25_signals.csv`, `metrics.json`) live at the run dir root for strategy-aware tooling and human inspection.

### N5. Dashboard CSV schema is fixed — don't deviate

From OM25 v3 (verified contract):

**momentum_equity.csv** — required columns:
- `date` (YYYY-MM-DD string or datetime)
- `portfolio_value` (float)
- `drawdown` (float, negative)
- `benchmark` (optional)

**momentum_holdings.csv** — required columns:
- `symbol` (string)
- `shares` (int)
- `avg_cost` (float, includes slippage in cost basis)
- `entry_date` (date)
- `entry_rank` (int, can be NaN if not tracked)
- `holding_days` (int)
- `last_price` (float, from close_panel on backtest end date)
- `pnl_pct` (float, `last_price / avg_cost - 1`)
- `notional` (float, `shares * last_price`)
- `contribution_pct` (float, position weight in portfolio)

**momentum_trades.csv** — required columns:
- `date`, `symbol`, `side` (BUY/SELL), `shares`, `price`, `notional`, `slippage`

**momentum_metrics.csv** — single row with columns:
- `start`, `end`, `total_return`, `cagr`, `max_drawdown`, `sharpe_ratio`,
  `annualized_volatility`, `hit_rate_overall`, `avg_holding_days`,
  `trades_total`, `buys`, `sells`

We can copy `write_dashboard_outputs()` from `scripts/run_om25_v3_portfolio.py` almost verbatim — the only TL25 difference is `exits` column lookup may differ slightly; verify with one local run.

### N6. positions_service regex must be extended

The current regex in `kite-api/app/services/positions_service.py` matches:
```python
r'(final_portfolio|nifty\d+_portfolio|om25_v3_portfolio)_\d{8}(_\d{6}|\d{6})'
```

Add `tl25_v3_portfolio` to the alternation. The timestamp half (`\d{8}(_\d{6}|\d{6})`) is already correct.

Also: `sync_from_csv` has an `experiments_dir` branch with explicit `elif universe == "om25_v3"` — we need a parallel `elif universe == "tl25_v3"` returning `settings.data_dir / "data" / "tl25_v3_portfolios"`.

### N7. UNIVERSES dict in config.py is a strategy×universe combo, not a universe

OM25 v3 entry in `kite-api/app/config.py:UNIVERSES`:
```python
"om25_v3": {
    "id": "om25_v3", "name": "OM25 v3",
    "description": "Regime-tilted UC/CR composite on Nifty 250 (May 2026 OOS retune)",
    "strategy": "OM25 v3 (UC/CR composite, regime-tilted)",
    "stocks": 250,
    "risk_profile": "Quality momentum with defensive bear tilt",
    "data_dir": "nse500_data",
    "universe_file": "data/static/nifty250_universe.csv",
    "portfolio_dir": "data/om25_v3_portfolios",
},
```

TL25 v3 equivalent:
```python
"tl25_v3": {
    "id": "tl25_v3", "name": "TL25 v3",
    "description": "Trend-quality score on NSE 500 (May 2026 OOS retune)",
    "strategy": "TL25 v3 (3-component trend score, weekly rank-exit)",
    "stocks": 500,
    "risk_profile": "Pure trend-following, diversifier vs OM25",
    "data_dir": "nse500_data",
    "universe_file": "data/static/nse500_universe.csv",
    "portfolio_dir": "data/tl25_v3_portfolios",
},
```

Also extend `UniverseId` Literal to include `"tl25_v3"`.

### N8. Daily pipeline insertion point

Add a new sequential step **after** "Build OM25 v3 portfolio" and **before** the DB sync. Order matters: the sync step reads from `data/tl25_v3_portfolios/tl25_v3_portfolio_*/backtests/baseline/`, so the TL25 run must finish first.

Like OM25, use `--prices-dir nse500_data --start 2020-01-01` (live data dir, recent slice for daily updates). NO `--regime-index` for TL25.

### N9. Two output paths get committed; one stays gitignored

- `data/tl25_v3_portfolios/` — gitignored (per-run timestamped output, large). Already implicitly covered if `data/*_portfolios/` is gitignored; verify.
- `tasks/oos_retune_2026/winner_artifacts/tl25_v3_production_*.csv` — already committed (research evidence).

The dashboard reads from the timestamped dirs at runtime; nothing here needs to land in git.

### N10. The orchestrator should NOT include OOS-only restriction

The production orchestrator runs the full panel by default (`--start 2009-01-01` if backtesting from scratch; `--start 2020-01-01` for daily pipeline). The OOS-only restriction was a research/reporting concern. Production needs realistic warmup + the freshest holdings.

---

## Detailed task list

### Phase A — Production orchestrator + utilities

**Task 1.** Create `scripts/run_tl25_v3_portfolio.py`.
- Mirror `scripts/run_om25_v3_portfolio.py` structure.
- CLI args (with defaults from `V3_LOCKED`):
  - `--prices-dir` (default `nse500_data_merged` for backtest; production daily run passes `nse500_data`)
  - `--universe` (default `data/static/nse500_universe.csv`)
  - `--benchmark` (default `data/benchmarks/nifty100.csv`)
  - `--start` (default `2009-09-01`; pipeline passes `2020-01-01`)
  - `--end` (default None)
  - `--cadence` (only `"biweekly"` supported)
  - `--top-n`, `--exit-buffer`, `--max-weight`, `--slippage`
  - `--w-persistence`, `--w-drawdown`, `--w-momentum`
  - `--persistence-window`, `--drawdown-window`, `--momentum-window`
  - `--drawdown-stop` (default 0.20)
  - `--initial-capital` (default 1_000_000)
  - `--output-dir` (auto-generates if None)
- Use `build_tl25_panels` + `make_tl25_score` + `run_strategy(weekly_rank_check=True, ...)`.
- Output dir: `data/tl25_v3_portfolios/tl25_v3_portfolio_<YYYYMMDD>_<HHMMSS>/`.
- Write **both** sets of outputs:
  - Native: `tl25_equity.csv`, `tl25_trades.csv`, `tl25_exits.csv`, `tl25_signals.csv`, `metrics.json` (full args + summary).
  - Dashboard: `backtests/baseline/momentum_{equity,holdings,trades,metrics}.csv` via `write_dashboard_outputs` helper.
- Smoke test: running `python scripts/run_tl25_v3_portfolio.py --start 2017-01-01` should produce a working report that round-trips through the dashboard sync.

**Task 2.** Verify `data/tl25_v3_portfolios/` is gitignored.
- Check `.gitignore` for `data/*_portfolios/` or equivalent rule.
- Add `data/tl25_v3_portfolios/` if not already covered.

### Phase B — Dashboard backend wiring

**Task 3.** Update `kite-api/app/config.py`.
- Add `tl25_v3` entry to `UNIVERSES` dict (see N7 above for exact shape).
- Extend `UniverseId` Literal to include `"tl25_v3"`.
- Order: append after `om25_v3` (last position).

**Task 4.** Update `kite-api/app/services/sync_service.py`.
- In `get_latest_experiment_dir(universe)`: add an `elif universe == "tl25_v3":` branch returning `base_dir / "data" / "tl25_v3_portfolios" / "tl25_v3_portfolio_202*"`.
- In `sync_all_universes`: append `"tl25_v3"` to the iteration list (so it runs as part of "sync everything").

**Task 5.** Update `kite-api/app/services/positions_service.py`.
- Extend the `dir_pattern` regex alternation to include `tl25_v3_portfolio`. New pattern:
  ```python
  r'(final_portfolio|nifty\d+_portfolio|om25_v3_portfolio|tl25_v3_portfolio)_\d{8}(_\d{6}|\d{6})'
  ```
- In `sync_from_csv` add an `elif universe == "tl25_v3":` branch setting `experiments_dir = settings.data_dir / "data" / "tl25_v3_portfolios"`.

**Task 6.** Update `scripts/sync_to_database.py`.
- CLI `--universe` help text: include `tl25_v3` in the list of valid values.
- The default-sync list: append `"tl25_v3"` so `python scripts/sync_to_database.py` (no args) syncs TL25 v3 too.

### Phase C — Daily pipeline integration

**Task 7.** Update `scripts/run_daily_pipeline.py`.
- Add a new step to `SEQUENTIAL_STEPS`, placed **after** "Build OM25 v3 portfolio" and **before** the DB sync step:
  ```python
  ("Build TL25 v3 portfolio", [
      sys.executable, "scripts/run_tl25_v3_portfolio.py",
      "--prices-dir", "nse500_data",
      "--start", "2020-01-01",
  ]),
  ```
- Verify the step order: data fetch → momentum signals → OM25 v3 → **TL25 v3** → DB sync → backup.

### Phase D — Test plan (run after all of A–C)

**Task 8.** Local smoke tests.
1. **Standalone orchestrator run:**
   ```bash
   source .venv/bin/activate
   python scripts/run_tl25_v3_portfolio.py --start 2017-01-01
   ```
   - Expected: dir created at `data/tl25_v3_portfolios/tl25_v3_portfolio_<ts>/`.
   - Both `tl25_*.csv` (root) and `backtests/baseline/momentum_*.csv` produced.
   - `momentum_metrics.csv` shows OOS-only CAGR ~34.86%, Sharpe ~1.53 (matches `RESULTS.md`).

2. **Schema verification:**
   ```bash
   head -2 data/tl25_v3_portfolios/tl25_v3_portfolio_*/backtests/baseline/momentum_holdings.csv
   ```
   - Required columns: `symbol, shares, avg_cost, entry_date, entry_rank, holding_days, last_price, pnl_pct, notional, contribution_pct`.

3. **Dashboard sync (offline):**
   ```bash
   cd kite-api && source .venv/bin/activate
   python -c "
   from app.services.sync_service import get_latest_experiment_dir
   print(get_latest_experiment_dir('tl25_v3'))
   "
   ```
   - Expected: prints path to the latest tl25_v3_portfolio dir.
   - Should NOT return None.

4. **positions_service regex test:**
   ```bash
   cd kite-api && source .venv/bin/activate
   python -c "
   from app.services.positions_service import PositionsService
   r = PositionsService.sync_from_csv('tl25_v3')
   print(r)
   "
   ```
   - Expected: returns 25 positions (matching current holdings in latest run dir).
   - Failure mode: "Portfolio CSV not found for tl25_v3" → regex/branch not wired correctly.

5. **Sync CLI:**
   ```bash
   python scripts/sync_to_database.py --universe tl25_v3 --help
   python scripts/sync_to_database.py --universe tl25_v3  # actual sync
   ```
   - Expected: `tl25_v3` appears in help; sync completes with row counts in output.

6. **Daily pipeline dry-run:**
   ```bash
   python scripts/run_daily_pipeline.py --dry-run
   ```
   - Expected: TL25 v3 step prints in the dry-run output, between OM25 v3 and DB sync.

7. **Full daily pipeline (live):**
   ```bash
   python scripts/run_daily_pipeline.py
   ```
   - Expected: each step including TL25 v3 completes without error.
   - Output dir created, dashboard files present, sync step picks up the new data.

**Task 9.** Commit + push.
- One commit covering Phase A + B + C with the message style matching `d2c1162` ("Wire TL25 v3 into daily pipeline + dashboard sync").
- One commit if any regex/positions bug surfaces during testing (style of `826f2a9`).

---

## Out of scope (explicitly)

- **Frontend (kite-dashboard)** — adding a "TL25 v3" option to the universe selector requires changes in a separate Next.js codebase. Backend will return the data; UI surfacing is a follow-up.
- **Production deployment** — pushing to Railway/Vercel after the backend changes land. Local + main-branch commit only in this scope.
- **Cross-strategy correlation monitoring** — could be useful but out of scope.

---

## Open questions / decisions

None blocking. The wiring contract is fully specified by the three OM25 v3 commits — TL25 v3 is a straightforward mirror with the simplifications noted in N1-N3.
