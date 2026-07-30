# Research index — options program

Dated results (read in order for the narrative):

| File | What it holds |
|---|---|
| `RESULTS_2026-07-27_history_probe.md` | Historical API capability check + 5-session exploratory read (pin forming, straddle premium, PCR coincident) |
| `RESULTS_2026-07-28_first_patterns.md` | Day-one depth findings: pin built intraday (ATM OI 3x), ITM-put imbalance cluster (later killed), expiry friction curve |
| `RESULTS_2026-07-29_trend_day.md` | Out-of-sample: cluster killed honestly; OI-migration regimes (star result); friction two-regime confirmation |
| `NOTE_risk_thresholds.md` | **Founder framework**: MAE problem (drawdown > final profit all 3 days), probabilistic-not-predictive hold/roll/exit, per-regime threshold table as the future risk config |

Reusable scripts (run from `kite-api/` with DATABASE_URL set; see each
docstring):

| Script | Purpose |
|---|---|
| `backfill_history.py` | Pull minute+OI candles for a selection date (research-side; prod backfill is `app.workers.options.backfill`) |
| `explore_history.py` | 5-session exploratory suite over the first backfill |
| `analyze_positioning.py` | Day-one four-study suite (imbalance, OI crush, straddle, spreads) |
| `analyze_day2_trend.py` | Day-two out-of-sample + trend-day OI mechanics |
| `straddle_sim.py` | Short-straddle sim, real bid/ask fills; per-day CLI args |

Visual explorers (self-contained HTML, open in a browser):

- `depth_imbalance_chart.html` (+`chart_data.json`) — TradingView candles + imbalance histogram, 6 contracts across the pin and trend days
- `otm_depth_comparison.html` (+`otm_depth_data.json`) — 3 OTM CE vs 3 OTM PE book imbalance, synced panes

Since 2026-07-30 the worker writes an automated daily report to the
Railway volume (`/data/options/reports/<date>.md`) — the standing
successor to hand-run analysis; files here are for deeper dives.
